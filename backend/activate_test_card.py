import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firebase Admin
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def activate_test_card(raw_uid):
    # Find the test patient
    users = list(db.collection('users').where('email', '==', 'testpatient@swasthya.com').get())
    
    if not users:
        print("Test patient not found! Please run 'python seed_patient.py' first.")
        return

    patient_uid = users[0].id
    health_id = "DHI-2026-9999"

    # Delete any existing card with this UID to avoid conflicts
    existing = db.collection('rfid_cards').where('raw_card_uid', '==', raw_uid).get()
    for doc in existing:
        doc.reference.delete()

    # Create an active card directly in the database
    card_doc = {
        "card_code": "SS-TEST-1234",
        "raw_card_uid": raw_uid,
        "patient_uid": patient_uid,
        "health_id": health_id,
        "patient_name": "Test Patient",
        "patient_email": "testpatient@swasthya.com",
        "status": "active",
        "issued_by_admin": "system",
        "issued_at": firestore.SERVER_TIMESTAMP,
        "mailed_at": firestore.SERVER_TIMESTAMP,
        "activated_at": firestore.SERVER_TIMESTAMP
    }

    doc_ref = db.collection("rfid_cards").add(card_doc)
    print(f"Successfully activated test card! Card ID: {doc_ref[1].id}")
    print(f"Now try scanning your RFID card ({raw_uid}) again.")

if __name__ == "__main__":
    activate_test_card("C3:5E:46:39")
