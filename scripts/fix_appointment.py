"""
fix_appointment.py — Fix appointment document to match what patient dashboard queries
The patient dashboard queries:
  - where('healthId', '==', healthId)   <-- needs 'healthId' field
  - apt.datetime                         <-- needs single 'datetime' string
  - apt.doctorName, apt.hospitalName, apt.reason, apt.status
"""
import sys
sys.path.insert(0, 'backend')
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

if not firebase_admin._apps:
    cred = credentials.Certificate('backend/serviceAccountKey.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

DOCTOR_UID        = 'tOeW20ZvjVSfXWFSO5irl2E90tO2'
HOSPITAL_UID      = 'kLvfA1vox2amigADh6tPdN7OtEz2'
PATIENT_HEALTH_ID = 'DHI-2026-5164'
PATIENT_UID       = 'YCM0kW8lGOQiVf5yKXUIoFnzagq2'
APPT_ID           = 'G8ojnPyVxn23Pz5POVbF'

# Tomorrow's appointment at 10:30 AM — as ISO datetime string
tomorrow = (datetime.now()).strftime('%Y-%m-%d')
appt_datetime = f'2026-08-07T10:30:00'   # ISO string: what new Date(apt.datetime) expects

# Update the existing appointment with correct fields
db.collection('appointments').document(APPT_ID).set({
    # Fields the PATIENT dashboard needs
    'healthId':       PATIENT_HEALTH_ID,       # patient dashboard queries this
    'datetime':       appt_datetime,           # patient dashboard reads new Date(apt.datetime)
    'doctorName':     'Dr. Arjun Mehta',
    'hospitalName':   'Apollo City Hospital',
    'reason':         'Cardiac Wellness Checkup & ECG Review',
    'status':         'scheduled',

    # Fields the DOCTOR dashboard needs
    'healthId':       PATIENT_HEALTH_ID,
    'doctorId':       DOCTOR_UID,
    'hospitalId':     HOSPITAL_UID,

    # Extra context fields
    'patientUid':     PATIENT_UID,
    'patientName':    'Ananya Sharma',
    'patientHealthId': PATIENT_HEALTH_ID,
    'date':           '2026-08-07',
    'time':           '10:30 AM',
    'type':           'OPD',
    'fee':            800,
    'notes':          'Patient advised to get fasting blood test done before appointment. Bring previous ECG reports.',
    'createdBy':      'doctor',
    'createdAt':      firestore.SERVER_TIMESTAMP
}, merge=True)

print(f'Appointment {APPT_ID} updated with correct fields')
print(f'  healthId: {PATIENT_HEALTH_ID}')
print(f'  datetime: {appt_datetime}')
print(f'  status: scheduled')
print()

# Create a SECOND appointment from the doctor dashboard format too
appt2_ref = db.collection('appointments').add({
    'healthId':       PATIENT_HEALTH_ID,
    'datetime':       '2026-08-10T14:00:00',
    'doctorId':       DOCTOR_UID,
    'doctorName':     'Dr. Arjun Mehta',
    'hospitalId':     HOSPITAL_UID,
    'hospitalName':   'Apollo City Hospital',
    'reason':         'Follow-up: Post ECG Review & Medication Plan',
    'status':         'scheduled',
    'patientUid':     PATIENT_UID,
    'patientName':    'Ananya Sharma',
    'patientHealthId': PATIENT_HEALTH_ID,
    'type':           'OPD',
    'fee':            800,
    'createdBy':      'doctor',
    'createdAt':      firestore.SERVER_TIMESTAMP
})
print(f'Second appointment created: {appt2_ref[1].id}')
print(f'  datetime: 2026-08-10T14:00:00')
print(f'  reason: Follow-up appointment')
print()
print('All appointment data is now correct.')
print()
print('SUMMARY - Test Login Credentials:')
print('  PATIENT:  testpatient2026@swasthya.com  / Patient@123')
print('  DOCTOR:   dr.arjun.mehta@swasthya.com  / Doctor@123')
print('  HOSPITAL: apollo.bhopal@swasthya.com   / Hospital@123')
