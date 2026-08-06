// ============================================================
//  auth-guard.js  –  Auth Protection & Role Guard
//  Usage: import { requireAuth, requireRole, getToken } from './auth-guard.js'
// ============================================================

import { auth, db }     from "./firebase-config.js";
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { doc, getDoc }  from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

// ── Resolve the correct path depth for redirects ──────────────
//  (pages in subfolders need ../../login.html, root needs ./login.html)
function loginPath() {
  const depth = location.pathname.split('/').filter(Boolean).length;
  return depth >= 2 ? Array(depth - 1).fill('..').join('/') + '/login.html' : 'login.html';
}

// ── Wait for auth state + load userData ───────────────────────
export function requireAuth(callback) {
  onAuthStateChanged(auth, async (user) => {
    if (!user) {
      window.location.href = loginPath();
      return;
    }
    try {
      const snap = await getDoc(doc(db, "users", user.uid));
      const userData = snap.exists() ? snap.data() : {};

      // Enrich name for hospitals and labs
      if (userData.role === "hospital") {
        const h = await getDoc(doc(db, "hospitals", user.uid));
        if (h.exists()) userData.name = h.data().name;
      } else if (userData.role === "lab") {
        const l = await getDoc(doc(db, "laboratories", user.uid));
        if (l.exists()) userData.name = l.data().name;
      }

      callback(user, userData);
    } catch (e) {
      console.error("Auth guard error:", e);
      callback(user, {});
    }
  });
}

// ── Require a specific role ────────────────────────────────────
export function requireRole(allowedRoles, callback) {
  requireAuth((user, userData) => {
    if (!allowedRoles.includes(userData.role)) {
      window.location.href = loginPath();
      return;
    }
    callback(user, userData);
  });
}

// ── Get Firebase ID token for backend calls ────────────────────
export async function getToken() {
  const user = auth.currentUser;
  if (!user) throw new Error("Not authenticated");
  return await user.getIdToken();
}

// ── Sign out helper ────────────────────────────────────────────
export async function signOutUser() {
  await auth.signOut();
  window.location.href = loginPath();
}
