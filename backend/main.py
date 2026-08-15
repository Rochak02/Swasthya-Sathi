# FastAPI Backend for MediGrid
# Run with: uvicorn main:app --reload --port 8000

import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
import random

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header, status, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from groq import Groq
import fitz  # PyMuPDF

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore
from google.cloud.firestore import Increment as FSIncrement
import traceback

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ─── Firebase Admin Setup ─────────────────────────────────────────────────────
SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_CREDENTIALS", "serviceAccountKey.json")

if not firebase_admin._apps:
    if Path(SERVICE_ACCOUNT_PATH).exists():
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    else:
        print(f"WARNING: {SERVICE_ACCOUNT_PATH} not found. Admin endpoints will not work.")
        print("   Place your Firebase service account key as 'serviceAccountKey.json' in the backend folder.")

db = firestore.client() if firebase_admin._apps else None

# ─── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MediGrid API",
    description="Digital Healthcare Ecosystem Backend",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files as static
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

UPLOAD_DIR_ADS = UPLOAD_DIR / "ads"
UPLOAD_DIR_ADS.mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ─── Auth Dependency ──────────────────────────────────────────────────────────
async def verify_token(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split("Bearer ")[1]
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unauthorized: {str(e)}")

async def require_admin(user: dict = Depends(verify_token)) -> dict:
    if not db:
        raise HTTPException(status_code=503, detail="Firebase not configured")
    user_doc = db.collection("users").document(user["uid"]).get()
    if not user_doc.exists or user_doc.to_dict().get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "MediGrid API v2",
        "firebase": "connected" if firebase_admin._apps else "not_configured",
        "timestamp": datetime.utcnow().isoformat()
    }

# ─── File Upload ──────────────────────────────────────────────────────────────
@app.post("/api/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(verify_token)
):
    """Upload a medical document. Returns the URL to access it."""
    ALLOWED_TYPES = {
        "application/pdf", "image/jpeg", "image/png",
        "image/jpg", "image/webp", "application/dicom"
    }
    MAX_SIZE = 20 * 1024 * 1024  # 20MB

    # Read content for size check
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum 20MB allowed.")

    # Generate unique filename
    ext = Path(file.filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / unique_name

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "url": f"{request.base_url}uploads/{unique_name}",
        "filename": unique_name,
        "original_name": file.filename,
        "size": len(content)
    }

# ─── Ad Media Upload (No Auth — Local Dev) ───────────────────────────────────
@app.post("/api/upload/ad-media")
async def upload_ad_media(request: Request, file: UploadFile = File(...)):
    """
    Upload an advertiser banner/image to local storage.
    No authentication required for local dev.
    Returns a full localhost URL usable as imageUrl in Firestore ad documents.
    """
    ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
    MAX_SIZE = 10 * 1024 * 1024  # 10MB

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: jpg, png, webp, gif"
        )

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum 10MB allowed.")

    ext = Path(file.filename).suffix.lower() or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR_ADS / unique_name

    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "url": f"{request.base_url}uploads/ads/{unique_name}",
        "filename": unique_name,
        "original_name": file.filename,
        "size": len(content),
        "message": "Image uploaded successfully to local storage"
    }


# ─── Register Patient (Bypass client rules) ──────────────────────────────────
@app.post("/api/register/patient")
async def register_patient(request: Request):
    """Registers a new patient via Admin SDK to bypass Firestore client rules."""
    if not db:
        raise HTTPException(status_code=503, detail="Firebase not configured")
    
    data = await request.json()
    email = data.get("email")
    password = data.get("password")
    
    try:
        user = firebase_auth.create_user(email=email, password=password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    current_year = datetime.now().year
    rand4 = random.randint(1000, 9999)
    health_id = f"DHI-{current_year}-{rand4}"
    
    db.collection("users").document(user.uid).set({
        "email": email,
        "role": "patient",
        "verified": True,
        "healthId": health_id,
        "createdAt": firestore.SERVER_TIMESTAMP
    })
    
    db.collection("patients").document(health_id).set({
        "personalInfo": {
            "uid": user.uid,
            "name": data.get("name"),
            "email": email,
            "dob": data.get("dob"),
            "gender": data.get("gender"),
            "phone": data.get("phone"),
            "address": data.get("address")
        },
        "medicalInfo": {
            "bloodGroup": data.get("bloodGroup"),
            "allergies": data.get("allergies") or "None",
            "chronicConditions": data.get("chronicConditions") or "None"
        },
        "emergencyContacts": [{
            "name": data.get("emgName"),
            "relation": data.get("emgRelation"),
            "phone": data.get("emgPhone")
        }],
        "healthId": health_id,
        "createdAt": firestore.SERVER_TIMESTAMP
    })
    
    return {"message": "Patient registered successfully", "healthId": health_id, "uid": user.uid}

# ─── Admin: Verify Provider ───────────────────────────────────────────────────
@app.put("/api/admin/verify/{uid}")
async def verify_provider(
    uid: str,
    body: dict,
    admin: dict = Depends(require_admin)
):
    """Approve a hospital or laboratory registration."""
    if not db:
        raise HTTPException(status_code=503, detail="Firebase not configured")

    role = body.get("role")
    if role not in ["hospital", "lab"]:
        raise HTTPException(status_code=400, detail="Role must be 'hospital' or 'lab'")

    collection_name = "hospitals" if role == "hospital" else "laboratories"

    # Update users collection
    db.collection("users").document(uid).set({"verified": True}, merge=True)
    # Update role-specific collection
    db.collection(collection_name).document(uid).set({"verified": True}, merge=True)

    return {"message": f"Provider {uid} verified successfully", "role": role}

# ─── Admin: Reject/Delete Provider ────────────────────────────────────────────
@app.delete("/api/admin/reject/{uid}")
async def reject_provider(
    uid: str,
    body: dict,
    admin: dict = Depends(require_admin)
):
    """Reject and delete a provider account."""
    if not db:
        raise HTTPException(status_code=503, detail="Firebase not configured")

    role = body.get("role")
    collection_name = "hospitals" if role == "hospital" else "laboratories"

    try:
        firebase_auth.delete_user(uid)
    except Exception:
        pass  # User may already not exist in auth

    db.collection("users").document(uid).delete()
    db.collection(collection_name).document(uid).delete()

    return {"message": f"Provider {uid} rejected and deleted"}

# ─── Delete User Account ──────────────────────────────────────────────────────
@app.delete("/api/users/{uid}")
async def delete_user(uid: str, user: dict = Depends(verify_token)):
    """Delete a user account. User can delete their own, admin can delete any."""
    if not db:
        raise HTTPException(status_code=503, detail="Firebase not configured")

    # Check permissions
    requester_doc = db.collection("users").document(user["uid"]).get()
    is_admin = requester_doc.exists and requester_doc.to_dict().get("role") == "admin"

    target_uid = uid
    is_patient = uid.startswith("DHI-")
    
    if is_patient:
        users_ref = list(db.collection("users").where("healthId", "==", uid).limit(1).get())
        if users_ref:
            target_uid = users_ref[0].id
            
    if user["uid"] != target_uid and not is_admin:
        raise HTTPException(status_code=403, detail="Cannot delete another user's account")

    try:
        if target_uid:
            firebase_auth.delete_user(target_uid)
    except Exception:
        pass

    if target_uid:
        db.collection("users").document(target_uid).delete()
        
    if is_patient:
        db.collection("patients").document(uid).delete()
    else:
        # For doctors/hospitals/labs, their uid is their doc id in their respective collections
        db.collection("hospitals").document(target_uid).delete()
        db.collection("laboratories").document(target_uid).delete()
        db.collection("doctors").document(target_uid).delete()
        
    return {"message": "Account deleted successfully"}

# ─── Get Patient Records (for doctor/hospital after auth) ─────────────────────
@app.get("/api/patient/{health_id}/records")
async def get_patient_records(health_id: str, user: dict = Depends(verify_token)):
    """Get records for a patient. Caller must have an active accessLink."""
    if not db:
        raise HTTPException(status_code=503, detail="Firebase not configured")

    # Verify access
    access_links = db.collection("accessLinks").where("healthId", "==", health_id).get()

    valid_link = None
    for l in access_links:
        data = l.to_dict()
        if (data.get("hospitalId") == user["uid"] or data.get("doctorId") == user["uid"]) and data.get("status") in ("scoped", "active", "active_global", "global"):
            valid_link = data
            break

    if not valid_link:
        raise HTTPException(status_code=403, detail="No active access link for this patient")

    is_global = valid_link.get("status") in ("active_global", "global")

    records_ref = db.collection(f"patients/{health_id}/records").order_by("date", direction=firestore.Query.DESCENDING).get()
    
    records = []
    for r in records_ref:
        rec_data = r.to_dict()
        if is_global:
            records.append({"id": r.id, **rec_data})
        else:
            # Scoped access: return if the record belongs to the hospital or doctor in the link
            h_id = valid_link.get("hospitalId")
            if rec_data.get("hospitalId") == h_id or rec_data.get("doctorId") == user["uid"]:
                records.append({"id": r.id, **rec_data})

    return {"records": records, "count": len(records), "isGlobal": is_global}

# ─── Campaigns / Advertisements ───────────────────────────────────────────────

def serialize_campaign(doc_id: str, data: dict) -> dict:
    """Convert a Firestore ad document to a JSON-serializable dict."""
    result = {"id": doc_id}
    for key, value in data.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif value is None or isinstance(value, (str, int, float, bool)):
            result[key] = value
        elif isinstance(value, list):
            result[key] = value
        elif isinstance(value, dict):
            result[key] = value
        else:
            result[key] = str(value)
    return result


@app.post("/api/campaigns")
async def create_campaign(request: Request):
    """
    Create a new ad campaign in Firestore via Admin SDK.
    No client auth required — bypasses Firestore security rules.
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firebase not configured")

    data = await request.json()

    if not data.get("title"):
        raise HTTPException(status_code=400, detail="Campaign title is required")

    campaign = {
        "advertiserUid":   data.get("advertiserUid", "anon"),
        "companyName":     data.get("companyName", "Partner Brand"),
        "title":           data.get("title"),
        "description":     data.get("description", ""),
        "category":        data.get("category", "wellness"),
        "placement":       data.get("placement", "partner_card"),
        "targetUrl":       data.get("targetUrl", "#"),
        "imageUrl":        data.get("imageUrl", ""),
        "budget":          data.get("budget", "₹0"),
        "status":          "pending",
        "rejectionReason": None,
        "impressions":     0,
        "clicks":          0,
        "createdAt":       firestore.SERVER_TIMESTAMP,
    }

    doc_ref = db.collection("advertisements").add(campaign)
    doc_id  = doc_ref[1].id  # add() returns (update_time, doc_ref)

    return {"message": "Campaign submitted for review", "id": doc_id}


@app.get("/api/campaigns")
async def list_campaigns(status: str = None, advertiserUid: str = None):
    """List campaigns — optionally filter by status and/or advertiserUid."""
    if not db:
        raise HTTPException(status_code=503, detail="Firebase not configured")

    try:
        ref = db.collection("advertisements")

        if status and advertiserUid:
            docs = ref.where("status", "==", status)\
                      .where("advertiserUid", "==", advertiserUid).stream()
        elif status:
            docs = ref.where("status", "==", status).stream()
        elif advertiserUid:
            docs = ref.where("advertiserUid", "==", advertiserUid).stream()
        else:
            docs = ref.order_by("createdAt", direction=firestore.Query.DESCENDING).stream()

        campaigns = [serialize_campaign(d.id, d.to_dict()) for d in docs]

        # Sort client-side when ordering wasn't applied by Firestore
        if status or advertiserUid:
            campaigns.sort(key=lambda x: x.get("createdAt") or "", reverse=True)

        return {"campaigns": campaigns, "count": len(campaigns)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/campaigns/{ad_id}/approve")
async def approve_campaign(ad_id: str):
    """Approve an ad campaign (Admin SDK — bypasses Firestore rules)."""
    if not db:
        raise HTTPException(status_code=503, detail="Firebase not configured")
    try:
        db.collection("advertisements").document(ad_id).update({
            "status":          "approved",
            "rejectionReason": None,
            "approvedAt":      firestore.SERVER_TIMESTAMP,
        })
        return {"message": f"Campaign {ad_id} approved and live"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/campaigns/{ad_id}/reject")
async def reject_campaign(ad_id: str, request: Request):
    """Reject an ad campaign with a reason (Admin SDK)."""
    if not db:
        raise HTTPException(status_code=503, detail="Firebase not configured")
    try:
        data = await request.json()
        reason = data.get("reason", "Rejected by Admin")
        db.collection("advertisements").document(ad_id).update({
            "status":          "rejected",
            "rejectionReason": reason,
            "rejectedAt":      firestore.SERVER_TIMESTAMP,
        })
        return {"message": f"Campaign {ad_id} rejected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/campaigns/{ad_id}/impression")
async def track_impression(ad_id: str):
    """Atomically increment the impression counter for an ad."""
    if not db:
        return {"message": "ok"}
    try:
        db.collection("advertisements").document(ad_id).update({
            "impressions": FSIncrement(1)
        })
    except Exception:
        pass  # Silent fail — analytics should never break the UI
    return {"message": "ok"}


@app.post("/api/campaigns/{ad_id}/click")
async def track_click(ad_id: str):
    """Atomically increment the click counter for an ad."""
    if not db:
        return {"message": "ok"}
    try:
        db.collection("advertisements").document(ad_id).update({
            "clicks": FSIncrement(1)
        })
    except Exception:
        pass  # Silent fail
    return {"message": "ok"}


# ═══════════════════════════════════════════════════════════════════════════════
# RFID HARDWARE INTEGRATION ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

import secrets
import string

def generate_card_code() -> str:
    """Generate a human-friendly card code like SS-A1B2-C3D4."""
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(chars) for _ in range(4))
    part2 = ''.join(secrets.choice(chars) for _ in range(4))
    return f"SS-{part1}-{part2}"

# ─── RFID Cards ───────────────────────────────────────────────────────────────

@app.post("/api/rfid/cards")
async def issue_rfid_card(request: Request, admin: dict = Depends(require_admin)):
    """Admin: Issue a new RFID card to a patient."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    data = await request.json()
    patient_uid = data.get("patient_uid"); raw_card_uid = data.get("raw_card_uid")
    if not patient_uid or not raw_card_uid:
        raise HTTPException(status_code=400, detail="patient_uid and raw_card_uid required")
    patient_doc = db.collection("users").document(patient_uid).get()
    if not patient_doc.exists: raise HTTPException(status_code=404, detail="Patient not found")
    patient_data = patient_doc.to_dict()
    if patient_data.get("role") != "patient":
        raise HTTPException(status_code=400, detail="User is not a patient")
    
    health_id = patient_data.get("healthId", "")
    actual_patient_doc = db.collection("patients").document(health_id).get()
    patient_name = actual_patient_doc.to_dict().get("personalInfo", {}).get("name", "Unknown") if actual_patient_doc.exists else "Unknown"

    if list(db.collection("rfid_cards").where("patient_uid","==",patient_uid).where("status","in",["pending","mailed","active"]).get()):
        raise HTTPException(status_code=409, detail="Patient already has an active or pending card")
    if list(db.collection("rfid_cards").where("raw_card_uid","==",raw_card_uid).get()):
        raise HTTPException(status_code=409, detail="This RFID UID is already assigned")
    card_code = generate_card_code()
    card_doc = {
        "card_code": card_code, "raw_card_uid": raw_card_uid,
        "patient_uid": patient_uid, "health_id": health_id,
        "patient_name": patient_name, "patient_email": patient_data.get("email",""),
        "status": "pending", "issued_by_admin": admin["uid"],
        "issued_at": firestore.SERVER_TIMESTAMP, "mailed_at": None, "activated_at": None
    }
    doc_ref = db.collection("rfid_cards").add(card_doc)
    db.collection("users").document(patient_uid).set({"rfid_status":"pending"}, merge=True)
    return {"message":"Card issued successfully","card_id":doc_ref[1].id,"card_code":card_code,"patient_uid":patient_uid,"health_id":health_id}

@app.get("/api/rfid/cards/pending")
async def list_pending_cards(admin: dict = Depends(require_admin)):
    """Admin: List patients who do not yet have a card."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    assigned = {c.to_dict().get("patient_uid") for c in db.collection("rfid_cards").where("status","in",["pending","mailed","active"]).stream()}
    result = []
    for doc in db.collection("patients").stream():
        d = doc.to_dict()
        personal_info = d.get("personalInfo", {})
        uid = personal_info.get("uid")
        if uid and uid not in assigned:
            result.append({"uid":uid, "name":personal_info.get("name","Unknown"), "email":personal_info.get("email",""), "healthId":doc.id, "createdAt":d.get("createdAt").isoformat() if d.get("createdAt") else None})
    return {"patients":result,"count":len(result)}

@app.get("/api/rfid/cards/all")
async def list_all_cards(admin: dict = Depends(require_admin)):
    """Admin: List all RFID cards."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    result = []
    for c in db.collection("rfid_cards").stream():
        d = c.to_dict()
        result.append({"card_id":c.id,"card_code":d.get("card_code"),"patient_uid":d.get("patient_uid"),"health_id":d.get("health_id"),"patient_name":d.get("patient_name"),"patient_email":d.get("patient_email"),"status":d.get("status"),"issued_at":d.get("issued_at").isoformat() if d.get("issued_at") else None,"mailed_at":d.get("mailed_at").isoformat() if d.get("mailed_at") else None,"activated_at":d.get("activated_at").isoformat() if d.get("activated_at") else None})
    return {"cards":result,"count":len(result)}

@app.get("/api/rfid/cards/my")
async def get_my_card(user: dict = Depends(verify_token)):
    """Patient: Get their own card status."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    cards = list(db.collection("rfid_cards").where("patient_uid","==",user["uid"]).get())
    if not cards: return {"card":None,"status":"none"}
    card = cards[0]; d = card.to_dict()
    return {"card":{"card_id":card.id,"card_code":d.get("card_code"),"status":d.get("status"),"issued_at":d.get("issued_at").isoformat() if d.get("issued_at") else None,"mailed_at":d.get("mailed_at").isoformat() if d.get("mailed_at") else None,"activated_at":d.get("activated_at").isoformat() if d.get("activated_at") else None},"status":d.get("status","none")}

@app.post("/api/rfid/cards/activate")
async def activate_card(request: Request, user: dict = Depends(verify_token)):
    """Patient: Self-verify / activate their card using the printed code."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    data = await request.json()
    card_code = data.get("card_code","").strip().upper()
    if not card_code: raise HTTPException(status_code=400, detail="card_code is required")
    cards = list(db.collection("rfid_cards").where("patient_uid","==",user["uid"]).get())
    card = next((c for c in cards if c.to_dict().get("card_code") == card_code or c.to_dict().get("raw_card_uid") == card_code), None)
    if not card: raise HTTPException(status_code=404, detail="Card code not found or does not belong to your account")
    card_data = card.to_dict()
    if card_data.get("status") == "active": return {"message":"Card already active","card_code":card_code}
    if card_data.get("status") == "pending": raise HTTPException(status_code=400, detail="Card not mailed yet. Please wait.")
    if card_data.get("status") == "revoked": raise HTTPException(status_code=400, detail="Card revoked. Contact admin.")
    card.reference.update({"status":"active","activated_at":firestore.SERVER_TIMESTAMP})
    db.collection("users").document(user["uid"]).set({"rfid_status":"active"}, merge=True)
    return {"message":"Card activated! You can now use it at hospitals.","card_code":card_code,"health_id":card_data.get("health_id")}

@app.put("/api/rfid/cards/{card_id}/mail")
async def mark_card_mailed(card_id: str, admin: dict = Depends(require_admin)):
    """Admin: Mark a card as mailed."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    card_ref = db.collection("rfid_cards").document(card_id)
    card_doc = card_ref.get()
    if not card_doc.exists: raise HTTPException(status_code=404, detail="Card not found")
    card_ref.update({"status":"mailed","mailed_at":firestore.SERVER_TIMESTAMP})
    patient_uid = card_doc.to_dict().get("patient_uid")
    if patient_uid: db.collection("users").document(patient_uid).set({"rfid_status":"mailed"}, merge=True)
    return {"message":"Card marked as mailed"}

@app.put("/api/rfid/cards/{card_id}/revoke")
async def revoke_card(card_id: str, admin: dict = Depends(require_admin)):
    """Admin: Revoke a card."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    card_ref = db.collection("rfid_cards").document(card_id)
    card_doc = card_ref.get()
    if not card_doc.exists: raise HTTPException(status_code=404, detail="Card not found")
    patient_uid = card_doc.to_dict().get("patient_uid")
    card_ref.update({"status":"revoked"})
    if patient_uid: db.collection("users").document(patient_uid).set({"rfid_status":"revoked"}, merge=True)
    return {"message":f"Card {card_id} revoked"}

# ─── Hospital Hubs ────────────────────────────────────────────────────────────

@app.post("/api/hubs")
async def register_hub(request: Request, admin: dict = Depends(require_admin)):
    """Admin: Register a new hub and assign it to a hospital."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    data = await request.json()
    hub_id = data.get("hub_id","").strip().upper(); hospital_uid = data.get("hospital_uid")
    if not hub_id or not hospital_uid:
        raise HTTPException(status_code=400, detail="hub_id and hospital_uid required")
    if db.collection("hospital_hubs").document(hub_id).get().exists:
        raise HTTPException(status_code=409, detail=f"Hub '{hub_id}' already registered")
    hosp_doc = db.collection("hospitals").document(hospital_uid).get()
    hospital_name = hosp_doc.to_dict().get("name","") if hosp_doc.exists else ""
    db.collection("hospital_hubs").document(hub_id).set({
        "hub_id":hub_id,"hospital_uid":hospital_uid,"hospital_name":hospital_name,
        "status":"assigned","assigned_by_admin":admin["uid"],
        "assigned_at":firestore.SERVER_TIMESTAMP,"activated_at":None,
        "last_seen":None,"ip_address":None,"firmware_version":None
    })
    return {"message":f"Hub '{hub_id}' registered and assigned to {hospital_name}","hub_id":hub_id}

@app.get("/api/hubs")
async def list_hubs(admin: dict = Depends(require_admin)):
    """Admin: List all registered hubs."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    result = []
    for h in db.collection("hospital_hubs").stream():
        d = h.to_dict()
        result.append({"hub_id":h.id,"hospital_uid":d.get("hospital_uid"),"hospital_name":d.get("hospital_name"),"status":d.get("status"),"assigned_at":d.get("assigned_at").isoformat() if d.get("assigned_at") else None,"activated_at":d.get("activated_at").isoformat() if d.get("activated_at") else None,"last_seen":d.get("last_seen").isoformat() if d.get("last_seen") else None,"ip_address":d.get("ip_address"),"firmware_version":d.get("firmware_version")})
    return {"hubs":result,"count":len(result)}

@app.get("/api/hubs/my")
async def get_my_hubs(user: dict = Depends(verify_token)):
    """Hospital: Get their own hubs."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    result = []
    for h in db.collection("hospital_hubs").where("hospital_uid","==",user["uid"]).stream():
        d = h.to_dict()
        result.append({"hub_id":h.id,"status":d.get("status"),"activated_at":d.get("activated_at").isoformat() if d.get("activated_at") else None,"last_seen":d.get("last_seen").isoformat() if d.get("last_seen") else None,"firmware_version":d.get("firmware_version")})
    return {"hubs":result,"count":len(result)}

@app.put("/api/hubs/{hub_id}/activate")
async def activate_hub(hub_id: str, user: dict = Depends(verify_token)):
    """Hospital: Activate their hub by entering its ID."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    hub_ref = db.collection("hospital_hubs").document(hub_id.upper())
    hub_doc = hub_ref.get()
    if not hub_doc.exists: raise HTTPException(status_code=404, detail="Hub ID not found. Contact admin.")
    hub_data = hub_doc.to_dict()
    if hub_data.get("hospital_uid") != user["uid"]:
        raise HTTPException(status_code=403, detail="Hub not assigned to your hospital")
    if hub_data.get("status") == "active": return {"message":"Hub already active","hub_id":hub_id}
    hub_ref.update({"status":"active","activated_at":firestore.SERVER_TIMESTAMP})
    return {"message":f"Hub '{hub_id}' activated. Scanner is now live.","hub_id":hub_id}

@app.post("/api/hubs/{hub_id}/heartbeat")
async def hub_heartbeat(hub_id: str, request: Request):
    """ESP32: Send keepalive heartbeat."""
    if not db: return {"status":"ok"}
    try: data = await request.json()
    except Exception: data = {}
    hub_ref = db.collection("hospital_hubs").document(hub_id.upper())
    if not hub_ref.get().exists: raise HTTPException(status_code=404, detail="Hub not found")
    hub_ref.update({"last_seen":firestore.SERVER_TIMESTAMP,"ip_address":data.get("ip_address"),"firmware_version":data.get("firmware_version"),"status":"active"})
    return {"status":"ok","hub_id":hub_id}

@app.get("/api/hubs/{hub_id}/status")
async def get_hub_status(hub_id: str):
    """Check hub status (no auth required — used by ESP32 on boot)."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    hub_doc = db.collection("hospital_hubs").document(hub_id.upper()).get()
    if not hub_doc.exists: raise HTTPException(status_code=404, detail="Hub not registered")
    d = hub_doc.to_dict()
    return {"hub_id":hub_id,"status":d.get("status"),"hospital_name":d.get("hospital_name"),"hospital_uid":d.get("hospital_uid")}

# ─── RFID Scan — Core ESP32 Endpoint ─────────────────────────────────────────

@app.post("/api/rfid/scan")
async def rfid_scan(request: Request):
    """ESP32: Receive a scan event and create/update a patient visit."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    data = await request.json()
    hub_id = data.get("hub_id","").strip().upper()
    raw_card_uid = data.get("raw_card_uid","").strip()
    if not hub_id or not raw_card_uid:
        raise HTTPException(status_code=400, detail="hub_id and raw_card_uid required")
    hub_doc = db.collection("hospital_hubs").document(hub_id).get()
    if not hub_doc.exists: raise HTTPException(status_code=404, detail=f"Hub '{hub_id}' not registered")
    hub_data = hub_doc.to_dict()
    if hub_data.get("status") != "active": raise HTTPException(status_code=403, detail="Hub not active. Contact admin.")
    hospital_uid = hub_data["hospital_uid"]; hospital_name = hub_data.get("hospital_name","")
    db.collection("hospital_hubs").document(hub_id).update({"last_seen":firestore.SERVER_TIMESTAMP})
    cards = list(db.collection("rfid_cards").where("raw_card_uid","==",raw_card_uid).get())
    if not cards: raise HTTPException(status_code=403, detail="Card not recognized")
    
    card = cards[0]; card_data = card.to_dict()
    status = card_data.get("status")
    
    if status == "revoked":
        raise HTTPException(status_code=403, detail="Card revoked. Contact admin.")
        
    if status in ["pending", "mailed"]:
        # Auto-activate on first hospital scan
        card.reference.update({"status":"active","activated_at":firestore.SERVER_TIMESTAMP})
        db.collection("users").document(card_data["patient_uid"]).set({"rfid_status":"active"}, merge=True)
        card_data["status"] = "active"
        
    patient_uid = card_data["patient_uid"]; health_id = card_data.get("health_id",""); patient_name = card_data.get("patient_name","")
    now = datetime.utcnow(); scan_stamp = {"at":now.isoformat(),"hub_id":hub_id}
    
    # Re-activate access link if it already exists (e.g. they were dismissed but scanned again)
    link_id = f"{hospital_uid}_{health_id}"
    link_doc = db.collection("accessLinks").document(link_id).get()
    if link_doc.exists:
        db.collection("accessLinks").document(link_id).update({
            "status": "scoped",
            "lastUpdated": firestore.SERVER_TIMESTAMP
        })
    # If it doesn't exist, we do NOT create it here. 
    # The frontend Doctor Assignment Modal will create it once a doctor is chosen.
    
    open_list = list(db.collection("visits").where("patient_uid","==",patient_uid).where("hospital_uid","==",hospital_uid).where("status","==","open").get())
    if open_list:
        v = open_list[0]
        v.reference.update({"last_scan_at":firestore.SERVER_TIMESTAMP,"scans":firestore.ArrayUnion([scan_stamp])})
        return {"event":"re_entry","visit_id":v.id,"patient_uid":patient_uid,"health_id":health_id,"patient_name":patient_name,"hospital_name":hospital_name,"message":f"Welcome back, {patient_name}. Visit updated.","is_new_visit":False}
    else:
        doc_ref = db.collection("visits").add({"patient_uid":patient_uid,"health_id":health_id,"patient_name":patient_name,"hospital_uid":hospital_uid,"hospital_name":hospital_name,"hub_id":hub_id,"card_id":card.id,"raw_card_uid":raw_card_uid,"status":"open","check_in_at":firestore.SERVER_TIMESTAMP,"last_scan_at":firestore.SERVER_TIMESTAMP,"scans":[scan_stamp],"bill_id":None,"notes":""})
        return {"event":"new_visit","visit_id":doc_ref[1].id,"patient_uid":patient_uid,"health_id":health_id,"patient_name":patient_name,"hospital_name":hospital_name,"message":f"New visit created for {patient_name}.","is_new_visit":True}

# ─── Visits ───────────────────────────────────────────────────────────────────

@app.get("/api/visits")
async def list_visits(user: dict = Depends(verify_token), status: str = None):
    """Hospital/Admin: List visits. Hospitals only see their own."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    user_doc = db.collection("users").document(user["uid"]).get()
    role = user_doc.to_dict().get("role") if user_doc.exists else ""
    if role not in ("hospital","admin"): raise HTTPException(status_code=403, detail="Hospital or admin access required")
    ref = db.collection("visits")
    if role == "hospital": ref = ref.where("hospital_uid","==",user["uid"])
    if status: ref = ref.where("status","==",status)
    result = []
    for v in ref.order_by("check_in_at",direction=firestore.Query.DESCENDING).stream():
        d = v.to_dict()
        result.append({"visit_id":v.id,"patient_uid":d.get("patient_uid"),"health_id":d.get("health_id"),"patient_name":d.get("patient_name"),"hospital_name":d.get("hospital_name"),"hub_id":d.get("hub_id"),"status":d.get("status"),"check_in_at":d.get("check_in_at").isoformat() if d.get("check_in_at") else None,"last_scan_at":d.get("last_scan_at").isoformat() if d.get("last_scan_at") else None,"bill_id":d.get("bill_id"),"notes":d.get("notes",""),"scans":d.get("scans",[])})
    return {"visits":result,"count":len(result)}

@app.get("/api/visits/patient/my")
async def get_my_visits(user: dict = Depends(verify_token)):
    """Patient: Get their own visit history."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    result = []
    for v in db.collection("visits").where("patient_uid","==",user["uid"]).order_by("check_in_at",direction=firestore.Query.DESCENDING).stream():
        d = v.to_dict()
        result.append({"visit_id":v.id,"hospital_name":d.get("hospital_name"),"status":d.get("status"),"check_in_at":d.get("check_in_at").isoformat() if d.get("check_in_at") else None,"last_scan_at":d.get("last_scan_at").isoformat() if d.get("last_scan_at") else None,"scan_count":len(d.get("scans",[]))})
    return {"visits":result,"count":len(result)}

@app.get("/api/visits/{visit_id}")
async def get_visit(visit_id: str, user: dict = Depends(verify_token)):
    """Get a single visit. Accessible by the hospital, patient, or admin."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    visit_doc = db.collection("visits").document(visit_id).get()
    if not visit_doc.exists: raise HTTPException(status_code=404, detail="Visit not found")
    d = visit_doc.to_dict()
    user_doc = db.collection("users").document(user["uid"]).get()
    role = user_doc.to_dict().get("role") if user_doc.exists else ""
    if role not in ("admin",) and d.get("hospital_uid") != user["uid"] and d.get("patient_uid") != user["uid"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return {"visit_id":visit_doc.id,**{k:(v.isoformat() if hasattr(v,"isoformat") else v) for k,v in d.items()}}

@app.put("/api/visits/{visit_id}/bill")
async def link_bill_to_visit(visit_id: str, request: Request, user: dict = Depends(verify_token)):
    """Hospital: Link a bill to a visit."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    data = await request.json(); bill_id = data.get("bill_id")
    if not bill_id: raise HTTPException(status_code=400, detail="bill_id required")
    visit_ref = db.collection("visits").document(visit_id)
    visit_doc = visit_ref.get()
    if not visit_doc.exists: raise HTTPException(status_code=404, detail="Visit not found")
    if visit_doc.to_dict().get("hospital_uid") != user["uid"]: raise HTTPException(status_code=403, detail="Access denied")
    visit_ref.update({"bill_id":bill_id,"status":"billed"})
    return {"message":"Bill linked","visit_id":visit_id,"bill_id":bill_id}

@app.put("/api/visits/{visit_id}/discharge")
async def discharge_patient(visit_id: str, request: Request, user: dict = Depends(verify_token)):
    """Hospital: Mark a patient as discharged."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    data = await request.json()
    visit_ref = db.collection("visits").document(visit_id)
    visit_doc = visit_ref.get()
    if not visit_doc.exists: raise HTTPException(status_code=404, detail="Visit not found")
    if visit_doc.to_dict().get("hospital_uid") != user["uid"]: raise HTTPException(status_code=403, detail="Access denied")
    visit_ref.update({"status":"discharged","discharged_at":firestore.SERVER_TIMESTAMP,"notes":data.get("notes","")})
    return {"message":"Patient discharged","visit_id":visit_id}

@app.put("/api/visits/{visit_id}/notes")
async def update_visit_notes(visit_id: str, request: Request, user: dict = Depends(verify_token)):
    """Hospital: Update notes on a visit."""
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    data = await request.json()
    visit_ref = db.collection("visits").document(visit_id)
    visit_doc = visit_ref.get()
    if not visit_doc.exists: raise HTTPException(status_code=404, detail="Visit not found")
    if visit_doc.to_dict().get("hospital_uid") != user["uid"]: raise HTTPException(status_code=403, detail="Access denied")
    visit_ref.update({"notes":data.get("notes","")})
    return {"message":"Notes updated","visit_id":visit_id}

# ─── AI Summarizer ────────────────────────────────────────────────────────────
@app.post("/api/ai/summarize")
async def summarize_record(request: Request, user: dict = Depends(verify_token)):
    """Patient: Ask AI about a specific medical record."""
    if not groq_client:
        raise HTTPException(status_code=500, detail="AI Assistant is not configured on the server. Please set GROQ_API_KEY.")
        
    data = await request.json()
    record_id = data.get("record_id")
    query = data.get("query", "Summarize this medical record.")
    
    if not record_id:
        raise HTTPException(status_code=400, detail="record_id is required")
        
    try:
        # 1. Look up the patient's actual document ID (healthId) using their auth uid
        patients = db.collection("patients").where("personalInfo.uid", "==", user["uid"]).limit(1).get()
        if not patients:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        
        health_id = patients[0].id

        # 2. Fetch record from patient's records subcollection
        record_ref = db.collection(f"patients/{health_id}/records").document(record_id)
        record_doc = record_ref.get()
        if not record_doc.exists:
            raise HTTPException(status_code=404, detail="Record not found")
            
        rec_data = record_doc.to_dict()
        record_text = f"Type: {rec_data.get('type')}\nDate: {rec_data.get('date')}\nNotes: {rec_data.get('notes')}\nHospital: {rec_data.get('hospitalName')}\nDoctor: {rec_data.get('doctorName')}"
        
        # 3. Check if there's a file attached
        file_url = rec_data.get("fileUrl") or rec_data.get("fileURL")
        extracted_text = ""
        
        if file_url:
            filename = file_url.split("/")[-1]
            local_file_path = UPLOAD_DIR / filename
            if local_file_path.exists():
                if local_file_path.suffix.lower() == ".pdf":
                    try:
                        doc = fitz.open(local_file_path)
                        for page in doc:
                            extracted_text += page.get_text() + "\n"
                        doc.close()
                    except Exception as e:
                        print(f"Failed to read PDF: {e}")
                else:
                    extracted_text = "[An image was attached to this record, but the current text-only AI model cannot view it.]"

        system_prompt = "You are a helpful AI Medical Assistant for a patient. The patient is asking you a question about one of their medical records. Keep your answer clear, easy to understand for a non-doctor, and structured."
        user_prompt = f"Here is the medical record data:\n{record_text}\n\n"
        
        if extracted_text:
            user_prompt += f"Here is the extracted text from the attached file:\n{extracted_text}\n\n"
            
        user_prompt += f"Patient's Question: {query}"

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )
        
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")

# ─── Drone Delivery System ───────────────────────────────────────────────────
import math
import json
import googlemaps

# Initialize Google Maps Client
GMAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=GMAPS_API_KEY) if GMAPS_API_KEY else None

class DroneConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_launch_command(self, order_data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(order_data))
            except Exception as e:
                print(f"Error sending to drone: {e}")

drone_manager = DroneConnectionManager()

@app.websocket("/ws/drone")
async def drone_endpoint(websocket: WebSocket):
    """ESP32 Drone WebSocket connection."""
    await drone_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Drone Update: {data}")
            # Optionally forward GPS updates to the patient/pharmacy UI here
    except WebSocketDisconnect:
        drone_manager.disconnect(websocket)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.post("/api/emergency/request")
async def emergency_request(request: Request, user: dict = Depends(verify_token)):
    """Patient: Request emergency medicine."""
    data = await request.json()
    details = data.get("details")
    lat = data.get("lat")
    lng = data.get("lng")
    
    if not details or lat is None or lng is None:
        raise HTTPException(status_code=400, detail="Missing details, lat, or lng")
        
    try:
        # Mocking 3 nearby pharmacies
        pharmacies = [
            {"id": "shop1", "name": "Apollo Pharmacy", "lat": lat + 0.01, "lng": lng + 0.01},
            {"id": "shop2", "name": "Wellness Forever", "lat": lat + 0.05, "lng": lng - 0.02},
            {"id": "shop3", "name": "MedPlus", "lat": lat - 0.02, "lng": lng - 0.01}
        ]
        
        # Calculate distances using Google Maps API if available, else Haversine
        nearest = None
        min_dist = float('inf')
        
        if gmaps:
            origins = [(lat, lng)]
            destinations = [(shop["lat"], shop["lng"]) for shop in pharmacies]
            try:
                matrix = gmaps.distance_matrix(origins, destinations, mode="driving")
                if matrix['status'] == 'OK':
                    elements = matrix['rows'][0]['elements']
                    for idx, element in enumerate(elements):
                        if element['status'] == 'OK':
                            duration_sec = element['duration']['value']
                            if duration_sec < min_dist:
                                min_dist = duration_sec
                                nearest = pharmacies[idx]
            except Exception as e:
                print(f"Google Maps API error: {e}")
                
        # Fallback to Haversine if GMaps failed or is not configured
        if nearest is None:
            print("Falling back to Haversine distance.")
            for shop in pharmacies:
                dist = haversine(lat, lng, shop["lat"], shop["lng"])
                if dist < min_dist:
                    min_dist = dist
                    nearest = shop
                
        # Create Emergency Order in Firestore
        order_data = {
            "patient_uid": user["uid"],
            "details": details,
            "patient_location": {"lat": lat, "lng": lng},
            "pharmacy_id": nearest["id"],
            "status": "pending",
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        order_ref = db.collection("emergency_orders").document()
        order_ref.set(order_data)
        
        return {"message": "Request sent", "pharmacy": nearest, "order_id": order_ref.id}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pharmacy/dispatch/{order_id}")
async def dispatch_drone(order_id: str):
    """Pharmacy: Accept order and dispatch drone."""
    order_ref = db.collection("emergency_orders").document(order_id)
    doc = order_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order_data = doc.to_dict()
    
    # Send Launch Command to ESP32 Drone via WebSocket
    command = {
        "action": "LAUNCH",
        "order_id": order_id,
        "destination": order_data["patient_location"]
    }
    await drone_manager.send_launch_command(command)
    
    # Update Status
    order_ref.update({"status": "dispatched"})
    
    return {"message": "Drone Dispatched"}

@app.post("/api/test-drone")
async def test_drone(user: dict = Depends(verify_token)):
    """Patient/Pharmacy: Directly test drone spin."""
    command = {
        "action": "TEST_SPIN"
    }
    await drone_manager.send_launch_command(command)
    return {"message": "Test command sent to drone"}

# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
