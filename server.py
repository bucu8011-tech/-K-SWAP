import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify

app = Flask(__name__)
db = None

try:
    config = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if config:
        cred = credentials.Certificate(json.loads(config))
        firebase_admin.initialize_app(cred)
        db = firestore.client()
except Exception as e:
    print("Firebase setup error:", e)

@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "game": "K-SWAP",
        "firebase": "connected" if db else "not_configured"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
