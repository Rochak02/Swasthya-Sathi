// ============================================================
//  index.js – Swasthya Sathi Landing Page Logic
// ============================================================

import { initDarkMode } from './utils.js';
import { subscribeToApprovedAds, createAdvertisement } from './ads-config.js';

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize Dark/Light Mode
  initDarkMode();

  // 2. Mobile Menu Toggle
  const mobileMenuBtn = document.getElementById('mobile-menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  if (mobileMenuBtn && mobileMenu) {
    mobileMenuBtn.addEventListener('click', () => {
      mobileMenu.classList.toggle('hidden');
    });
  }

  // 3. Dynamic Advertisements
  const dynamicAdsContainer = document.getElementById('dynamic-ads-container');
  let currentAds = [];

  function renderAds(category = 'all') {
    if (!dynamicAdsContainer) return;

    dynamicAdsContainer.innerHTML = '';
    const filtered = category === 'all' 
      ? currentAds 
      : currentAds.filter(ad => ad.category === category);

    if (filtered.length === 0) {
      dynamicAdsContainer.innerHTML = `<div class="col-span-full text-center py-10 opacity-50 text-sm font-medium">No partner campaigns available in this category yet.</div>`;
      return;
    }

    filtered.forEach(ad => {
      // Use imageUrl if provided, else fallback icon logic could be added
      const icon = category === 'diagnostics' ? 'fa-vial-virus' : (category === 'pharma' ? 'fa-pills' : 'fa-heart-pulse');
      
      const card = document.createElement('div');
      card.className = 'ad-card flat-panel flat-panel-hover rounded-2xl p-6 group animate-fade-in flex flex-col justify-between';
      card.innerHTML = `
        <div>
          <div class="flex items-center justify-between mb-4">
            <span class="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 badge-minimal">Sponsored</span>
            <span class="text-xs font-semibold text-neutral-500 capitalize">${ad.category}</span>
          </div>
          <h4 class="font-heading font-bold text-lg text-black dark:text-white group-hover:opacity-80 transition-opacity">${ad.title}</h4>
          <p class="text-neutral-600 dark:text-neutral-400 text-xs font-medium mt-2 leading-relaxed">${ad.description}</p>
        </div>
        <div class="mt-6 pt-4 border-t border-black/10 dark:border-white/10 flex items-center justify-between text-xs font-bold text-black dark:text-white cursor-pointer hover:opacity-70 transition-opacity" onclick="window.open('${ad.targetUrl || '#'}', '_blank')">
          <span>Explore Partner</span>
          <i class="fa-solid fa-arrow-up-right-from-square"></i>
        </div>
      `;
      dynamicAdsContainer.appendChild(card);
    });
  }

  // Subscribe to live approved ads for the landing page
  subscribeToApprovedAds((ads) => {
    // Only show ads meant for the landing page or partner cards (adjust filter as needed)
    currentAds = ads.filter(ad => ad.placement === 'partner_card' || ad.placement === 'hero_banner');
    // Read the currently active tab
    const activeTab = document.querySelector('.ad-tab-btn.btn-primary');
    const cat = activeTab ? activeTab.getAttribute('data-category') : 'all';
    renderAds(cat);
  });

  // Category Filtering Tabs
  const adTabs = document.querySelectorAll('.ad-tab-btn');
  adTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const category = tab.getAttribute('data-category');

      // Update active tab styles
      adTabs.forEach(t => {
        t.classList.remove('btn-primary');
        t.classList.add('btn-translucent');
      });
      tab.classList.remove('btn-translucent');
      tab.classList.add('btn-primary');

      // Re-render
      renderAds(category);
    });
  });

  // 4. "Advertise With Us" Modal Logic
  const openAdModalBtn = document.getElementById('open-ad-modal-btn');
  const closeAdModalBtn = document.getElementById('close-ad-modal-btn');
  const adModal = document.getElementById('ad-modal');
  const adForm = document.getElementById('ad-partner-form');

  if (openAdModalBtn && adModal) {
    openAdModalBtn.addEventListener('click', () => {
      adModal.classList.remove('hidden');
      adModal.classList.add('flex');
    });
  }

  if (closeAdModalBtn && adModal) {
    closeAdModalBtn.addEventListener('click', () => {
      adModal.classList.add('hidden');
      adModal.classList.remove('flex');
    });
  }

  if (adForm) {
    adForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const submitBtn = document.getElementById('ad-partner-submit-btn');
      const originalText = submitBtn.textContent;
      submitBtn.textContent = 'Submitting...';
      submitBtn.disabled = true;

      try {
        const companyName = document.getElementById('ad-partner-company').value.trim();
        const email = document.getElementById('ad-partner-email').value.trim();
        const category = document.getElementById('ad-partner-category').value;
        const details = document.getElementById('ad-partner-details').value.trim();

        // Save as a pending advertisement/inquiry
        await createAdvertisement({
          title: 'Partner Inquiry: ' + companyName,
          description: `Email: ${email} | Details: ${details}`,
          category: category,
          placement: 'partner_card', // or something else so admin sees it
          targetUrl: '',
          budget: 'Contact for Quote',
          imageUrl: '',
          advertiserUid: 'landing_inquiry',
          companyName: companyName,
          status: 'pending' // Admin will moderate it
        });

        alert('Thank you for your interest! Your proposal has been submitted to the Admin team.');
        adModal.classList.add('hidden');
        adModal.classList.remove('flex');
        adForm.reset();
      } catch (err) {
        console.error('Error submitting inquiry:', err);
        alert('Failed to submit proposal. Please try again.');
      } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
      }
    });
  }
});
