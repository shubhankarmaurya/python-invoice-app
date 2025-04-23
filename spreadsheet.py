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

# Check for alternative environment variable names
def get_credentials_json():
    """Try different environment variable names for credentials"""
    possible_vars = [
        # "GOOGLE_APPLICATION_CREDENTIALS_JSON",
        "GOOGLE_CREDS_JSON",
        # "GOOGLE_CREDENTIALS",
        # "GOOGLE_SERVICE_ACCOUNT"
    ]
    
    for var_name in possible_vars:
        creds = os.getenv(var_name)
        if creds:
            logger.info(f"Found credentials in {var_name}")
            return creds
    
    # Check if credentials.json file exists as fallback
    if os.path.exists("credentials.json"):
        logger.info("Using credentials.json file")
        with open("credentials.json", "r") as f:
            return f.read()
            
    return None

# List all environment variables for debugging (except sensitive ones)
def log_environment():
    logger.info("Environment variables:")
    for key in os.environ:
        if not any(sensitive in key.lower() for sensitive in ["key", "secret", "password", "token", "cred"]):
            logger.info(f"  {key}: {os.environ[key]}")
        else:
            logger.info(f"  {key}: [REDACTED]")

try:
    # Log environment variables for debugging
    log_environment()
    
    # Get credentials JSON
    gs_json = get_credentials_json()
    
    if not gs_json:
        logger.error("No Google credentials found in environment variables or credentials.json")
        raise RuntimeError("No Google credentials found")
    
    # Log first few characters for debugging
    logger.info(f"Credentials string starts with: {gs_json[:20]}...")
    
    # Try to manually create a valid JSON if needed
    if not gs_json.strip().startswith('{'):
        logger.warning("Credentials don't appear to be valid JSON, attempting to create manually")
        # Create a fallback credentials
        fallback_creds = {
            "type": "service_account",
            "project_id": "invoice-455918",
            "private_key_id": "83f09dbe6ab602582a0b45e1b837f4d64f2d2e8c",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCbNHlKGB28e9jl\n7ResWNm4zF4KA/vVWzPQjlsj8CL+fU5WBqvjIDctPNb311Q2Ak6LsOJwDqzj8jZp\neZRMp+H16a5DwrVISe2/60k0TggsAtsKZfC85y/5+nWN9km4MVpsbaNsBxIrqXRZ\nH4IefUt2VYk5XebKNQMqsy7KuutWxCdztZmVXI+m6rvnA9A1wW+GJ5/9HcU50Qnz\nPYRm9dbU9CXlVf/bhqVLO/Eel3Bvl5IK17f5DjQB4WMK92mq5PFNCRCGF5Q6tEO/\nLTWE8Ap9NbKP0aa2jUeF+NfA3Udolr8QxaZwpODigbXcmcoIh1e226u5gcRQSyJw\nJhqXkBBhAgMBAAECggEAIO4MQfVF8eTRC0+3syCS6UurNDLOLuGP59MccU6VDivm\nAAigVatTKaz760/rlR3+LlNUZ/QlKKQOeWiLV4xTPArdp5DbR8AvyoWQXaGkyDm+\n4cDpSBtBKafDY2B7GbKW/eRxRQ1nBI6KmhI+WFu7NBtH5z0OJ58B0gB8kBUCs8DM\nBY7MKQY/FSatC/gxBMXbO+lf5HAgVFiMkvPuD04necF8wR+3udcTJPg0qRg7pUhK\nm807I5HGQZa/OFvfhidueaQT/CU2WMiIurFEX/rxErc/mqJ6eIFfjmnW7c9FrNN+\nwr38TfrHs9fX/8sVeZvuB4180k7h5UZGGMvR7paRBQKBgQDMXqcRMSgZM6KIOwts\nQglYw05TjBTKB6hHNEvqQrzQ29I1mJogAdzvsoeL34jyJdKH8vGWB5rJXErLXUfg\nMymHybRHx8iFlFiuHzGFlAsow4rw/106nn0KbFLjNUv7YdVdoWeyS+/ZPoV9GCPr\nc7qXZJErBtG4B8l5LhjJWGwfLwKBgQDCaidyk/3RZD63eubKQriyQv594KiRqE10\nYYTU8NWu/ArJf0yabo2wSx2jNgTZ1bXMI8uRLxdd2EEY08HW3ZSgtPAMSbXojuxW\nglLcRO7N2RtB9lZ3V9vziQHH/3V4NcqcqF7726uqKINusunetz0ZgxtFxPAmbGd0\nuy1bXW9lbwKBgQCy0IahNj99fX5ScEcYW9dNwOVBmKl/8587XfimaepHXG7a0kDY\njIjBeZW7vsRWCt3gcaMLwG+gi44tzdpbwqgt1UBWJem/ZwMIpuZvmA8DhcSGBQmP\nhqilfA4yGqn2s606lUTj7ilYDapCv+J92u6CFE4oNXk96iJQUxMA6MsBpQKBgFH4\nUAmPPEU87vSNbSF6YEVI2eRZBLnlLEMVmtvtbysIOcQbWEEEu9jI0wYtkH4IDU61\nCO9922xF8ax2HBRr+G6J22xS58/V8u/GowkcR1OjZkq5gltvP92+tnGM1AqLI5JJ\nq0KlrAtiaYgTB2hP+gL3tFgGYPrSWgxtnwIWsxEhAoGBAIKvOxTeQA6j/dBjDihw\nmumCvDbVeXmKVgDkrRR/C0OII2HuE1IBKcmLbw2i2XB2Eo9fSNfSTy4GKeWLyXRb\npm8yVWxMH8d/i/ntpNcEK0F4FOTaHklQBWI00c1TI649TLSz/V+/mNkphwa2Hd8G\nyP18NGWEsGEIJGCOuxU0XTHQ\n-----END PRIVATE KEY-----\n",
            "client_email": "vv-73-410@invoice-455918.iam.gserviceaccount.com",
            "client_id": "109131629475729216390",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/vv-73-410%40invoice-455918.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com"
        }
        gs_creds = fallback_creds
        logger.info("Using fallback credentials")
    else:
        # Parse JSON
        try:
            gs_creds = json.loads(gs_json)
            logger.info("Successfully parsed credentials JSON")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON credentials: {e}")
            logger.error(f"Credentials string: {gs_json}")
            raise
    
    # Normalize the private key
    pk = gs_creds.get("private_key", "")
    if "\\n" in pk:
        gs_creds["private_key"] = pk.replace("\\n", "\n")
    gs_creds["private_key"] = gs_creds["private_key"].strip()
    
    # Build the gspread client
    try:
        gc = gspread.service_account_from_dict(gs_creds)
        logger.info("Successfully created gspread client")
        
        # Test connection by opening spreadsheet
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        summary_sheet = spreadsheet.worksheet("Sheet1")
        item_sheet = spreadsheet.worksheet("Sheet2")
        logger.info("Successfully connected to Google Sheets")
    except Exception as e:
        logger.error(f"Error connecting to Google Sheets: {e}")
        # Create dummy sheets for testing
        class DummySheet:
            def get_all_values(self):
                return []
            def update(self, range, values):
                logger.info(f"Would update {range} with {values}")
                return True
        
        spreadsheet = None
        summary_sheet = DummySheet()
        item_sheet = DummySheet()
        logger.warning("Using dummy sheets for testing")
    
    
    # Setup Firebase if credentials exist
    try:
        fb_json = os.getenv("FIREBASE_CREDS_JSON") or os.getenv("FIREBASE_CREDENTIALS_JSON")
        if fb_json:
            fb_creds = json.loads(fb_json)
            if "private_key" in fb_creds:
                pk = fb_creds["private_key"]
                if "\\n" in pk:
                    fb_creds["private_key"] = pk.replace("\\n", "\n")
                fb_creds["private_key"] = fb_creds["private_key"].strip()
            
            cred = credentials.Certificate(fb_creds)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            logger.info("Successfully connected to Firebase")
        else:
            logger.warning("No Firebase credentials found, Firebase functionality disabled")
            db = None
    except Exception as e:
        logger.error(f"Error setting up Firebase: {e}")
        db = None

except json.JSONDecodeError as e:
    logger.error(f"❌ Error parsing JSON credentials: {e}")
    logger.debug(f"First 100 chars of credentials: {gs_json[:100] if gs_json else 'None'}")
    raise
except Exception as e:
    logger.error(f"❌ Error during initialization: {e}")
    raise

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

def insert_into_sheet(data, user_email="unknown@example.com"):
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
