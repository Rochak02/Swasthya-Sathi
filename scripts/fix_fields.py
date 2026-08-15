"""
fix_fields.py — Fix accessLink fields to match what dashboards query
"""
import sys
sys.path.insert(0, 'backend')
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate('backend/serviceAccountKey.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

DOCTOR_UID        = 'tOeW20ZvjVSfXWFSO5irl2E90tO2'
HOSPITAL_UID      = 'kLvfA1vox2amigADh6tPdN7OtEz2'
PATIENT_HEALTH_ID = 'DHI-2026-5164'

# Update BOTH access links to include assignedDoctorId field
# (doctor dashboard queries: where('assignedDoctorId', '==', currentUser.uid))
for link_id in [
    f'{HOSPITAL_UID}_{PATIENT_HEALTH_ID}',
    f'{DOCTOR_UID}_{PATIENT_HEALTH_ID}'
]:
    db.collection('accessLinks').document(link_id).set({
        'assignedDoctorId': DOCTOR_UID,
        'doctorId':         DOCTOR_UID,
        'doctorName':       'Dr. Arjun Mehta',
        'status':           'active',
        'healthId':         PATIENT_HEALTH_ID,
        'patientUid':       'YCM0kW8lGOQiVf5yKXUIoFnzagq2',
        'patientName':      'Ananya Sharma',
        'hospitalId':       HOSPITAL_UID,
        'hospitalName':     'Apollo City Hospital',
    }, merge=True)
    print(f'Updated accessLink: {link_id}')

print()
print('Appointments:')
appts = db.collection('appointments').get()
for a in appts:
    d = a.to_dict()
    print(f'  ID: {a.id}')
    print(f'  Patient: {d.get("patientName")} | Date: {d.get("date")} | Status: {d.get("status")}')
    print(f'  patientUid: {d.get("patientUid")} | healthId: {d.get("patientHealthId")}')
    print()

print('Done! All fields fixed.')
