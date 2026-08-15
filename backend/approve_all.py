import os
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin
SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"
if Path(SERVICE_ACCOUNT_PATH).exists():
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    print("serviceAccountKey.json not found")
    exit(1)

def approve_all():
    # Approve Hospitals
    hospitals = db.collection('hospitals').where('verified', '==', False).stream()
    for h in hospitals:
        db.collection('hospitals').document(h.id).update({'verified': True})
        print(f"Verified hospital: {h.id}")

    # Approve Labs
    labs = db.collection('laboratories').where('verified', '==', False).stream()
    for l in labs:
        db.collection('laboratories').document(l.id).update({'verified': True})
        print(f"Verified lab: {l.id}")

    # Approve Ads
    ads = db.collection('advertisements').where('status', '==', 'pending').stream()
    for ad in ads:
        db.collection('advertisements').document(ad.id).update({'status': 'approved'})
        print(f"Approved ad: {ad.id}")

if __name__ == "__main__":
    approve_all()
    print("All pending accounts and ads verified successfully.")
