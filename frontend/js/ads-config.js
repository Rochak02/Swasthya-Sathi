// ============================================================
//  ads-config.js  —  Backend API-Powered Advertisement Manager
//
//  ✅ All reads & writes go through FastAPI backend (Admin SDK)
//  ✅ Bypasses Firestore client security rules entirely
//  ✅ Uses 5-second polling for "near real-time" updates
//  ✅ Zero direct Firestore client SDK dependency for ads
// ============================================================

import { API_BASE } from './firebase-config.js';

const POLL_INTERVAL_MS = 5000; // 5-second poll interval

// ── Internal helper: fetch campaigns from backend ─────────────
async function fetchCampaigns(params = {}) {
  try {
    const url = new URL(`${API_BASE}/api/campaigns`);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        url.searchParams.set(k, v);
      }
    });

    const res = await fetch(url.toString());
    if (!res.ok) {
      console.error('[AdsConfig] Backend returned', res.status, await res.text());
      return [];
    }
    const data = await res.json();
    return data.campaigns || [];
  } catch (err) {
    console.error('[AdsConfig] fetchCampaigns error:', err);
    return [];
  }
}

// ── Get All Ads (with optional status filter) ─────────────────
/**
 * Fetch advertisements from the backend.
 * @param {string} [status] - 'approved', 'pending', 'rejected', or undefined for all
 * @returns {Promise<Array>}
 */
export async function getAdvertisements(status) {
  return fetchCampaigns(status ? { status } : {});
}

// ── Get Campaigns for a Specific Advertiser ───────────────────
/**
 * @param {string} advertiserUid
 * @returns {Promise<Array>}
 */
export async function getAdvertiserCampaigns(advertiserUid) {
  return fetchCampaigns({ advertiserUid });
}

// ── Real-time Polling: Approved Ads (Patient Shop) ────────────
/**
 * Subscribe to approved ads via polling (replaces Firestore onSnapshot).
 * @param {function} callback - Called with array of approved ads every poll cycle
 * @returns {function} unsubscribe — call to stop polling
 */
export function subscribeToApprovedAds(callback) {
  let cancelled = false;

  async function poll() {
    if (cancelled) return;
    const ads = await fetchCampaigns({ status: 'approved' });
    if (!cancelled) callback(ads);
  }

  poll(); // Immediate first load
  const timer = setInterval(poll, POLL_INTERVAL_MS);

  return () => {
    cancelled = true;
    clearInterval(timer);
  };
}

// ── Real-time Polling: All Ads (Admin Queue) ──────────────────
/**
 * Subscribe to all ads via polling.
 * @param {function} callback
 * @returns {function} unsubscribe
 */
export function subscribeToAllAds(callback) {
  let cancelled = false;

  async function poll() {
    if (cancelled) return;
    const ads = await fetchCampaigns();
    if (!cancelled) callback(ads);
  }

  poll();
  const timer = setInterval(poll, POLL_INTERVAL_MS);

  return () => {
    cancelled = true;
    clearInterval(timer);
  };
}

// ── Real-time Polling: Advertiser's Own Campaigns ─────────────
/**
 * Subscribe to an advertiser's own campaigns via polling.
 * @param {string} advertiserUid
 * @param {function} callback
 * @returns {function} unsubscribe
 */
export function subscribeToAdvertiserCampaigns(advertiserUid, callback) {
  let cancelled = false;

  async function poll() {
    if (cancelled) return;
    const ads = await fetchCampaigns({ advertiserUid });
    if (!cancelled) callback(ads);
  }

  poll();
  const timer = setInterval(poll, POLL_INTERVAL_MS);

  return () => {
    cancelled = true;
    clearInterval(timer);
  };
}

// ── Create a New Ad Campaign ──────────────────────────────────
/**
 * Submit a new campaign via the backend API.
 * @param {Object} adData
 * @returns {Promise<{id: string, ...adData}>}
 */
export async function createAdvertisement(adData) {
  const res = await fetch(`${API_BASE}/api/campaigns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(adData),
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    const detail = errBody.detail || `HTTP ${res.status}`;
    console.error('[AdsConfig] createAdvertisement failed:', detail);
    throw new Error(detail);
  }

  const data = await res.json();
  console.log('[AdsConfig] New campaign created:', data.id);
  return { id: data.id, ...adData };
}

// ── Admin: Approve an Ad ──────────────────────────────────────
/**
 * @param {string} adId
 */
export async function approveAdvertisement(adId) {
  const res = await fetch(`${API_BASE}/api/campaigns/${adId}/approve`, {
    method: 'PUT',
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || 'Failed to approve campaign');
  }
  console.log('[AdsConfig] Ad approved:', adId);
}

// ── Admin: Reject an Ad with Reason ──────────────────────────
/**
 * @param {string} adId
 * @param {string} reason
 */
export async function rejectAdvertisement(adId, reason = 'Rejected by Admin') {
  const res = await fetch(`${API_BASE}/api/campaigns/${adId}/reject`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || 'Failed to reject campaign');
  }
  console.log('[AdsConfig] Ad rejected:', adId, '| Reason:', reason);
}

// ── Track Impression (fire-and-forget) ───────────────────────
/**
 * @param {string} adId
 */
export async function incrementAdImpression(adId) {
  try {
    await fetch(`${API_BASE}/api/campaigns/${adId}/impression`, { method: 'POST' });
  } catch (err) {
    // Silently fail — analytics errors must never break the UI
    console.warn('[AdsConfig] incrementAdImpression failed for', adId);
  }
}

// ── Track Click (fire-and-forget) ────────────────────────────
/**
 * @param {string} adId
 */
export async function incrementAdClick(adId) {
  try {
    await fetch(`${API_BASE}/api/campaigns/${adId}/click`, { method: 'POST' });
  } catch (err) {
    console.warn('[AdsConfig] incrementAdClick failed for', adId);
  }
}


