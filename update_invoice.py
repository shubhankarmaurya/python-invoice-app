import firebase_admin
from firebase_admin import credentials, firestore
from flask import request, jsonify

FIREBASE_CREDS_JSON = 'FIREBASE_CREDS_JSON.json'  # Path to your Firebase credentials JSON file

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CREDS_JSON)  # Use the path to the Firebase credentials JSON file
    firebase_admin.initialize_app(cred)
else:
    print("Firebase app is already initialized.")

def update_invoice_route():
    try:
        # Get data from the incoming request
        data = request.json
        user_email = data['user_email']
        doc_id = data['doc_id']
        updated_data = data['updated_data']

        # Ensure doc_id is also stored in the document data
        updated_data['doc_id'] = doc_id

        print(f"🔁 Updating invoice for user: {user_email}, doc_id: {doc_id}")
        print("📦 Updated data:", updated_data)

        # --- Update Firestore ---
        db = firestore.client()
        invoice_ref = db.collection('invoices').document(user_email).collection('invoices').document(doc_id)
        
        # Merging the updated data into the document in Firestore
        invoice_ref.set(updated_data, merge=True)  

        print("✅ Invoice updated successfully in Firestore")
        return jsonify({"message": "Invoice updated successfully", "doc_id": doc_id}), 200

    except Exception as e:
        print("🔥 Exception occurred:", str(e))
        return jsonify({"error": str(e)}), 500
