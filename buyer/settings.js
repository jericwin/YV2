/**
 * settings.js — Buyer Settings Page Logic
 * All data is persisted in localStorage under the 'yv2_profile' key.
 */

// ── Storage keys ──────────────────────────────────────────────────────────────
const PROFILE_KEY   = 'yv2_profile';
const PREFS_KEY     = 'yv2_prefs';
const CART_KEY      = 'yv2_cart';
const WISHLIST_KEY  = 'yv2_wishlist';

// ── Default profile structure ─────────────────────────────────────────────────
const defaultProfile = {
  firstName: '',
  lastName: '',
  displayName: '',
  phone: '',
  bio: '',
  email: 'guest@youversion2.com',
  password: '',          // stored as plain text (demo only — not production safe)
  street: '',
  city: '',
  province: '',
  zipcode: '',
  country: 'PH',
};

const defaultPrefs = {
  notifOrders: true,
  notifArrivals: true,
  notifPromos: false,
  notifNewsletter: false,
  lang: 'en',
  currency: 'PHP',
};

// ── Persistence helpers ───────────────────────────────────────────────────────
function loadProfile() {
  try {
    const s = localStorage.getItem(PROFILE_KEY);
    return s ? { ...defaultProfile, ...JSON.parse(s) } : { ...defaultProfile };
  } catch { return { ...defaultProfile }; }
}

function saveProfile(data) {
  const current = loadProfile();
  localStorage.setItem(PROFILE_KEY, JSON.stringify({ ...current, ...data }));
}

function loadPrefs() {
  try {
    const s = localStorage.getItem(PREFS_KEY);
    return s ? { ...defaultPrefs, ...JSON.parse(s) } : { ...defaultPrefs };
  } catch { return { ...defaultPrefs }; }
}

function savePrefs(data) {
  localStorage.setItem(PREFS_KEY, JSON.stringify(data));
}

// ── Badge / sidebar helpers ───────────────────────────────────────────────────
function updateBadges() {
  try {
    const cart = JSON.parse(localStorage.getItem(CART_KEY) || '[]');
    const wishlist = JSON.parse(localStorage.getItem(WISHLIST_KEY) || '[]');
    const qty = cart.reduce((s, i) => s + (i.quantity || 0), 0);
    const wb = document.getElementById('wishlist-badge');
    const cb = document.getElementById('cart-badge');
    if (wb) wb.innerText = wishlist.length;
    if (cb) cb.innerText = qty;
  } catch {}
}

function updateSidebar(profile) {
  const nameEl    = document.getElementById('sidebar-name');
  const emailEl   = document.getElementById('sidebar-email');
  const initialsEl= document.getElementById('sidebar-initials');
  const currentEmailEl = document.getElementById('current-email');

  const fullName = [profile.firstName, profile.lastName].filter(Boolean).join(' ') || 'Guest User';
  const initials = (profile.firstName?.[0] ?? '') + (profile.lastName?.[0] ?? '');

  if (nameEl)    nameEl.innerText    = profile.displayName || fullName;
  if (emailEl)   emailEl.innerText   = profile.email || '—';
  if (initialsEl) initialsEl.innerText = initials.toUpperCase() || '?';
  if (currentEmailEl) currentEmailEl.value = profile.email || '';
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const iconMap  = { success: 'check-circle', info: 'info', warning: 'alert-triangle', error: 'x-circle' };
  const colorMap = { success: '#1565C0', info: '#0ea5e9', warning: '#f59e0b', error: '#ef4444' };
  const toast = document.createElement('div');
  toast.style.cssText = `
    display:flex; align-items:center; gap:.75rem;
    background:#fff; border:1.5px solid ${colorMap[type]};
    border-radius:12px; padding:.85rem 1.1rem;
    box-shadow:0 8px 24px rgba(0,0,0,.12); min-width:260px; max-width:360px;
    animation:fadeInToast .35s cubic-bezier(.34,1.56,.64,1) forwards;
    font-family:'Poppins',sans-serif;
  `;
  toast.innerHTML = `
    <span style="color:${colorMap[type]};display:flex;flex-shrink:0"><i data-lucide="${iconMap[type]}"></i></span>
    <span style="font-size:.88rem;font-weight:500;color:#1F2937;flex:1">${message}</span>
  `;
  container.appendChild(toast);
  lucide.createIcons();
  setTimeout(() => {
    toast.style.animation = 'fadeOutToast .4s cubic-bezier(.4,0,1,1) forwards';
    setTimeout(() => toast.remove(), 400);
  }, 3500);
}

// ── Tab switching ─────────────────────────────────────────────────────────────
function switchTab(tab) {
  // Sidebar items
  document.querySelectorAll('.settings-nav-item').forEach(el => {
    el.classList.toggle('active', el.getAttribute('data-tab') === tab);
  });
  // Strip buttons
  document.querySelectorAll('.tab-strip-btn').forEach(el => {
    el.classList.toggle('active', el.getAttribute('data-tab') === tab);
  });
  // Panels
  document.querySelectorAll('.settings-panel').forEach(p => {
    p.classList.toggle('active', p.id === `panel-${tab}`);
  });
}

// ── Field validation helpers ──────────────────────────────────────────────────
function setError(fieldId, errId, show) {
  const field = document.getElementById(fieldId);
  const err   = document.getElementById(errId);
  if (field) field.classList.toggle('is-error', show);
  if (err)   err.classList.toggle('visible', show);
}

function clearErrors(...errIds) {
  errIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove('visible');
  });
}

function showInlineSuccess(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add('visible');
  setTimeout(() => el.classList.remove('visible'), 4000);
}

// ── Password strength evaluator ───────────────────────────────────────────────
function evalPasswordStrength(value) {
  const fill  = document.getElementById('pw-strength-fill');
  const label = document.getElementById('pw-strength-label');
  if (!fill || !label) return;

  if (!value) {
    fill.style.width = '0%';
    label.textContent = 'Enter a password to see its strength';
    label.style.color = 'var(--text-light)';
    return;
  }

  let score = 0;
  if (value.length >= 8)  score++;
  if (value.length >= 12) score++;
  if (/[A-Z]/.test(value)) score++;
  if (/[0-9]/.test(value)) score++;
  if (/[^A-Za-z0-9]/.test(value)) score++;

  const levels = [
    { pct: '10%', color: '#ef4444', text: 'Very Weak' },
    { pct: '30%', color: '#f97316', text: 'Weak' },
    { pct: '55%', color: '#eab308', text: 'Fair' },
    { pct: '78%', color: '#22c55e', text: 'Strong' },
    { pct: '100%', color: '#059669', text: 'Very Strong' },
  ];
  const lvl = levels[Math.min(score, 4)];
  fill.style.width    = lvl.pct;
  fill.style.background = lvl.color;
  label.textContent   = lvl.text;
  label.style.color   = lvl.color;
}

// ── Toggle password visibility ────────────────────────────────────────────────
function initPasswordToggles() {
  document.querySelectorAll('.toggle-pw').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input    = document.getElementById(targetId);
      if (!input) return;
      const isHidden = input.type === 'password';
      input.type = isHidden ? 'text' : 'password';
      btn.innerHTML = isHidden
        ? '<i data-lucide="eye-off"></i>'
        : '<i data-lucide="eye"></i>';
      lucide.createIcons();
    });
  });
}

// ── Populate form fields from stored data ─────────────────────────────────────
function populateForms() {
  const profile = loadProfile();
  const prefs   = loadPrefs();

  // Personal Info
  setVal('first-name',   profile.firstName);
  setVal('last-name',    profile.lastName);
  setVal('display-name', profile.displayName);
  setVal('phone',        profile.phone);
  setVal('bio',          profile.bio);

  // Address
  setVal('street',   profile.street);
  setVal('city',     profile.city);
  setVal('province', profile.province);
  setVal('zipcode',  profile.zipcode);
  setSelectVal('country', profile.country);

  // Credentials
  setVal('current-email', profile.email);

  // Preferences
  setChecked('notif-orders',      prefs.notifOrders);
  setChecked('notif-arrivals',    prefs.notifArrivals);
  setChecked('notif-promos',      prefs.notifPromos);
  setChecked('notif-newsletter',  prefs.notifNewsletter);
  setSelectVal('lang',     prefs.lang);
  setSelectVal('currency', prefs.currency);

  updateSidebar(profile);
}

function setVal(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val || '';
}
function setSelectVal(id, val) {
  const el = document.getElementById(id);
  if (el && val) el.value = val;
}
function setChecked(id, val) {
  const el = document.getElementById(id);
  if (el) el.checked = !!val;
}

// ── Save handlers ─────────────────────────────────────────────────────────────

// Profile
function handleProfileSave() {
  const firstName = document.getElementById('first-name')?.value.trim();
  const lastName  = document.getElementById('last-name')?.value.trim();
  let valid = true;

  clearErrors('first-name-err', 'last-name-err');
  if (!firstName) { setError('first-name', 'first-name-err', true); valid = false; }
  if (!lastName)  { setError('last-name',  'last-name-err',  true); valid = false; }
  if (!valid) return;

  saveProfile({
    firstName,
    lastName,
    displayName: document.getElementById('display-name')?.value.trim(),
    phone: document.getElementById('phone')?.value.trim(),
    bio:   document.getElementById('bio')?.value.trim(),
  });

  updateSidebar(loadProfile());
  showInlineSuccess('profile-success');
  showToast('Profile information saved!', 'success');
}

// Address
function handleAddressSave() {
  saveProfile({
    street:   document.getElementById('street')?.value.trim(),
    city:     document.getElementById('city')?.value.trim(),
    province: document.getElementById('province')?.value.trim(),
    zipcode:  document.getElementById('zipcode')?.value.trim(),
    country:  document.getElementById('country')?.value,
  });
  showInlineSuccess('address-success');
  showToast('Shipping address saved!', 'success');
}

// Email
function handleEmailSave() {
  const newEmail     = document.getElementById('new-email')?.value.trim();
  const confirmEmail = document.getElementById('confirm-email')?.value.trim();
  let valid = true;

  clearErrors('new-email-err', 'confirm-email-err');

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!newEmail || !emailRegex.test(newEmail)) {
    setError('new-email', 'new-email-err', true); valid = false;
  }
  if (newEmail !== confirmEmail) {
    setError('confirm-email', 'confirm-email-err', true); valid = false;
  }
  if (!valid) return;

  saveProfile({ email: newEmail });

  // Clear fields
  setVal('new-email', '');
  setVal('confirm-email', '');
  setVal('current-email', newEmail);
  updateSidebar(loadProfile());
  showInlineSuccess('email-success');
  showToast('Email address updated!', 'success');
}

// Password
function handlePasswordSave() {
  const currentPw = document.getElementById('current-pw')?.value;
  const newPw     = document.getElementById('new-pw')?.value;
  const confirmPw = document.getElementById('confirm-pw')?.value;
  const profile   = loadProfile();
  let valid = true;

  clearErrors('current-pw-err', 'new-pw-err', 'confirm-pw-err');

  // Validate current password if one is stored
  if (profile.password && currentPw !== profile.password) {
    setError('current-pw', 'current-pw-err', true);
    document.getElementById('current-pw-err').textContent = 'Incorrect current password.';
    valid = false;
  } else if (!currentPw) {
    setError('current-pw', 'current-pw-err', true);
    document.getElementById('current-pw-err').textContent = 'Current password is required.';
    valid = false;
  }

  if (!newPw || newPw.length < 8) {
    setError('new-pw', 'new-pw-err', true); valid = false;
  }
  if (newPw !== confirmPw) {
    setError('confirm-pw', 'confirm-pw-err', true);
    document.getElementById('confirm-pw-err').textContent = 'Passwords do not match.';
    valid = false;
  }
  if (!valid) return;

  saveProfile({ password: newPw });

  // Clear fields
  ['current-pw', 'new-pw', 'confirm-pw'].forEach(id => setVal(id, ''));
  evalPasswordStrength('');
  showInlineSuccess('pw-success');
  showToast('Password changed successfully!', 'success');
}

// Preferences
function handlePrefsSave() {
  savePrefs({
    notifOrders:     document.getElementById('notif-orders')?.checked,
    notifArrivals:   document.getElementById('notif-arrivals')?.checked,
    notifPromos:     document.getElementById('notif-promos')?.checked,
    notifNewsletter: document.getElementById('notif-newsletter')?.checked,
    lang:     document.getElementById('lang')?.value,
    currency: document.getElementById('currency')?.value,
  });
  showToast('Preferences saved!', 'success');
}

function handleRegionalSave() {
  const prefs = loadPrefs();
  savePrefs({
    ...prefs,
    lang:     document.getElementById('lang')?.value,
    currency: document.getElementById('currency')?.value,
  });
  showToast('Regional settings saved!', 'success');
}

// Discard helpers
function discardProfile() {
  populateForms();
  showToast('Changes discarded.', 'info');
}

// ── Danger zone ───────────────────────────────────────────────────────────────
function dangerClearWishlist() {
  if (!confirm('Are you sure you want to clear your entire wishlist? This cannot be undone.')) return;
  localStorage.removeItem(WISHLIST_KEY);
  updateBadges();
  showToast('Wishlist cleared.', 'info');
}

function dangerClearCart() {
  if (!confirm('Are you sure you want to empty your shopping cart?')) return;
  localStorage.removeItem(CART_KEY);
  updateBadges();
  showToast('Cart cleared.', 'info');
}

function dangerResetAll() {
  if (!confirm('⚠️ This will delete ALL your locally stored data including profile, address, cart, and wishlist. Continue?')) return;
  [PROFILE_KEY, PREFS_KEY, CART_KEY, WISHLIST_KEY].forEach(k => localStorage.removeItem(k));
  populateForms();
  updateBadges();
  showToast('All account data has been reset.', 'info');
}

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();

  // Mobile drawer
  const mobileMenuTrigger = document.getElementById('mobile-menu-trigger');
  const closeMobileDrawer = document.getElementById('close-mobile-drawer');
  const mobileDrawer      = document.getElementById('mobile-drawer');
  if (mobileMenuTrigger) mobileMenuTrigger.addEventListener('click', () => mobileDrawer.classList.remove('hidden'));
  if (closeMobileDrawer) closeMobileDrawer.addEventListener('click', () => mobileDrawer.classList.add('hidden'));

  // Sidebar nav items
  document.querySelectorAll('.settings-nav-item[data-tab]').forEach(el => {
    el.addEventListener('click', () => switchTab(el.getAttribute('data-tab')));
  });

  // Mobile tab strip
  document.querySelectorAll('.tab-strip-btn[data-tab]').forEach(el => {
    el.addEventListener('click', () => switchTab(el.getAttribute('data-tab')));
  });

  // Profile panel buttons
  document.getElementById('profile-save-btn')?.addEventListener('click', handleProfileSave);
  document.getElementById('profile-discard-btn')?.addEventListener('click', discardProfile);
  document.getElementById('address-save-btn')?.addEventListener('click', handleAddressSave);
  document.getElementById('address-discard-btn')?.addEventListener('click', discardProfile);

  // Credentials panel
  document.getElementById('email-save-btn')?.addEventListener('click', handleEmailSave);
  document.getElementById('pw-save-btn')?.addEventListener('click', handlePasswordSave);

  // Preferences panel
  document.getElementById('prefs-save-btn')?.addEventListener('click', handlePrefsSave);
  document.getElementById('regional-save-btn')?.addEventListener('click', handleRegionalSave);

  // Danger zone
  document.getElementById('danger-clear-wishlist')?.addEventListener('click', dangerClearWishlist);
  document.getElementById('danger-clear-cart')?.addEventListener('click', dangerClearCart);
  document.getElementById('danger-reset-all')?.addEventListener('click', dangerResetAll);

  // Avatar click → focus first name
  document.getElementById('sidebar-avatar')?.addEventListener('click', () => {
    switchTab('profile');
    document.getElementById('first-name')?.focus();
  });

  // Password toggles
  initPasswordToggles();

  // Read URL hash for tab (#credentials, #preferences, #danger)
  const hash = window.location.hash.replace('#', '');
  if (['profile','credentials','preferences','danger'].includes(hash)) {
    switchTab(hash);
  }

  // Populate all fields from storage
  populateForms();
  updateBadges();
});

// Expose for inline HTML use
window.evalPasswordStrength = evalPasswordStrength;
