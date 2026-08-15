import firebase_admin
from firebase_admin import credentials, auth, firestore

# Initialize Firebase Admin
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def seed_test_patient():
    email = "testpatient@swasthya.com"
    password = "password123"
    name = "Test Patient"
    
    try:
        user = auth.get_user_by_email(email)
        print(f"User {email} already exists. UID: {user.uid}")
    except firebase_admin.auth.UserNotFoundError:
        user = auth.create_user(email=email, password=password)
        print(f"Created new user {email}. UID: {user.uid}")

    healthId = "DHI-2026-9999"

    # Save to users
    db.collection('users').document(user.uid).set({
        'email': email,
        'role': 'patient',
        'verified': True,
        'createdAt': firestore.SERVER_TIMESTAMP
    })

    # Save to patients
    db.collection('patients').document(healthId).set({
        'personalInfo': {
            'uid': user.uid,
            'name': name,
            'email': email,
            'dob': '12-12-1995',
            'gender': 'Male',
            'phone': '9876543210',
            'address': '123 Test Street, Test City'
        },
        'medicalInfo': {
            'bloodGroup': 'O+',
            'allergies': 'None',
            'chronicConditions': 'None'
        },
        'emergencyContacts': [{
            'name': 'Emergency Contact',
            'relation': 'Friend',
            'phone': '9876543211'
        }],
        'healthId': healthId,
        'createdAt': firestore.SERVER_TIMESTAMP
    })
    print("Seeded patient data to Firestore successfully.")

if __name__ == "__main__":
    seed_test_patient()
