import datetime
import logging
import gspread
from firebase_admin import firestore
import firebase_admin
from firebase_admin import credentials

# Setup logger
logger = logging.getLogger("spreadsheet")
logging.basicConfig(level=logging.INFO)

# Spreadsheet ID from URL: https://docs.google.com/spreadsheets/d/<ID>/edit
SPREADSHEET_ID = "1oHZaMlRgjshM-iQmB05l7ph-3tb_fRtGKeBKY-8OzqI"

# Initialize gspread with service account
gc = """{
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
}"""

# Setup Firebase Admin SDK
cred = """{
  "type": "service_account",
  "project_id": "otp-f08ed",
  "private_key_id": "190f531348930811115be47b9e6a4b4bcc142880",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDGHrJWqquw11Tr\nV1O48hFpd3nUxL0RMyqQlumMcmsBol9p78otMXdRrrEzsRczwlVESz011eJW8D7N\nL4faOGwKbdNeU1+md6vIIPJAmZjFt7xRexI/jvO/QfiLQDCQukXMcf4+z2kGOdp2\nAvouFtwwqAxZNUms/oM0vN7V6mqg8oCmkK2tKTqeLULybttwTULciS0oz4b7ybRY\npK3P/qjxi9U64sj6Vv8rT30lR4noDNdni6bvzHyrf7VVcmpE6zZRbZmAHAWXkImU\nfImZl7sBRivUd/g/Atv98bq7l0g2/N/JceWxQ0Io0oLs2Tsq1rj0Xy9sW3A7QfS7\nVv+6dwgTAgMBAAECggEAELNgvC6J54/XUDldzN7W+emA4x8sgukpwuN9z4GLpKkf\n2unERLgBQ2jy9hUNDCdrEaU4BTRA7qw01w4VKR+Nd/mXEkH786ft2qJwWWK5Pp2E\n6edye9ockPhKL87a6TBSlu/bC0dnpoc087K/jSgPKqjX1aNI0STpQYZUUHsAvw1c\nGGedOI+h3E9/YcMF5Vop2/Ef5uenoy31AUO61GuYYRBw33PhtZmzfSLVgTUdA1FZ\n5M26aE0HD/4xKZuj76qqcrpvMqTs9/gAEk6mt4+px/vFKVyuLM6cVO/CzJdhXPoQ\nNk8PLIPEUlf72GTw8C2hvb2v/eDbe1/SWxtKjgZoKQKBgQDyzQnRFvJdG9elHZlo\negsxxbLNd2YVGcVIKB8V7AEUIsmLBd6PaNNXgVOFBBWAsXV2rAvMtpH8XxanbPbE\nJdjKVycB17F7Ll5AM9bAvHhBbyk0gpNvLgl3iLPo+57yZsuP2Mn2mDxtbp9Gb2i+\n8WfuxavE9fD+oBvQpbgFHkZLCQKBgQDQ49nHkFv2mrcgy/Drui1AMB24UKdCWMG1\ngsNEJiSbqI+NMfJC0Fqp9x+wrEbPD5pzGULEjwc7vSokUoQOscDiB/9fa/v+YRaq\nrN1vylCaAFQCmOokBk2PkwKQX1JZ1ATdR7D4jCikk3JRcN5FKwSher8bDr08JKtP\nBVlktjwVOwKBgQCBfWim4p4PmjHAFbEjTzN5L/7UJcGDr2LPwNYTUvKgUo06X776\nrOVJ3ec1IaB2Ki6DQ+5nF1d0SSJD2JEiuyyLfT+IdAhrsacChqMZ12orO6W2I42N\n1femkHmi3889aCVYaj4MDdTsZ/r6DaDHdOgBJ9scCC6nHay38inaUPMcQQKBgQCz\ntBDaefpjgF4ivNAaOyRKoBoxQlFh5nFe8YuCyT2dG7nDQkCj8hLNPWfp2Ytg/o9k\njUq/Rjx2zBnA/avV6F2DFlY/hOpYwLV7RxOI5IfKtJWRVnO3YiS/az09boOt+5Pj\nuZUpfYpJav9hyLOu1X86XBqj8F4jq3gklvl8hrnRmQKBgEKzciMEg9pkRtr6Rmgq\nQSistX7fvrjnNHBUXp/DmY6aOIEGWkqZqt8eGygCsVxFE+xfEWIfxDHr8z+5xagO\nuFzu8DEu8nBjWMzROzjpViU+7iihamW7XQ5JxVpw/I+RT98gkfD9wFj6ksq3xGIL\ntQcPG3soBe84QL9OBwz4OX2m\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-du8o3@otp-f08ed.iam.gserviceaccount.com",
  "client_id": "100293648152219402100",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-du8o3%40otp-f08ed.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}"""
firebase_admin.initialize_app(cred)

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
