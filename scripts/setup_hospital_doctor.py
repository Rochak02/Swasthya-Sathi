"""
setup_hospital_doctor.py
========================
Creates a complete test ecosystem:
  1. Hospital  — Apollo City Hospital, Bhopal
  2. Doctor    — Dr. Arjun Mehta (Cardiologist), assigned to that hospital
  3. AccessLink — Patient Ananya Sharma linked to the hospital
  4. Appointment — Doctor sends appointment to patient
  5. Approves hospital & doctor (verified = True)

Run: python setup_hospital_doctor.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# ── Bootstrap Firebase Admin ──────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore

SERVICE_KEY = Path(__file__).parent / "backend" / "serviceAccountKey.json"
if not firebase_admin._apps:
    cred = credentials.Certificate(str(SERVICE_KEY))
    firebase_admin.initialize_app(cred)

db = firestore.client()
print("✅ Firebase Admin connected\n")

# ──────────────────────────────────────────────────────────────────────────────
# STEP 1: Create Hospital Account
# ──────────────────────────────────────────────────────────────────────────────
print("━" * 55)
print("STEP 1: Creating Hospital Account")
print("━" * 55)

HOSPITAL_EMAIL    = "apollo.bhopal@swasthya.com"
HOSPITAL_PASSWORD = "Hospital@123"
HOSPITAL_NAME     = "Apollo City Hospital"

try:
    hosp_user = firebase_auth.create_user(
        email=HOSPITAL_EMAIL,
        password=HOSPITAL_PASSWORD,
        display_name=HOSPITAL_NAME
    )
    print(f"  Auth user created: {hosp_user.uid}")
except firebase_admin.exceptions.AlreadyExistsError:
    hosp_user = firebase_auth.get_user_by_email(HOSPITAL_EMAIL)
    print(f"  Hospital already exists, using: {hosp_user.uid}")

HOSPITAL_UID = hosp_user.uid

# Write users/{uid}
db.collection("users").document(HOSPITAL_UID).set({
    "email":     HOSPITAL_EMAIL,
    "role":      "hospital",
    "verified":  True,
    "name":      HOSPITAL_NAME,
    "createdAt": firestore.SERVER_TIMESTAMP
})

# Write hospitals/{uid}
db.collection("hospitals").document(HOSPITAL_UID).set({
    "uid":                HOSPITAL_UID,
    "name":               HOSPITAL_NAME,
    "email":              HOSPITAL_EMAIL,
    "phone":              "07554001234",
    "address":            "Plot 12, MP Nagar Zone-II, Bhopal, Madhya Pradesh 462011",
    "registrationNumber": "REG-HOSP-MP-2019-4521",
    "type":               "Private",
    "verified":           True,
    "totalBeds":          350,
    "departments":        ["Cardiology", "Orthopedics", "Neurology", "General Medicine", "Pediatrics"],
    "createdAt":          firestore.SERVER_TIMESTAMP
})

print(f"  ✅ Hospital '{HOSPITAL_NAME}' created & verified")
print(f"     UID:   {HOSPITAL_UID}")
print(f"     Email: {HOSPITAL_EMAIL}")
print(f"     Pass:  {HOSPITAL_PASSWORD}\n")

# ──────────────────────────────────────────────────────────────────────────────
# STEP 2: Create Doctor Account
# ──────────────────────────────────────────────────────────────────────────────
print("━" * 55)
print("STEP 2: Creating Doctor Account")
print("━" * 55)

DOCTOR_EMAIL    = "dr.arjun.mehta@swasthya.com"
DOCTOR_PASSWORD = "Doctor@123"
DOCTOR_NAME     = "Dr. Arjun Mehta"

try:
    doc_user = firebase_auth.create_user(
        email=DOCTOR_EMAIL,
        password=DOCTOR_PASSWORD,
        display_name=DOCTOR_NAME
    )
    print(f"  Auth user created: {doc_user.uid}")
except firebase_admin.exceptions.AlreadyExistsError:
    doc_user = firebase_auth.get_user_by_email(DOCTOR_EMAIL)
    print(f"  Doctor already exists, using: {doc_user.uid}")

DOCTOR_UID = doc_user.uid

# Write users/{uid} for doctor (this is what the doctor dashboard reads)
db.collection("users").document(DOCTOR_UID).set({
    "name":               DOCTOR_NAME,
    "email":              DOCTOR_EMAIL,
    "role":               "doctor",
    "specialization":     "Cardiology",
    "licenseNumber":      "MCI-2018-112233",
    "affiliatedHospitals": [HOSPITAL_UID],
    "hospitalName":       HOSPITAL_NAME,
    "hospitalUid":        HOSPITAL_UID,
    "fee":                800,
    "experience":         "12 Yrs",
    "rating":             4.8,
    "reviewsCount":       127,
    "verified":           True,
    "createdAt":          firestore.SERVER_TIMESTAMP
})

print(f"  ✅ Doctor '{DOCTOR_NAME}' created & verified")
print(f"     UID:   {DOCTOR_UID}")
print(f"     Email: {DOCTOR_EMAIL}")
print(f"     Pass:  {DOCTOR_PASSWORD}")
print(f"     Hospital: {HOSPITAL_NAME}\n")

# ──────────────────────────────────────────────────────────────────────────────
# STEP 3: Assign Patient to Hospital (AccessLink)
# ──────────────────────────────────────────────────────────────────────────────
print("━" * 55)
print("STEP 3: Assigning Patient to Hospital")
print("━" * 55)

# Patient data from earlier registration
PATIENT_HEALTH_ID = "DHI-2026-5164"
PATIENT_NAME      = "Ananya Sharma"
PATIENT_UID       = "YCM0kW8lGOQiVf5yKXUIoFnzagq2"

# Verify patient exists
pat_doc = db.collection("patients").document(PATIENT_HEALTH_ID).get()
if pat_doc.exists:
    print(f"  Patient found: {PATIENT_NAME} ({PATIENT_HEALTH_ID})")
else:
    print(f"  ⚠️  Patient doc not found at patients/{PATIENT_HEALTH_ID} — creating it...")
    # Find patient uid from users collection
    users_ref = db.collection("users").document(PATIENT_UID).get()
    if users_ref.exists:
        PATIENT_HEALTH_ID = users_ref.to_dict().get("healthId", PATIENT_HEALTH_ID)

# Create access link — hospital can see patient records
ACCESS_LINK_ID = f"{HOSPITAL_UID}_{PATIENT_HEALTH_ID}"
db.collection("accessLinks").document(ACCESS_LINK_ID).set({
    "healthId":     PATIENT_HEALTH_ID,
    "patientName":  PATIENT_NAME,
    "patientUid":   PATIENT_UID,
    "hospitalId":   HOSPITAL_UID,
    "hospitalName": HOSPITAL_NAME,
    "doctorId":     DOCTOR_UID,
    "doctorName":   DOCTOR_NAME,
    "status":       "active",
    "grantedAt":    firestore.SERVER_TIMESTAMP
})

print(f"  ✅ Patient '{PATIENT_NAME}' linked to '{HOSPITAL_NAME}'")
print(f"     AccessLink ID: {ACCESS_LINK_ID}")
print(f"     Status: active\n")

# ──────────────────────────────────────────────────────────────────────────────
# STEP 4: Doctor sends Appointment to Patient
# ──────────────────────────────────────────────────────────────────────────────
print("━" * 55)
print("STEP 4: Doctor Creates Appointment for Patient")
print("━" * 55)

# Appointment scheduled for tomorrow at 10:30 AM
tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
appt_time = "10:30 AM"

appt_ref = db.collection("appointments").add({
    "patientUid":      PATIENT_UID,
    "patientName":     PATIENT_NAME,
    "patientHealthId": PATIENT_HEALTH_ID,
    "doctorUid":       DOCTOR_UID,
    "doctorName":      DOCTOR_NAME,
    "hospitalUid":     HOSPITAL_UID,
    "hospitalName":    HOSPITAL_NAME,
    "specialization":  "Cardiology",
    "date":            tomorrow,
    "time":            appt_time,
    "reason":          "Cardiac Wellness Checkup & ECG Review",
    "status":          "confirmed",
    "type":            "OPD",
    "fee":             800,
    "notes":           "Patient advised to get fasting blood test done before appointment. Bring previous ECG reports.",
    "createdBy":       "doctor",
    "createdAt":       firestore.SERVER_TIMESTAMP
})

appt_id = appt_ref[1].id
print(f"  ✅ Appointment Created!")
print(f"     ID:      {appt_id}")
print(f"     Doctor:  {DOCTOR_NAME} (Cardiologist)")
print(f"     Patient: {PATIENT_NAME}")
print(f"     Date:    {tomorrow} at {appt_time}")
print(f"     Reason:  Cardiac Wellness Checkup & ECG Review")
print(f"     Status:  confirmed\n")

# ──────────────────────────────────────────────────────────────────────────────
# STEP 5: Update Patient Overview Stats
# ──────────────────────────────────────────────────────────────────────────────
print("━" * 55)
print("STEP 5: Updating Patient Stats")
print("━" * 55)

# Update the patient doc with hospital visit info
pat_ref = db.collection("patients").document(PATIENT_HEALTH_ID)
pat_ref.set({
    "lastVisitedHospital": HOSPITAL_NAME,
    "lastVisitedDate": tomorrow,
    "hospitalsVisited": firestore.Increment(1),
    "upcomingAppointmentId": appt_id,
    "upcomingAppointmentDate": tomorrow,
    "upcomingAppointmentTime": appt_time,
    "upcomingAppointmentDoctor": DOCTOR_NAME,
    "upcomingAppointmentHospital": HOSPITAL_NAME
}, merge=True)

print(f"  ✅ Patient profile updated with appointment info\n")

# ──────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────────────────────────
print("=" * 55)
print("🎉  ALL DONE — Test Ecosystem Created")
print("=" * 55)
print()
print("🏥 HOSPITAL")
print(f"   Name:  {HOSPITAL_NAME}")
print(f"   Email: {HOSPITAL_EMAIL}")
print(f"   Pass:  {HOSPITAL_PASSWORD}")
print(f"   UID:   {HOSPITAL_UID}")
print()
print("👨‍⚕️ DOCTOR")
print(f"   Name:  {DOCTOR_NAME}")
print(f"   Spec:  Cardiology")
print(f"   Email: {DOCTOR_EMAIL}")
print(f"   Pass:  {DOCTOR_PASSWORD}")
print(f"   UID:   {DOCTOR_UID}")
print()
print("🧑‍💼 PATIENT")
print(f"   Name:      {PATIENT_NAME}")
print(f"   Health ID: {PATIENT_HEALTH_ID}")
print(f"   Email:     testpatient2026@swasthya.com")
print()
print("📅 APPOINTMENT")
print(f"   Date:   {tomorrow} at {appt_time}")
print(f"   Doctor: {DOCTOR_NAME}")
print(f"   Reason: Cardiac Wellness Checkup & ECG Review")
print(f"   Status: confirmed")
print()
print("Next steps — Test in browser:")
print("  1. Login as Patient  → http://localhost:8080/login.html")
print("  2. Login as Doctor   → same URL (email/pass above)")
print("  3. Login as Hospital → same URL (email/pass above)")
