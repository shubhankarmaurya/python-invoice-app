import os
import uuid
import re
import logging
import base64
import datetime
import json
import zipfile
import io
import magic
import google.generativeai as genai
from flask import jsonify
from dotenv import load_dotenv

# === Setup ===
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Gemini API Setup ===
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-pro")

# === Parse JSON from Gemini Response ===
def parse_json(text):
    try:
        # Look for the JSON inside the text, whether it's marked with ```json or not
        if "```json" in text:
            # Match JSON between ```json and the closing ```
            match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        else:
            # Look for JSON data without the ```json marking
            match = re.search(r"\{.*\}", text, re.DOTALL)

        if not match:
            logger.warning("No JSON found in Gemini response.")
            return None

        # Return the parsed JSON object
        return json.loads(match.group(1 if "```json" in text else 0))

    except Exception as e:
        logger.error(f"JSON parsing failed: {str(e)}")
        return None

def process_invoice(image_data=None, image_path=None):
    try:
        # Check if image_data is provided; if not, read from image_path
        if image_data is None and image_path:
            with open(image_path, 'rb') as file:
                image_data = file.read()

        mime_type = magic.from_buffer(image_data, mime=True)
        if not mime_type.startswith("image/"):
            raise ValueError("Invalid image format")

        image_base64 = base64.b64encode(image_data).decode("utf-8")
        prompt = [
            """You are an invoice data extractor. Extract the following fields in JSON format:

{"vendor": {"name": "", "company": ""}, 
 "invoice_no": "", "date": "", "due_date": "", "vehicle_no": "",
 "bill_to": {"name": "", "company": ""}, 
 "issued_to": {"name": "", "company": ""}, 
 "items": [{"description": "", "unit_price": 0, "quantity": 0, "total": 0, "remark": ""}],
 "subtotal": 0, "tax_percent": 0, "total": 0
} 
""",
            {"mime_type": mime_type, "data": image_base64}
        ]

        response = model.generate_content(prompt)
        data = parse_json(response.text)

        if not data:
            raise ValueError("Failed to parse data from Gemini response")

        # Fallback for missing bill_to
        if not data.get("bill_to") and data.get("issued_to"):
            logger.info("ℹ️ Using issued_to as bill_to since bill_to is missing.")
            data["bill_to"] = data["issued_to"]

        # Ensure required nested fields are initialized
        for key in ["vendor", "bill_to", "issued_to", "pay_to"]:
            if not isinstance(data.get(key), dict):
                data[key] = {"name": "", "company": "", "address": ""}

        if "items" not in data or not isinstance(data["items"], list):
            data["items"] = []

        # Add timestamp
        data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Clean empty fields recursively
        def clean_empty(d):
            if isinstance(d, dict):
                return {k: clean_empty(v) for k, v in d.items() if v not in ("", None, [], {}, 0)}
            elif isinstance(d, list):
                return [clean_empty(i) for i in d if i not in ("", None, [], {}, 0)]
            return d

        return clean_empty(data)

    except Exception as e:
        logger.error(f"Invoice processing failed: {str(e)}")
        return None

# === Process ZIP Archive ===
def process_uploaded_zip(zipfile_data=None, zipfile_path=None):
    try:
        # If zipfile_data is not provided, open the file from the zipfile_path
        if zipfile_data is None and zipfile_path:
            with open(zipfile_path, 'rb') as file:
                zipfile_data = file.read()

        zip_file = zipfile.ZipFile(io.BytesIO(zipfile_data))
        extracted_files = []

        for file_name in zip_file.namelist():
            if file_name.endswith('/'):
                continue  # Skip directories

            with zip_file.open(file_name) as file:
                if file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf')):  # Modify extensions as needed
                    image_data = file.read()
                    extracted_files.append({"file_name": file_name, "data": image_data})
                else:
                    logger.warning(f"Skipping unsupported file: {file_name}")

        results = []
        for extracted_file in extracted_files:
            file_data = extracted_file["data"]
            result = process_invoice(image_data=file_data)
            if result:
                results.append(result)

        return {"status": "success", "results": results}

    except Exception as e:
        logger.error(f"Error extracting ZIP contents: {str(e)}")
        return {"error": f"An unexpected error occurred while processing the ZIP file: {str(e)}"}

# === Process Multiple Invoices ===
def process_multiple_invoices(image_data_list=None, image_path_list=None):
    try:
        results = []

        # Process a list of images passed as data
        if image_data_list:
            for image_data in image_data_list:
                result = process_invoice(image_data=image_data)
                if result:
                    results.append(result)

        # Process a list of image paths
        if image_path_list:
            for image_path in image_path_list:
                with open(image_path, 'rb') as file:
                    image_data = file.read()
                result = process_invoice(image_data=image_data)
                if result:
                    results.append(result)

        return {"status": "success", "results": results}

    except Exception as e:
        logger.error(f"Error processing multiple invoices: {str(e)}")
        return {"error": f"An unexpected error occurred while processing the invoices: {str(e)}"}
