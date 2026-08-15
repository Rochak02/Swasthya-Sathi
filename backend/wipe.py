import os
import firebase_admin
from firebase_admin import credentials, auth, firestore

# Initialize Firebase Admin
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

def delete_all_auth_users():
    print("Deleting all Auth users (skipping admin)...")
    page = auth.list_users()
    while page:
        for user in page.users:
            if user.email == "admin@swasthya.com":
                print(f"Skipping admin user: {user.uid} ({user.email})")
                continue
            print(f"Deleting auth user: {user.uid} ({user.email})")
            auth.delete_user(user.uid)
        page = page.get_next_page()
    print("All Auth users deleted.")

def wipe_firestore():
    print("Wiping Firestore collections...")
    
    admin_uid = None
    try:
        admin_user = auth.get_user_by_email("admin@swasthya.com")
        admin_uid = admin_user.uid
    except Exception:
        pass

    collections = ['users', 'patients', 'hospitals', 'laboratories', 'doctors', 'advertisers', 'advertisements', 'accessLinks']
    for coll in collections:
        print(f"--- Deleting collection: {coll} ---")
        docs = db.collection(coll).stream()
        for doc in docs:
            if coll == 'users' and doc.id == admin_uid:
                print(f"Skipping admin doc {doc.id} in {coll}")
                continue
            print(f"Deleting doc {doc.id} => {coll}")
            doc.reference.delete()
            
    print("Firestore wipe complete.")

if __name__ == "__main__":
    print("Starting Firebase Wipe (Except Admin)...")
    delete_all_auth_users()
    wipe_firestore()
    print("Done!")
