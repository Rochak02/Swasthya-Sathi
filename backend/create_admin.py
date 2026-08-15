import os
import firebase_admin
from firebase_admin import credentials, auth, firestore

# Initialize Firebase Admin
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def create_admin():
    email = "admin@swasthya.com"
    password = "password123"
    
    try:
        user = auth.create_user(email=email, password=password)
        print(f"Created auth user: {user.uid}")
    except auth.EmailAlreadyExistsError:
        user = auth.get_user_by_email(email)
        print(f"User already exists: {user.uid}")
    
    # Write to users collection
    db.collection("users").document(user.uid).set({
        "email": email,
        "role": "admin",
        "createdAt": firestore.SERVER_TIMESTAMP
    })
    print("Admin user created in Firestore.")

if __name__ == "__main__":
    create_admin()
