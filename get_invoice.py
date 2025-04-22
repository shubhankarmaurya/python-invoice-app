from flask import request, jsonify
import logging
import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("FIREBASE_CREDS_JSON.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
user_collection = "users"

def get_invoices():
    email = request.args.get("email") or request.headers.get("X-User-Email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    try:
        users_ref = db.collection(user_collection)
        query = users_ref.where("email", "==", email).limit(1).get()

        if not query:
            return jsonify({"invoices": []}), 200

        user_doc = query[0]
        user_doc_id = user_doc.id
        invoices_ref = db.collection(user_collection).document(user_doc_id).collection("invoices")
        invoices = [doc.to_dict() for doc in invoices_ref.stream()]

        return jsonify(invoices), 200

    except Exception as e:
        logger.exception("Error fetching invoices")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
