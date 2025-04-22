from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
import datetime
import logging
from dotenv import load_dotenv
from profile_1 import get_profile_route
from process import process_invoice
from spreadsheet import insert_into_sheet  # Import the function
import firebase_admin
from update_invoice import update_invoice_route

from firebase_admin import credentials, firestore

# Initialize Flask app
app = Flask(__name__)
CORS(app)
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔐 Firebase setup
def initialize_firebase():
    try:
        if not firebase_admin._apps:
            cred_path = os.path.join(os.path.dirname(__file__), 'FIREBASE_CREDS_JSON.json')
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase initialized successfully.")
        else:
            logger.info("⚠️ Firebase already initialized.")
        return firestore.client()
    except Exception as e:
        logger.exception("❌ Failed to initialize Firebase")
        raise e

db = initialize_firebase()
user_collection = "users"

@app.route('/api/update_invoice', methods=['POST'])
def update_invoice():
    return update_invoice_route()

# ✅ Process invoice route
@app.route("/api/process", methods=["POST"])
def process_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    email = request.form.get("email") or request.headers.get("X-User-Email")
    if not email:
        return jsonify({"error": "User email is required"}), 400

    logger.info(f"🔍 Processing invoice for email: {email}")
    try:
        image_data = file.read()
        result = process_invoice(image_data)

        if not result:
            return jsonify({"error": "Failed to process invoice, no data returned from Gemini."}), 500

        required_keys = ["invoice_no", "date", "issued_to", "pay_to", "items"]
        missing_keys = [key for key in required_keys if key not in result]
        if missing_keys:
            return jsonify({"error": f"Missing invoice fields: {', '.join(missing_keys)}"}), 400

        users_ref = db.collection(user_collection)
        query = users_ref.where("email", "==", email).limit(1).get()

        if not query:
            logger.info(f"👤 Creating new user for: {email}")
            new_user = {"email": email, "created_at": datetime.datetime.now(datetime.timezone.utc)}
            user_doc_ref = users_ref.document()
            user_doc_ref.set(new_user)
            user_doc_id = user_doc_ref.id
        else:
            user_doc_id = query[0].id
            logger.info(f"✅ Found user doc ID: {user_doc_id}")

        invoice_id = (result.get("invoice_no") or str(uuid.uuid4())).replace('/', '_')
        result["invoice_no"] = invoice_id

        invoice_ref = db.collection(user_collection).document(user_doc_id).collection("invoices").document(invoice_id)
        if invoice_ref.get().exists:
            return jsonify({"message": "Invoice already uploaded."}), 409

        invoice_ref.set(result)
        logger.info("📄 Storing invoice in Google Sheet...")

        # Pass email as argument to insert_into_sheet
        sheet_result = insert_into_sheet(result, email)

        if sheet_result == "Already uploaded":
            return jsonify({"message": "Invoice already uploaded."}), 409
        elif sheet_result == "Failed":
            logger.warning("⚠️ Stored in Firebase but failed to insert into Google Sheets.")
            return jsonify({
                "message": "Stored in Firebase but failed to insert into Google Sheets.",
                "data": result
            }), 207
        else:
            logger.info("✅ Invoice successfully inserted into Google Sheet.")

        return jsonify({"message": "Invoice stored successfully", "data": result}), 200

    except Exception as e:
        logger.exception("🔥 Error processing invoice")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# ✅ Get invoices for user
@app.route("/api/invoices", methods=["GET"])
def get_invoices():
    logger.info("📥 /api/invoices route hit")
    email = request.args.get("email") or request.headers.get("X-User-Email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    try:
        users_ref = db.collection(user_collection)
        query = users_ref.where("email", "==", email).limit(1).get()

        if not query:
            return jsonify({"invoices": []}), 200

        user_doc_id = query[0].id
        invoices_ref = db.collection(user_collection).document(user_doc_id).collection("invoices")
        invoices = [doc.to_dict() for doc in invoices_ref.stream()]

        return jsonify(invoices), 200

    except Exception as e:
        logger.exception("❌ Error fetching invoices")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# ✅ Health check route
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "✅ Flask server is alive"}), 200

# ✅ Register profile route
app.add_url_rule("/get_profile", view_func=get_profile_route, methods=["GET"])
    


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
