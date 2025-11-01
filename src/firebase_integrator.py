import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

db = None

def initialize_firebase():
    global db
    if db is not None:
        print("--- Firebase already initialized. ---")
        return

    # Check for Firebase credentials in environment variable
    firebase_credentials_json = os.getenv('FIREBASE_CREDENTIALS_JSON')

    if firebase_credentials_json:
        try:
            # Load credentials from JSON string
            cred = credentials.Certificate(json.loads(firebase_credentials_json))
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("--- Firebase initialized successfully from environment variable. ---")
        except Exception as e:
            print(f"FATAL ERROR initializing Firebase from environment variable: {e}")
            db = None
    else:
        print("--- Firebase credentials (FIREBASE_CREDENTIALS_JSON) not found in environment. Skipping Firebase initialization. ---")
        db = None

def save_test_cases_to_firebase(test_cases: list, collection_name: str = "test_cases"):
    if db is None:
        print("--- Firebase not initialized. Cannot save test cases. ---")
        return ["Firebase not initialized. Cannot save test cases."]

    confirmations = []
    try:
        batch = db.batch()
        for tc in test_cases:
            # Firestore automatically generates document IDs if not provided
            doc_ref = db.collection(collection_name).document()
            batch.set(doc_ref, tc)
        batch.commit()
        confirmations.append(f"Successfully saved {len(test_cases)} test cases to Firestore collection '{collection_name}'.")
        print(f"--- Successfully saved {len(test_cases)} test cases to Firestore. ---")
    except Exception as e:
        error_message = f"Error saving test cases to Firebase: {e}"
        print(f"--- {error_message} ---")
        confirmations.append(error_message)
    return confirmations
