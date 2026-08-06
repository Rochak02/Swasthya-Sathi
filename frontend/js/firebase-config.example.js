// ============================================================
//  firebase-config.example.js  –  SETUP TEMPLATE
//
//  HOW TO USE:
//  1. Copy this file and rename it to: firebase-config.js
//  2. Go to https://console.firebase.google.com
//  3. Open your project → Project Settings → Your Apps → Web App
//  4. Copy your firebaseConfig object values below
//  5. NEVER commit firebase-config.js to git (it is in .gitignore)
// ============================================================

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth }        from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { getFirestore }   from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

// 👇 Replace all values below with your actual Firebase project config
const firebaseConfig = {
  apiKey:            "YOUR_FIREBASE_API_KEY",
  authDomain:        "YOUR_PROJECT_ID.firebaseapp.com",
  projectId:         "YOUR_PROJECT_ID",
  storageBucket:     "YOUR_PROJECT_ID.firebasestorage.app",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId:             "YOUR_APP_ID",
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const db   = getFirestore(app);

// Backend URL — change this when deploying to production
export const API_BASE = "http://localhost:8000";
