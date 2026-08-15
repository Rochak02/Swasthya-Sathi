# 🏗️ Technical Architecture & Technology Stack
### **Swasthya Sathi — Universal Digital Healthcare Ecosystem**

---

## 📌 Executive Overview

**Swasthya Sathi** (also referenced as *MediGrid*) is a multi-tenant, role-based digital healthcare companion platform designed for the Indian healthcare ecosystem. The platform seamlessly connects seven key user personas—**Patients, Doctors, Hospitals, Diagnostic Labs, Healthcare Advertisers, Emergency Responders, and Super Admins**—under a unified digital umbrella.

The system is architected around a **Zero-Build Frontend** combined with a **Serverless-First Database (Cloud Firestore)** and a **High-Performance Asynchronous Python Backend (FastAPI)**. This design provides maximum operational simplicity, low latency, real-time synchronization, and strict data isolation for Electronic Health Records (EHR).

---

## 🛠️ Technology Stack

```
                               ┌──────────────────────────────────────────────┐
                               │             SWASTHYA SATHI STACK             │
                               └──────────────────────┬───────────────────────┘
                                                      │
         ┌─────────────────────────┬──────────────────┴──────────────────────┬─────────────────────────┐
         ▼                         ▼                                         ▼                         ▼
 ┌───────────────┐        ┌──────────────────┐                      ┌──────────────────┐      ┌──────────────────┐
 │   FRONTEND    │        │  AUTHENTICATION  │                      │     DATABASE     │      │   BACKEND API    │
 ├───────────────┤        ├──────────────────┤                      ├──────────────────┤      ├──────────────────┤
 │ • HTML5       │        │ • Firebase Auth  │                      │ • Cloud Firestore│      │ • FastAPI        │
 │ • ES6+ Modules│        │ • Bearer Tokens  │                      │ • Real-time DB   │      │ • Uvicorn        │
 │ • Tailwind CSS│        │ • Role RBAC      │                      │ • Security Rules │      │ • Firebase Admin │
 │ • FontAwesome │        └──────────────────┘                      └──────────────────┘      │ • Python Aiofiles│
 └───────────────┘                                                                            └──────────────────┘
```

### 1. Frontend Architecture
* **Core Markup & Styling:**
  * **HTML5**: Semantic, accessible markup designed for responsive cross-device viewing (desktop, tablet, mobile).
  * **Tailwind CSS (CDN)**: Utility-first CSS engine for rapid, consistent UI rendering.
  * **Custom Design System (`custom.css`)**: Tailored CSS tokens, HSL color schemes, dark mode variables, micro-animations, and glassmorphism UI components.
  * **Font & Icon Libraries**: *Outfit* & *Plus Jakarta Sans* typography via Google Fonts; icons via *Font Awesome 6 Free*.
* **Logic & Execution:**
  * **ES6+ Vanilla JavaScript**: Zero-build frontend paradigm. Utilizes browser-native ES module imports (`import`/`export`) directly from CDN distribution endpoints (e.g., `gstatic.com`).
  * **Role Guards (`auth-guard.js`)**: Client-side route protection that intercepts unauthorized access and verifies identity roles before UI rendering.
  * **Internationalization (`i18n.js`)**: Native multi-language translation engine providing real-time UI localization across regional languages (English, Hindi, Bengali, etc.).

---

### 2. Backend API Layer
* **Framework**: **FastAPI 0.111.0** running on **Python 3.10+**.
* **ASGI Server**: **Uvicorn 0.30.1** high-performance asynchronous execution engine.
* **Authentication Integration**: **Firebase Admin SDK 6.5.0** for server-side token validation and secure privilege checks.
* **Asynchronous Utilities**: `aiofiles` and `python-multipart` for efficient handling of multi-part file uploads (medical documents, DICOM files, scan images, ad assets).
* **Configuration**: `python-dotenv` for secure environment variable isolation (`FIREBASE_CREDENTIALS`, API keys).

---

### 3. Database & Security Layer
* **Primary Database**: **Cloud Firestore (NoSQL Document Database)**.
  * Flexible JSON document structures grouped under isolated collections.
  * Real-time listeners enabled for live appointments, bed availability updates, and diagnostic lab notifications.
* **Security & Access Rules (`firestore.rules`)**:
  * Fine-grained, document-level security policy written in Firebase Security Rules Language (v2).
  * Role-based permissions matching caller authentication tokens (`request.auth.uid`) with resource ownership (`resource.data.personalInfo.uid` or `resource.data.doctorId`).
* **Media & Asset Storage**:
  * Local File System Storage mounted at `/uploads` (PDFs, DICOM, JPEG, PNG, WEBP) served statically by FastAPI.
  * Extensible integration hooks for Firebase Storage and Supabase local storage layers (`supabase-config.js`).

---

## 🎯 Architecture & Engineering Approach

### 1. Zero-Build Lightweight Frontend
Instead of relying on heavy JavaScript frameworks (React, Angular, Vue) requiring Node.js build steps, Webpack, or Vite, Swasthya Sathi employs a **native ES module design**:
* **Instant Deployment & Preview**: Files can be served directly from any HTTP server (e.g., Python `http.server`, Nginx, VS Code Live Server).
* **CDN-Based Dependency Loading**: Firebase SDKs and icon libraries load asynchronously from trusted CDNs.
* **Modularity**: Code is structured into dedicated ES modules (`firebase-config.js`, `auth-guard.js`, `utils.js`, `ads-config.js`, `i18n.js`).

---

### 2. Hybrid Client-Server Data Paradigm
Swasthya Sathi utilizes a hybrid approach balancing direct database access with REST API server capabilities:

```
                          ┌─────────────────────────────────────┐
                          │         Web Browser / Client        │
                          └──────────┬──────────────┬───────────┘
                                     │              │
                    Direct Firestore │              │ HTTP REST Requests
                    SDK Connections  │              │ (File Uploads / Admin)
                                     ▼              ▼
                          ┌────────────────┐  ┌────────────────┐
                          │ Cloud Firestore│  │ FastAPI Server │
                          └────────────────┘  └───────┬────────┘
                                                      │
                                                      │ Firebase Admin SDK
                                                      ▼
                                              ┌────────────────┐
                                              │ Firestore Admin│
                                              └────────────────┘
```

1. **Direct Reactive Reads/Writes**: The web client interacts directly with Firestore for standard operations (reading profile info, booking appointments, listing lab tests) using secure rules.
2. **REST API Endpoint Processing**: Operations requiring elevated permissions, complex file handling, DICOM file validation, or media storage hit the FastAPI backend. FastAPI validates the incoming JWT Bearer token using the Firebase Admin SDK.

---

### 3. Role-Based Access Control (RBAC) Architecture
The platform isolates capabilities across seven distinct user roles:

| Role | Access Scope & Permissions | Key Modules |
|:---|:---|:---|
| **Patient** | Full control over personal health record (PHR/EHR). Can view/upload records, manage consent access links, view health timeline. | `patient/dashboard.html`, `profile.html`, `timeline.html`, `upload.html` |
| **Doctor** | Access to patient queue, digital prescription writing, consultation history, shared medical records. | `doctor/dashboard.html` |
| **Hospital** | Real-time bed management (General/ICU), doctor roster scheduling, OPD/IPD patient tracking. | `hospital/dashboard.html` |
| **Diagnostic Lab**| Test order queue management, result report uploads, patient report dispatching. | `lab/dashboard.html` |
| **Advertiser** | Targeted ad campaign submission, target demographic selection, analytics dashboard. | `advertiser/dashboard.html` |
| **Super Admin** | Platform-wide oversight, advertiser campaign moderation, user management, analytics. | `admin/dashboard.html` |
| **Emergency** | Quick-access responder profile, critical blood group / emergency contact retrieval. | `emergency/profile.html` |

---

## 🗄️ Firestore Database Schema

The database relies on a structured collection layout:

```
cloud_firestore/
│
├── 📂 users/ {uid}
│   ├── uid: string
│   ├── email: string
│   ├── role: "patient" | "doctor" | "hospital" | "lab" | "advertiser" | "admin"
│   └── createdAt: timestamp
│
├── 📂 patients/ {healthId}
│   ├── personalInfo: { uid, name, dob, bloodGroup, emergencyContact }
│   └── 📂 records/ {recordId}  [Sub-collection]
│       ├── doctorId: string
│       ├── hospitalId: string
│       ├── recordType: "Prescription" | "Lab Result" | "Discharge Summary"
│       ├── fileUrl: string
│       └── timestamp: timestamp
│
├── 📂 doctors/ {uid}
│   ├── name: string
│   ├── specialization: string
│   ├── registrationNo: string
│   ├── hospitalAffiliations: array
│   └── schedule: object
│
├── 📂 hospitals/ {uid}
│   ├── name: string
│   ├── totalBeds: number
│   ├── availableBeds: { general: number, icu: number, emergency: number }
│   └── doctors: array
│
├── 📂 laboratories/ {uid}
│   ├── name: string
│   ├── licenseNo: string
│   └── availableTests: array
│
├── 📂 accessLinks/ {linkId}
│   ├── patientHealthId: string
│   ├── requestedBy: string
│   ├── status: "pending" | "approved" | "revoked"
│   └── expiresAt: timestamp
│
├── 📂 appointments/ {apptId}
│   ├── patientHealthId: string
│   ├── doctorId: string
│   ├── hospitalId: string
│   ├── date: string
│   ├── status: "scheduled" | "completed" | "cancelled"
│   └── type: "OPD" | "Teleconsult"
│
└── 📂 advertisements/ {adId}
    ├── title: string
    ├── imageUrl: string
    ├── targetAudience: array
    ├── status: "pending" | "approved" | "rejected"
    ├── impressions: number
    └── clicks: number
```

---

## 🔒 Security Model & Data Governance

1. **Authentication Token Flow**:
   * Patient/User logs in via Firebase Authentication (`login.html`).
   * On authorization, Firebase issues a short-lived JSON Web Token (JWT).
   * Web client includes this token in the `Authorization: Bearer <token>` header for FastAPI REST backend queries.

2. **Firestore Security Enforcement**:
   * `firestore.rules` enforces that patients can only modify their own data.
   * Doctors and Hospitals can only view records for which permission has been explicitly granted or created by their entity.
   * Public read permissions are limited strictly to static resources like approved Advertisements and basic Hospital directories.

3. **Admin Privilege Isolation**:
   * Critical operations (e.g., approving ad campaigns, provisioning admin users) check user roles in Firestore using the helper function `isAdmin()` or the backend's `require_admin` FastAPI dependency.

---

## ⚡ Setup & Execution Guide

### Running the Frontend
The frontend requires no compiler or package manager:
```bash
# Serve frontend via Python HTTP server
cd frontend
python -m http.server 3000
```
Open `http://localhost:3000` in any modern web browser.

### Running the FastAPI Backend
```bash
cd backend
# Create virtual environment (optional)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend development server
uvicorn main:app --reload --port 8000
```

The REST API will be accessible at `http://localhost:8000` with interactive API docs at `http://localhost:8000/docs`.

---

## 📊 Summary Matrix

| Metric / Dimension | Specification |
|:---|:---|
| **Architecture Pattern** | Decoupled Client-Server / Serverless NoSQL Hybrid |
| **Frontend Stack** | HTML5, Vanilla JavaScript (ES Modules), Tailwind CSS |
| **Backend Framework** | FastAPI (Python 3.10+ ASGI) |
| **Database Engine** | Google Cloud Firestore (NoSQL) |
| **Authentication System** | Firebase Auth (JWT + Custom Claims / Firestore Role Doc) |
| **File Storage** | Asynchronous Local Uploads (`/uploads`) + Cloud Storage Ready |
| **Supported User Personas**| 7 Roles (Patient, Doctor, Hospital, Lab, Advertiser, Admin, Emergency) |
