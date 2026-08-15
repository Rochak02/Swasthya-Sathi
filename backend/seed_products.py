import firebase_admin
from firebase_admin import credentials, firestore
import os

# Initialize Firebase (assuming same setup as main.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(current_dir, 'serviceAccountKey.json')

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

products = [
    {
        'title': 'Vitamin D3 60,000 IU (4 Softgels)',
        'category': 'medicine',
        'provider': 'Apollo Pharmacy Partner',
        'city': 'New Delhi',
        'originalPrice': 240,
        'price': 120,
        'discount': '50% OFF',
        'image': 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=400&q=80',
        'inStock': True
    },
    {
        'title': 'Complete Blood Count (CBC) Test',
        'category': 'lab',
        'provider': 'Dr. Lal PathLabs',
        'city': 'New Delhi',
        'originalPrice': 500,
        'price': 350,
        'discount': '30% OFF',
        'image': 'https://images.unsplash.com/photo-1579154204601-01588f351e67?auto=format&fit=crop&w=400&q=80',
        'inStock': True
    },
    {
        'title': 'Paracetamol 650mg (15 Tablets)',
        'category': 'medicine',
        'provider': 'Wellness Forever',
        'city': 'Mumbai',
        'originalPrice': 45,
        'price': 35,
        'discount': '22% OFF',
        'image': 'https://images.unsplash.com/photo-1631549916768-4119b2e5f926?auto=format&fit=crop&w=400&q=80',
        'inStock': True
    },
    {
        'title': 'Full Body Health Checkup (Comprehensive)',
        'category': 'lab',
        'provider': 'Max Healthcare Labs',
        'city': 'Bengaluru',
        'originalPrice': 3000,
        'price': 1499,
        'discount': '50% OFF',
        'image': 'https://images.unsplash.com/photo-1530497610245-94d3c16cda28?auto=format&fit=crop&w=400&q=80',
        'inStock': True
    },
    {
        'title': 'Digital Thermometer',
        'category': 'equipment',
        'provider': 'MediEquip Supplies',
        'city': 'New Delhi',
        'originalPrice': 350,
        'price': 250,
        'discount': '28% OFF',
        'image': 'https://images.unsplash.com/photo-1584362917165-526a968579e8?auto=format&fit=crop&w=400&q=80',
        'inStock': True
    },
    {
        'title': 'Ayurvedic Immunity Booster (500g)',
        'category': 'wellness',
        'provider': 'Patanjali Ayurveda',
        'city': 'New Delhi',
        'originalPrice': 400,
        'price': 360,
        'discount': '10% OFF',
        'image': 'https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?auto=format&fit=crop&w=400&q=80',
        'inStock': True
    }
]

print("Seeding products into Firestore...")
batch = db.batch()
for p in products:
    doc_ref = db.collection('products').document()
    batch.set(doc_ref, p)
batch.commit()
print("Successfully seeded products!")
