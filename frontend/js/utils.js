// ============================================================
//  utils.js  –  Shared Utility Functions
//  Monochrome Clean Architecture (No Emoji Icons)
// ============================================================

// ── Toast Notifications ───────────────────────────────────────
export function toast(message, type = "info", duration = 3500) {
  const colors = {
    success: "bg-black text-white dark:bg-white dark:text-black border border-black/20 dark:border-white/20",
    error:   "bg-black text-white dark:bg-white dark:text-black border border-red-500/50",
    warning: "bg-black text-white dark:bg-white dark:text-black border border-amber-500/50",
    info:    "bg-black text-white dark:bg-white dark:text-black border border-black/20 dark:border-white/20"
  };
  const icons = {
    success: "✓", error: "✕", warning: "!", info: "i"
  };

  const el = document.createElement("div");
  el.className = `fixed top-5 right-5 z-[9999] flex items-center gap-3 px-5 py-4 rounded-2xl shadow-2xl font-bold text-xs max-w-sm transform transition-all duration-300 translate-x-full ${colors[type] || colors.info}`;
  el.innerHTML = `<span class="text-sm">${icons[type] || icons.info}</span><span>${message}</span>`;
  document.body.appendChild(el);

  requestAnimationFrame(() => {
    el.classList.remove("translate-x-full");
  });

  setTimeout(() => {
    el.classList.add("translate-x-full");
    setTimeout(() => el.remove(), 300);
  }, duration);
}

// ── Format Firestore Timestamp or Date ────────────────────────
export function formatDate(dateVal) {
  if (!dateVal) return "Unknown";
  let d;
  if (dateVal?.toDate) d = dateVal.toDate();
  else if (dateVal?.seconds) d = new Date(dateVal.seconds * 1000);
  else d = new Date(dateVal);

  return d.toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric"
  });
}

export function formatDateTime(dateVal) {
  if (!dateVal) return "";
  let d;
  if (dateVal?.toDate) d = dateVal.toDate();
  else if (dateVal?.seconds) d = new Date(dateVal.seconds * 1000);
  else d = new Date(dateVal);

  return d.toLocaleString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit"
  });
}

// ── Loading Spinner ───────────────────────────────────────────
export function setLoading(buttonEl, isLoading, text = "Submit") {
  if (isLoading) {
    buttonEl.disabled = true;
    buttonEl.innerHTML = `<span class="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>`;
  } else {
    buttonEl.disabled = false;
    buttonEl.textContent = text;
  }
}

// ── File URL helper ───────────────────────────────────────────
export function resolveFileUrl(url) {
  if (!url) return "#";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  const path = url.startsWith("/") ? url : "/" + url;
  return `http://localhost:8000${path}`;
}

// ── Record type to display name ───────────────────────────────
export function recordTypeLabel(type) {
  const labels = {
    blood_test:       "Blood Test Report",
    urine_test:       "Urine Test Report",
    pathology:        "Pathology Report",
    mri:              "MRI Scan",
    ct_scan:          "CT Scan",
    xray:             "X-Ray Scan",
    prescription:     "Prescription",
    discharge_summary:"Discharge Summary",
    vaccination:      "Vaccination Certificate",
    doctors_note:     "Doctor's Clinical Note",
    bill:             "Medical Bill & Invoice"
  };
  return labels[type] || type?.replace(/_/g, " ") || "Record";
}

// ── Record type to FontAwesome Icon Class ─────────────────────
export function recordTypeIcon(type) {
  const icons = {
    blood_test:       "fa-flask",
    urine_test:       "fa-vial",
    pathology:        "fa-microscope",
    mri:              "fa-wave-square",
    ct_scan:          "fa-radiation",
    xray:             "fa-x-ray",
    prescription:     "fa-prescription-bottle-medical",
    discharge_summary:"fa-file-medical",
    vaccination:      "fa-syringe",
    doctors_note:     "fa-user-doctor",
    bill:             "fa-receipt"
  };
  return icons[type] || "fa-file-lines";
}

// ── User initials helper ──────────────────────────────────────
export function initials(name) {
  if (!name) return "P";
  const parts = name.trim().split(" ").filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

// ── Dark/Light Mode Theme Switcher (System Preference + Manual Toggle) ───
export function initDarkMode() {
  const storedTheme = localStorage.getItem("theme");

  if (storedTheme) {
    if (storedTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  } else {
    // Detect Browser / OS system color scheme preference
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (prefersDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }

  // Listen for browser/OS system theme preference changes dynamically
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
      if (!localStorage.getItem("theme")) {
        if (e.matches) {
          document.documentElement.classList.add("dark");
        } else {
          document.documentElement.classList.remove("dark");
        }
      }
    });
  }

  const toggleBtns = document.querySelectorAll("#theme-toggle");
  toggleBtns.forEach(btn => {
    btn.onclick = () => {
      const isDark = document.documentElement.classList.toggle("dark");
      localStorage.setItem("theme", isDark ? "dark" : "light");
    };
  });
}
