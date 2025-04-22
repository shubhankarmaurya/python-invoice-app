import datetime
import logging
import gspread
from firebase_admin import firestore
import firebase_admin
from firebase_admin import credentials

# Setup logger
logger = logging.getLogger("spreadsheet")
logging.basicConfig(level=logging.INFO)

# Spreadsheet ID
SPREADSHEET_ID = "1oHZaMlRgjshM-iQmB05l7ph-3tb_fRtGKeBKY-8OzqI"

# Initialize gspread with service account
gc = gspread.service_account(filename="credentials.json")

# Setup Firebase Admin SDK
cred = credentials.Certificate("FIREBASE_CREDS_JSON.json")
firebase_admin.initialize_app(cred)

# Open spreadsheet
spreadsheet = gc.open_by_key(SPREADSHEET_ID)
summary_sheet = spreadsheet.worksheet("Sheet1")
item_sheet = spreadsheet.worksheet("Sheet2")

db = firestore.client()
user_collection = "users"

def safe_get(data, keys):
    """Safely get nested data."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, "")
        else:
            return ""
    return data or ""

def insert_into_sheet(data, user_email):
    try:
        # Use the email directly passed from app.py
        user_name = user_email  # If you want to fetch from Firebase, uncomment below
        # user_ref = db.collection(user_collection).where("email", "==", user_email).limit(1).get()
        # if user_ref:
        #     user_doc = user_ref[0]
        #     user_name = user_doc.get('name') or user_email
        # else:
        #     logger.warning(f"⚠️ User not found in Firebase: {user_email}")

        invoice_no = data.get("invoice_no", "")
        timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        current_summary = summary_sheet.get_all_values()
        row_num = len(current_summary) + 1  # insert at next available row

        summary_row = [
            f"{row_num - 1:04d}",  # Sr No.
            f"{user_name} ({user_email})",
            timestamp,
            safe_get(data, ["bill_to", "name"]),
            safe_get(data, ["vendor", "company"]),
            invoice_no,
            data.get("date", ""),
            data.get("vehicle_no", "")
        ]

        logger.debug(f"📊 Writing summary row at row {row_num}: {summary_row}")
        try:
            summary_sheet.update(f"A{row_num}:H{row_num}", [summary_row])
            logger.info("✅ Summary row written.")
        except gspread.exceptions.APIError as api_error:
            logger.exception(f"❌ Failed to write summary row due to API error: {api_error}")
            return f"Failed to write summary row due to API error: {api_error}"
        except Exception as e:
            logger.exception(f"❌ Failed to write summary row due to unexpected error: {e}")
            return f"Failed to write summary row due to unexpected error: {e}"

        # Insert items
        items = data.get("items", [])
        if not isinstance(items, list):
            logger.warning("⚠️ 'items' field is not a list.")
            items = []

        current_items = item_sheet.get_all_values()
        item_row_start = len(current_items) + 1

        for i, item in enumerate(items):
            item_row = [
                item_row_start + i,
                f"{row_num - 1:04d}",  # reference to Sr No.
                item.get("description", ""),
                item.get("quantity", 0),
                item.get("unit_price", 0),
                item.get("remark", "")
            ]
            try:
                item_sheet.update(f"A{item_row_start + i}:F{item_row_start + i}", [item_row])
                logger.debug(f"✅ Written item row #{i + 1}")
            except gspread.exceptions.APIError as api_error:
                logger.exception(f"❌ Failed to write item row #{i + 1} due to API error: {api_error}")
                return f"Failed to write item row #{i + 1} due to API error: {api_error}"
            except Exception as e:
                logger.exception(f"❌ Failed to write item row #{i + 1} due to unexpected error: {e}")
                return f"Failed to write item row #{i + 1} due to unexpected error: {e}"

        return "Inserted"

    except Exception as e:
        logger.exception(f"❌ General error inserting into Google Sheets: {type(e).__name__}: {e}")
        return f"Failed to insert into Google Sheets: {e}"
