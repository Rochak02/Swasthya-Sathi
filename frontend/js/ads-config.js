// ============================================================
//  ads-config.js  —  Firestore-backed Advertisement Manager
//  Replaces supabase-config.js (localStorage was never real)
//  All ad data is now persisted in Firestore "advertisements" collection
// ============================================================

import { db } from './firebase-config.js';
import {
  collection, doc, addDoc, updateDoc, getDocs, query,
  where, orderBy, serverTimestamp, increment, onSnapshot
} from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js';

const ADS_COLLECTION = 'advertisements';

// ── Get All Ads (with optional status filter) ─────────────────
/**
 * Fetch advertisements from Firestore.
 * @param {string} [status] - 'approved', 'pending', 'rejected', or undefined for all
 * @returns {Promise<Array>}
 */
export async function getAdvertisements(status) {
  try {
    const adsRef = collection(db, ADS_COLLECTION);
    let q;

    if (status) {
      q = query(adsRef, where('status', '==', status));
    } else {
      q = query(adsRef, orderBy('createdAt', 'desc'));
    }

    const snapshot = await getDocs(q);
    const docs = snapshot.docs.map(d => ({ id: d.id, ...d.data() }));
    if (status) docs.sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
    return docs;
  } catch (err) {
    console.error('[AdsConfig] getAdvertisements error:', err);
    return [];
  }
}

// ── Get Campaigns for a Specific Advertiser ───────────────────
/**
 * @param {string} advertiserUid
 * @returns {Promise<Array>}
 */
export async function getAdvertiserCampaigns(advertiserUid) {
  try {
    const adsRef = collection(db, ADS_COLLECTION);
    const q = query(
      adsRef,
      where('advertiserUid', '==', advertiserUid)
    );
    const snapshot = await getDocs(q);
    const docs = snapshot.docs.map(d => ({ id: d.id, ...d.data() }));
    docs.sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
    return docs;
  } catch (err) {
    console.error('[AdsConfig] getAdvertiserCampaigns error:', err);
    return [];
  }
}

// ── Real-time Listener for Approved Ads (Patient Shop) ────────
/**
 * Subscribe to live changes in approved advertisements.
 * @param {function} callback - Called with array of approved ads on every change
 * @returns {function} unsubscribe function
 */
export function subscribeToApprovedAds(callback) {
  const adsRef = collection(db, ADS_COLLECTION);
  const q = query(adsRef, where('status', '==', 'approved'));

  return onSnapshot(q, (snapshot) => {
    const ads = snapshot.docs.map(d => ({ id: d.id, ...d.data() }));
    ads.sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
    callback(ads);
  }, (err) => {
    console.error('[AdsConfig] subscribeToApprovedAds error:', err);
    callback([]);
  });
}

// ── Real-time Listener for All Ads (Admin Queue) ──────────────
/**
 * Subscribe to live changes in ALL advertisements (for admin moderation).
 * @param {function} callback
 * @returns {function} unsubscribe function
 */
export function subscribeToAllAds(callback) {
  const adsRef = collection(db, ADS_COLLECTION);
  const q = query(adsRef, orderBy('createdAt', 'desc'));

  return onSnapshot(q, (snapshot) => {
    const ads = snapshot.docs.map(d => ({ id: d.id, ...d.data() }));
    callback(ads);
  }, (err) => {
    console.error('[AdsConfig] subscribeToAllAds error:', err);
    callback([]);
  });
}

// ── Real-time Listener for Advertiser's Own Campaigns ─────────
/**
 * Subscribe to live changes in an advertiser's own campaigns.
 * @param {string} advertiserUid
 * @param {function} callback
 * @returns {function} unsubscribe
 */
export function subscribeToAdvertiserCampaigns(advertiserUid, callback) {
  const adsRef = collection(db, ADS_COLLECTION);
  const q = query(
    adsRef,
    where('advertiserUid', '==', advertiserUid),
    orderBy('createdAt', 'desc')
  );

  return onSnapshot(q, (snapshot) => {
    const ads = snapshot.docs.map(d => ({ id: d.id, ...d.data() }));
    callback(ads);
  }, (err) => {
    console.error('[AdsConfig] subscribeToAdvertiserCampaigns error:', err);
    callback([]);
  });
}

// ── Create a New Ad Campaign ──────────────────────────────────
/**
 * Advertiser submits a new campaign. Status defaults to 'pending'.
 * @param {Object} adData
 * @returns {Promise<{id: string, ...adData}>}
 */
export async function createAdvertisement(adData) {
  try {
    const newAd = {
      advertiserUid:   adData.advertiserUid || 'unknown',
      companyName:     adData.companyName   || 'Partner Brand',
      title:           adData.title,
      description:     adData.description   || '',
      category:        adData.category      || 'wellness',
      placement:       adData.placement     || 'partner_card',
      targetUrl:       adData.targetUrl     || '#',
      imageUrl:        adData.imageUrl      || '',
      status:          adData.status        || 'pending',
      rejectionReason: null,
      impressions:     0,
      clicks:          0,
      budget:          adData.budget        || '₹0',
      createdAt:       serverTimestamp(),
    };

    const docRef = await addDoc(collection(db, ADS_COLLECTION), newAd);
    console.log('[AdsConfig] New ad created:', docRef.id);
    return { id: docRef.id, ...newAd };
  } catch (err) {
    console.error('[AdsConfig] createAdvertisement error:', err);
    throw err;
  }
}

// ── Admin: Approve an Ad ──────────────────────────────────────
/**
 * @param {string} adId
 */
export async function approveAdvertisement(adId) {
  try {
    const adRef = doc(db, ADS_COLLECTION, adId);
    await updateDoc(adRef, {
      status:          'approved',
      rejectionReason: null,
      approvedAt:      serverTimestamp(),
    });
    console.log('[AdsConfig] Ad approved:', adId);
  } catch (err) {
    console.error('[AdsConfig] approveAdvertisement error:', err);
    throw err;
  }
}

// ── Admin: Reject an Ad with Reason ──────────────────────────
/**
 * @param {string} adId
 * @param {string} reason
 */
export async function rejectAdvertisement(adId, reason = 'Rejected by Admin') {
  try {
    const adRef = doc(db, ADS_COLLECTION, adId);
    await updateDoc(adRef, {
      status:          'rejected',
      rejectionReason: reason,
      rejectedAt:      serverTimestamp(),
    });
    console.log('[AdsConfig] Ad rejected:', adId, '| Reason:', reason);
  } catch (err) {
    console.error('[AdsConfig] rejectAdvertisement error:', err);
    throw err;
  }
}

// ── Track Impression (atomic increment) ──────────────────────
/**
 * @param {string} adId
 */
export async function incrementAdImpression(adId) {
  try {
    const adRef = doc(db, ADS_COLLECTION, adId);
    await updateDoc(adRef, { impressions: increment(1) });
  } catch (err) {
    // Silently fail — don't break UI for analytics errors
    console.warn('[AdsConfig] incrementAdImpression failed for', adId, err.message);
  }
}

// ── Track Click (atomic increment) ───────────────────────────
/**
 * @param {string} adId
 */
export async function incrementAdClick(adId) {
  try {
    const adRef = doc(db, ADS_COLLECTION, adId);
    await updateDoc(adRef, { clicks: increment(1) });
  } catch (err) {
    console.warn('[AdsConfig] incrementAdClick failed for', adId, err.message);
  }
}
