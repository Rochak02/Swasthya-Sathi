# 🖥️ Swasthya Sathi — Frontend

This directory contains the complete frontend source code for **Swasthya Sathi** — a role-based digital healthcare platform for India.

> **Zero dependencies. No build step. Open and run.**

---

## 🗂️ Folder Overview

| Folder / File | Description |
|---|---|
| `index.html` | Landing / marketing homepage |
| `login.html` | Unified login for all roles |
| `patient/` | Patient EHR portal (dashboard, profile, timeline, uploads, permissions) |
| `doctor/` | Doctor dashboard (appointments, patients, prescriptions) |
| `hospital/` | Hospital admin (beds, OPD/IPD, staff) |
| `lab/` | Lab portal (test orders, result uploads) |
| `admin/` | Super-admin panel (user management, moderation) |
| `advertiser/` | Ad campaign management portal |
| `emergency/` | Emergency responder profile & quick tools |
| `register/` | Role-specific registration/onboarding forms |
| `css/custom.css` | Global design tokens, animations, shared styles |
| `js/` | Shared JavaScript utilities and configuration |
| `assets/` | Static images and media |

---

## 🚀 Running the Frontend Locally

### Using Python (simplest)
```bash
cd frontend
python -m http.server 8080
```
Then visit: **http://localhost:8080**

### Using VS Code Live Server
Right-click `index.html` → **Open with Live Server**

### Using Node
```bash
npx http-server . -p 8080
```

---

## 🧩 Key JavaScript Modules

| File | Purpose |
|---|---|
| `js/firebase-config.js` | Firebase app init — exports `auth`, `db`, `API_BASE` |
| `js/auth-guard.js` | Protects routes; redirects unauthorized users |
| `js/i18n.js` | Internationalization — Hindi, Tamil, Bengali, and more |
| `js/utils.js` | Shared helpers (toast notifications, date formatters, etc.) |
| `js/ads-config.js` | Ad placement engine & render helpers |
| `js/supabase-config.js` | Ad storage layer with local-first fallback |
| `js/index.js` | Landing page behavior (animations, nav, counters) |

---

## 🎨 Design System

The project uses **Tailwind CSS** (via CDN) paired with a custom CSS file (`css/custom.css`) for:

- **Dark mode** (default) with light mode toggle
- **Color palette**: Black/white primary with accent greens and purples
- **Typography**: `Outfit` (headings) + `Plus Jakarta Sans` (body)
- **Glassmorphism** cards and pill navbar
- **Smooth micro-animations** on all interactive elements

---

## 🔒 Authentication Flow

1. User visits `login.html`
2. Firebase Auth (Email/Password) validates credentials
3. Firestore fetches the user's `role` field
4. `auth-guard.js` redirects to the correct dashboard:
   - `patient` → `/patient/dashboard.html`
   - `doctor` → `/doctor/dashboard.html`
   - `hospital` → `/hospital/dashboard.html`
   - `lab` → `/lab/dashboard.html`
   - `admin` → `/admin/dashboard.html`
   - `advertiser` → `/advertiser/dashboard.html`

---

## 📸 Pages at a Glance

### Landing Page (`index.html`)
Hero section with animated 3D visuals, platform feature cards, testimonials, partner logos, and a CTA to register.

### Patient Dashboard (`patient/dashboard.html`)
The richest page on the platform — includes:
- Health stats overview (BMI, blood group, vitals)
- Recent prescriptions & lab reports
- Upcoming appointments
- Shared access management
- Emergency ID card
- Quick action buttons

### Admin Dashboard (`admin/dashboard.html`)
- User verification queue
- Ad campaign moderation
- Platform metrics & charts

---

*For full project details, see the [root README](../README.md).*
