# main.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os, uuid, datetime, logging, re, base64, io, zipfile
from dotenv import load_dotenv
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import firebase_admin
from firebase_admin import credentials, firestore
import magic
from update_invoice import update_invoice_route

# Initialize Flask app
app = Flask(__name__)
CORS(app)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= Firebase Setup =================
def initialize_firebase():
    try:
        if not firebase_admin._apps:
            cred_path = os.path.join(os.path.dirname(__file__), 'FIREBASE_CREDS_JSON.json')
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase initialized successfully.")
        return firestore.client()
    except Exception as e:
        logger.exception("❌ Failed to initialize Firebase")
        raise e

db = initialize_firebase()
user_collection = "users"

# ================= Gemini AI Setup =================
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("models/gemini-1.5-pro")

# ================= Google Sheets Setup =================
SHEETS_SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_ID = "1oHZaMlRgjshM-iQmB05l7ph-3tb_fRtGKeBKY-8OzqI"
sheet_creds = Credentials.from_service_account_file("credentials.json", scopes=SHEETS_SCOPE)
gc = gspread.authorize(sheet_creds)

summary_sheet = gc.open_by_key(SPREADSHEET_ID).worksheet("Sheet1")
item_sheet = gc.open_by_key(SPREADSHEET_ID).worksheet("Sheet2")

# ================= Helper Functions =================
def parse_json(text):
    try:
        if "```json" in text:
            match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        else:
            match = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(match.group(1 if "```json" in text else 0)) if match else None
    except Exception as e:
        logger.error(f"JSON parsing failed: {str(e)}")
        return None

def safe_get(d, path, default=""):
    for key in path:
        if isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d

def clean_empty(data):
    if isinstance(data, dict):
        return {k: clean_empty(v) for k, v in data.items() if v not in ("", None, [], {}, 0)}
    if isinstance(data, list):
        return [clean_empty(i) for i in data if i not in ("", None, [], {}, 0)]
    return data

# ================= Invoice Processing =================
def process_invoice(image_path=None):
    try:
        with open(image_path, 'rb') as file:
            image_data = file.read()

        mime_type = magic.from_buffer(image_data, mime=True)
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        response = gemini_model.generate_content([
            """Extract invoice data in JSON format with fields: 
            vendor, invoice_no, date, bill_to, items, subtotal, tax, total""",
            {"mime_type": mime_type, "data": image_base64}
        ])
        
        data = parse_json(response.text)
        if not data: return None

        # Add timestamp and clean data
        data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return clean_empty(data)

    except Exception as e:
        logger.error(f"Invoice processing failed: {str(e)}")
        return None

# ================= Spreadsheet Operations =================
def insert_into_sheet(data, user_email):
    try:
        # Firebase user lookup
        user_ref = db.collection(user_collection).where("email", "==", user_email).limit(1).get()
        user_name = user_ref[0].get('name') if user_ref else 'Unknown User'

        # Check for existing invoice
        invoice_no = data.get("invoice_no", "")
        if invoice_no in [row[4] for row in summary_sheet.get_all_values()[1:]]:
            return "Already uploaded"

        # Prepare sheet data
        timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        summary_row = [
            f"{len(summary_sheet.get_all_values()):04d}",
            f"{user_name} ({user_email})",
            timestamp,
            safe_get(data, ["bill_to", "name"]),
            safe_get(data, ["vendor", "company"]),
            invoice_no,
            data.get("date", ""),
            data.get("vehicle_no", "")
        ]
        
        # Insert into sheets
        summary_sheet.append_row(summary_row)
        for item in data.get("items", []):
            item_sheet.append_row([
                len(item_sheet.get_all_values()) + 1,
                summary_row[0],
                item.get("description", ""),
                item.get("quantity", 0),
                item.get("unit_price", 0),
                item.get("remark", "")
            ])
        
        return "Inserted"
    except Exception as e:
        logger.error(f"Sheet insertion failed: {str(e)}")
        return "Failed"

# ================= Flask Routes =================
@app.route("/api/process", methods=["POST"])
def process_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    email = request.form.get("email") or request.headers.get("X-User-Email")
    if not email: return jsonify({"error": "Email required"}), 400

    try:
        # Save and process file
        temp_path = f"/tmp/{uuid.uuid4()}.png"
        file.save(temp_path)
        result = process_invoice(temp_path)
        
        # Firebase operations
        user_ref = db.collection(user_collection).document()
        if not db.collection(user_collection).where("email", "==", email).get():
            user_ref.set({"email": email, "created_at": datetime.datetime.now(datetime.timezone.utc)})
        
        # Store invoice data
        invoice_ref = user_ref.collection("invoices").document(result["invoice_no"])
        invoice_ref.set(result)
        
        # Update spreadsheet
        sheet_status = insert_into_sheet(result, email)
        if sheet_status == "Already uploaded":
            return jsonify({"message": "Duplicate invoice"}), 409
            
        return jsonify({"message": "Success", "data": result}), 200

    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route("/api/profile", methods=["GET"])
def get_profile():
    try:
        uid = request.args.get("uid")
        if not uid: return jsonify({"error": "UID required"}), 400
        
        user_data = db.collection(user_collection).document(uid).get().to_dict()
        return jsonify({
            "email": user_data.get("email"),
            "created_at": user_data.get("created_at").isoformat(),
            "last_login": datetime.datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/invoices", methods=["GET"])
def get_invoices():
    email = request.args.get("email") or request.headers.get("X-User-Email")
    if not email: return jsonify({"error": "Email required"}), 400

    try:
        user_ref = db.collection(user_collection).where("email", "==", email).limit(1).get()
        if not user_ref: return jsonify({"invoices": []})
        
        invoices = [doc.to_dict() for doc in user_ref[0].reference.collection("invoices").stream()]
        return jsonify(invoices), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/update_invoice', methods=['POST'])
def update_invoice():
    return update_invoice_route()

# ================= Main Execution =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)