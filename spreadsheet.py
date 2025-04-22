import datetime
import logging
import gspread
from firebase_admin import firestore
import firebase_admin
from firebase_admin import credentials
import os, json

# Setup logger
logger = logging.getLogger("spreadsheet")
logging.basicConfig(level=logging.INFO)

# Spreadsheet ID from URL: https://docs.google.com/spreadsheets/d/<ID>/edit
SPREADSHEET_ID = "1oHZaMlRgjshM-iQmB05l7ph-3tb_fRtGKeBKY-8OzqI"

# Initialize gspread with service account
gs_json = os.getenv("GOOGLE_CREDS_JSON")
if not gs_json:
    raise RuntimeError("Set the GOOGLE_CREDS_JSON env var")
gs_credentials_dict = json.loads(gs_json)
# Create a Client object—NOT just a dict
gc = gspread.service_account_from_dict(gs_credentials_dict)

# Setup Firebase Admin SDK
fb_json = os.getenv("FIREBASE_CREDS_JSON")
if not fb_json:
    raise RuntimeError("Set the FIREBASE_CREDS_JSON env var")
fb_creds = json.loads(fb_json)
cred = credentials.Certificate(fb_creds)
firebase_admin.initialize_app(cred)
# firebase_admin.initialize_app(cred)

# Open spreadsheet by ID
spreadsheet = gc.open_by_key(SPREADSHEET_ID)
summary_sheet = spreadsheet.worksheet("Sheet1")
item_sheet = spreadsheet.worksheet("Sheet2")

# Initialize Firestore client
db = firestore.client()

def safe_get(data, keys):
    """Safely get nested data."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, "")
        else:
            return ""
    return data or ""

def get_party_name(party_data):
    """Return company name if exists, else fallback to name."""
    if not isinstance(party_data, dict):
        return ""
    return party_data.get("company", "") or party_data.get("name", "")

def insert_into_sheet(data, user_email):
    try:
        # Use email as username display (optional: fetch name from Firestore)
        user_name = user_email

        invoice_no = data.get("invoice_no", "")
        timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        current_summary = summary_sheet.get_all_values()
        row_num = len(current_summary) + 1  # insert at next available row

        # Get party details
        bill_to_name = get_party_name(data.get("bill_to", {}))
        vendor_name = get_party_name(data.get("vendor", {}))

        summary_row = [
            f"{row_num - 1:04d}",  # Sr No.
            f"{user_name} ({user_email})",
            timestamp,
            bill_to_name,
            vendor_name,
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
