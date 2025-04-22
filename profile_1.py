from flask import request, jsonify
from firebase_admin import firestore

user_collection = "users"

def get_profile_route():
    try:
        db = firestore.client()
        uid = request.args.get("uid")
        if not uid:
            return jsonify({"error": "Missing UID"}), 400

        doc = db.collection(user_collection).document(uid).get()
        if not doc.exists:
            return jsonify({"error": "User not found"}), 404

        data = doc.to_dict()

        # 🔍 Get Firestore timestamp fields safely
        created_at = data.get("createdAt")
        last_login = data.get("lastLogin")

        # 🕒 Convert to ISO format if they're Firestore Timestamp objects
        data["createdAt"] = created_at.isoformat() if hasattr(created_at, "isoformat") else created_at
        data["lastLogin"] = last_login.isoformat() if hasattr(last_login, "isoformat") else last_login

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
