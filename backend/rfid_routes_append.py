
# ═══════════════════════════════════════════════════════════════════════════════
# RFID HARDWARE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

import secrets
import string

def generate_card_code() -> str:
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(chars) for _ in range(4))
    part2 = ''.join(secrets.choice(chars) for _ in range(4))
    return f"SS-{part1}-{part2}"

# ─── RFID Cards ───────────────────────────────────────────────────────────────

@app.post("/api/rfid/cards")
async def issue_rfid_card(request: Request, admin: dict = Depends(require_admin)):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    data = await request.json()
    patient_uid = data.get("patient_uid"); raw_card_uid = data.get("raw_card_uid")
    if not patient_uid or not raw_card_uid: raise HTTPException(status_code=400, detail="patient_uid and raw_card_uid required")
    patient_doc = db.collection("users").document(patient_uid).get()
    if not patient_doc.exists: raise HTTPException(status_code=404, detail="Patient not found")
    patient_data = patient_doc.to_dict()
    if patient_data.get("role") != "patient": raise HTTPException(status_code=400, detail="User is not a patient")
    if list(db.collection("rfid_cards").where("patient_uid","==",patient_uid).where("status","in",["pending","mailed","active"]).get()):
        raise HTTPException(status_code=409, detail="Patient already has an active or pending card")
    if list(db.collection("rfid_cards").where("raw_card_uid","==",raw_card_uid).get()):
        raise HTTPException(status_code=409, detail="This RFID UID is already assigned")
    card_code = generate_card_code()
    health_id = patient_data.get("healthId","")
    card_doc = {"card_code":card_code,"raw_card_uid":raw_card_uid,"patient_uid":patient_uid,"health_id":health_id,"patient_name":patient_data.get("name",""),"patient_email":patient_data.get("email",""),"status":"pending","issued_by_admin":admin["uid"],"issued_at":firestore.SERVER_TIMESTAMP,"mailed_at":None,"activated_at":None}
    doc_ref = db.collection("rfid_cards").add(card_doc)
    db.collection("users").document(patient_uid).set({"rfid_status":"pending"},merge=True)
    return {"message":"Card issued successfully","card_id":doc_ref[1].id,"card_code":card_code,"patient_uid":patient_uid,"health_id":health_id}

@app.get("/api/rfid/cards/pending")
async def list_pending_cards(admin: dict = Depends(require_admin)):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    assigned = {c.to_dict().get("patient_uid") for c in db.collection("rfid_cards").where("status","in",["pending","mailed","active"]).stream()}
    result = []
    for p in db.collection("users").where("role","==","patient").stream():
        if p.id not in assigned:
            d = p.to_dict()
            result.append({"uid":p.id,"name":d.get("name",""),"email":d.get("email",""),"healthId":d.get("healthId",""),"createdAt":d.get("createdAt").isoformat() if d.get("createdAt") else None})
    return {"patients":result,"count":len(result)}

@app.get("/api/rfid/cards/all")
async def list_all_cards(admin: dict = Depends(require_admin)):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    result = []
    for c in db.collection("rfid_cards").stream():
        d = c.to_dict()
        result.append({"card_id":c.id,"card_code":d.get("card_code"),"patient_uid":d.get("patient_uid"),"health_id":d.get("health_id"),"patient_name":d.get("patient_name"),"patient_email":d.get("patient_email"),"status":d.get("status"),"issued_at":d.get("issued_at").isoformat() if d.get("issued_at") else None,"mailed_at":d.get("mailed_at").isoformat() if d.get("mailed_at") else None,"activated_at":d.get("activated_at").isoformat() if d.get("activated_at") else None})
    return {"cards":result,"count":len(result)}

@app.get("/api/rfid/cards/my")
async def get_my_card(user: dict = Depends(verify_token)):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    cards = list(db.collection("rfid_cards").where("patient_uid","==",user["uid"]).get())
    if not cards: return {"card":None,"status":"none"}
    card = cards[0]; d = card.to_dict()
    return {"card":{"card_id":card.id,"card_code":d.get("card_code"),"status":d.get("status"),"issued_at":d.get("issued_at").isoformat() if d.get("issued_at") else None,"mailed_at":d.get("mailed_at").isoformat() if d.get("mailed_at") else None,"activated_at":d.get("activated_at").isoformat() if d.get("activated_at") else None},"status":d.get("status","none")}

@app.post("/api/rfid/cards/activate")
async def activate_card(request: Request, user: dict = Depends(verify_token)):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    data = await request.json()
    card_code = data.get("card_code","").strip().upper()
    if not card_code: raise HTTPException(status_code=400, detail="card_code is required")
    cards = list(db.collection("rfid_cards").where("card_code","==",card_code).where("patient_uid","==",user["uid"]).get())
    if not cards: raise HTTPException(status_code=404, detail="Card code not found or does not belong to your account")
    card = cards[0]; card_data = card.to_dict()
    if card_data.get("status") == "active": return {"message":"Card already active","card_code":card_code}
    if card_data.get("status") == "pending": raise HTTPException(status_code=400, detail="Card not mailed yet. Please wait.")
    if card_data.get("status") == "revoked": raise HTTPException(status_code=400, detail="Card revoked. Contact admin.")
    card.reference.update({"status":"active","activated_at":firestore.SERVER_TIMESTAMP})
    db.collection("users").document(user["uid"]).set({"rfid_status":"active"},merge=True)
    return {"message":"Card activated! You can now use it at hospitals.","card_code":card_code,"health_id":card_data.get("health_id")}

@app.put("/api/rfid/cards/{card_id}/mail")
async def mark_card_mailed(card_id: str, admin: dict = Depends(require_admin)):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    card_ref = db.collection("rfid_cards").document(card_id)
    card_doc = card_ref.get()
    if not card_doc.exists: raise HTTPException(status_code=404, detail="Card not found")
    card_ref.update({"status":"mailed","mailed_at":firestore.SERVER_TIMESTAMP})
    patient_uid = card_doc.to_dict().get("patient_uid")
    if patient_uid: db.collection("users").document(patient_uid).set({"rfid_status":"mailed"},merge=True)
    return {"message":"Card marked as mailed"}

@app.put("/api/rfid/cards/{card_id}/revoke")
async def revoke_card(card_id: str, admin: dict = Depends(require_admin)):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    card_ref = db.collection("rfid_cards").document(card_id)
    card_doc = card_ref.get()
    if not card_doc.exists: raise HTTPException(status_code=404, detail="Card not found")
    patient_uid = card_doc.to_dict().get("patient_uid")
    card_ref.update({"status":"revoked"})
    if patient_uid: db.collection("users").document(patient_uid).set({"rfid_status":"revoked"},merge=True)
    return {"message":f"Card {card_id} revoked"}

# ─── Hospital Hubs ────────────────────────────────────────────────────────────

@app.post("/api/hubs")
async def register_hub(request: Request, admin: dict = Depends(require_admin)):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    data = await request.json()
    hub_id = data.get("hub_id","").strip().upper(); hospital_uid = data.get("hospital_uid")
    if not hub_id or not hospital_uid: raise HTTPException(status_code=400, detail="hub_id and hospital_uid required")
    if db.collection("hospital_hubs").document(hub_id).get().exists: raise HTTPException(status_code=409, detail=f"Hub '{hub_id}' already registered")
    hosp_doc = db.collection("hospitals").document(hospital_uid).get()
    hospital_name = hosp_doc.to_dict().get("name","") if hosp_doc.exists else ""
    db.collection("hospital_hubs").document(hub_id).set({"hub_id":hub_id,"hospital_uid":hospital_uid,"hospital_name":hospital_name,"status":"assigned","assigned_by_admin":admin["uid"],"assigned_at":firestore.SERVER_TIMESTAMP,"activated_at":None,"last_seen":None,"ip_address":None,"firmware_version":None})
    return {"message":f"Hub '{hub_id}' registered and assigned to {hospital_name}","hub_id":hub_id}

@app.get("/api/hubs")
async def list_hubs(admin: dict = Depends(require_admin)):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    result = []
    for h in db.collection("hospital_hubs").stream():
        d = h.to_dict()
        result.append({"hub_id":h.id,"hospital_uid":d.get("hospital_uid"),"hospital_name":d.get("hospital_name"),"status":d.get("status"),"assigned_at":d.get("assigned_at").isoformat() if d.get("assigned_at") else None,"activated_at":d.get("activated_at").isoformat() if d.get("activated_at") else None,"last_seen":d.get("last_seen").isoformat() if d.get("last_seen") else None,"ip_address":d.get("ip_address"),"firmware_version":d.get("firmware_version")})
    return {"hubs":result,"count":len(result)}

@app.get("/api/hubs/my")
async def get_my_hubs(user: dict = Depends(verify_token)):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    result = []
    for h in db.collection("hospital_hubs").where("hospital_uid","==",user["uid"]).stream():
        d = h.to_dict()
        result.append({"hub_id":h.id,"status":d.get("status"),"activated_at":d.get("activated_at").isoformat() if d.get("activated_at") else None,"last_seen":d.get("last_seen").isoformat() if d.get("last_seen") else None,"firmware_version":d.get("firmware_version")})
    return {"hubs":result,"count":len(result)}

@app.put("/api/hubs/{hub_id}/activate")
async def activate_hub(hub_id: str, user: dict = Depends(verify_token)):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    hub_ref = db.collection("hospital_hubs").document(hub_id.upper())
    hub_doc = hub_ref.get()
    if not hub_doc.exists: raise HTTPException(status_code=404, detail="Hub ID not found. Contact admin.")
    hub_data = hub_doc.to_dict()
    if hub_data.get("hospital_uid") != user["uid"]: raise HTTPException(status_code=403, detail="Hub not assigned to your hospital")
    if hub_data.get("status") == "active": return {"message":"Hub already active","hub_id":hub_id}
    hub_ref.update({"status":"active","activated_at":firestore.SERVER_TIMESTAMP})
    return {"message":f"Hub '{hub_id}' activated. Scanner is now live.","hub_id":hub_id}

@app.post("/api/hubs/{hub_id}/heartbeat")
async def hub_heartbeat(hub_id: str, request: Request):
    if not db: return {"status":"ok"}
    try: data = await request.json()
    except Exception: data = {}
    hub_ref = db.collection("hospital_hubs").document(hub_id.upper())
    if not hub_ref.get().exists: raise HTTPException(status_code=404, detail="Hub not found")
    hub_ref.update({"last_seen":firestore.SERVER_TIMESTAMP,"ip_address":data.get("ip_address"),"firmware_version":data.get("firmware_version"),"status":"active"})
    return {"status":"ok","hub_id":hub_id}

@app.get("/api/hubs/{hub_id}/status")
async def get_hub_status(hub_id: str):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    hub_doc = db.collection("hospital_hubs").document(hub_id.upper()).get()
    if not hub_doc.exists: raise HTTPException(status_code=404, detail="Hub not registered")
    d = hub_doc.to_dict()
    return {"hub_id":hub_id,"status":d.get("status"),"hospital_name":d.get("hospital_name"),"hospital_uid":d.get("hospital_uid")}

# ─── RFID Scan — Core ESP32 Endpoint ─────────────────────────────────────────

@app.post("/api/rfid/scan")
async def rfid_scan(request: Request):
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    data = await request.json()
    hub_id = data.get("hub_id","").strip().upper(); raw_card_uid = data.get("raw_card_uid","").strip()
    if not hub_id or not raw_card_uid: raise HTTPException(status_code=400, detail="hub_id and raw_card_uid required")
    hub_doc = db.collection("hospital_hubs").document(hub_id).get()
    if not hub_doc.exists: raise HTTPException(status_code=404, detail=f"Hub '{hub_id}' not registered")
    hub_data = hub_doc.to_dict()
    if hub_data.get("status") != "active": raise HTTPException(status_code=403, detail="Hub not active. Contact admin.")
    hospital_uid = hub_data["hospital_uid"]; hospital_name = hub_data.get("hospital_name","")
    db.collection("hospital_hubs").document(hub_id).update({"last_seen":firestore.SERVER_TIMESTAMP})
    cards = list(db.collection("rfid_cards").where("raw_card_uid","==",raw_card_uid).where("status","==","active").get())
    if not cards: raise HTTPException(status_code=403, detail="Card not recognized or not yet activated")
    card = cards[0]; card_data = card.to_dict()
    patient_uid = card_data["patient_uid"]; health_id = card_data.get("health_id",""); patient_name = card_data.get("patient_name","")
    now = datetime.utcnow(); scan_stamp = {"at":now.isoformat(),"hub_id":hub_id}
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
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    result = []
    for v in db.collection("visits").where("patient_uid","==",user["uid"]).order_by("check_in_at",direction=firestore.Query.DESCENDING).stream():
        d = v.to_dict()
        result.append({"visit_id":v.id,"hospital_name":d.get("hospital_name"),"status":d.get("status"),"check_in_at":d.get("check_in_at").isoformat() if d.get("check_in_at") else None,"last_scan_at":d.get("last_scan_at").isoformat() if d.get("last_scan_at") else None,"scan_count":len(d.get("scans",[]))})
    return {"visits":result,"count":len(result)}

@app.get("/api/visits/{visit_id}")
async def get_visit(visit_id: str, user: dict = Depends(verify_token)):
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
    if not db: raise HTTPException(status_code=503, detail="Firebase not configured")
    data = await request.json()
    visit_ref = db.collection("visits").document(visit_id)
    visit_doc = visit_ref.get()
    if not visit_doc.exists: raise HTTPException(status_code=404, detail="Visit not found")
    if visit_doc.to_dict().get("hospital_uid") != user["uid"]: raise HTTPException(status_code=403, detail="Access denied")
    visit_ref.update({"notes":data.get("notes","")})
    return {"message":"Notes updated","visit_id":visit_id}
