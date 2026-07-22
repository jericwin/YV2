/**
 * settings.js — Buyer Settings Page Logic
 * All data is persisted in localStorage under the 'yv2_profile' key.
 */

// ── Storage keys ──────────────────────────────────────────────────────────────
const PROFILE_KEY   = 'yv2_profile';
const PREFS_KEY     = 'yv2_prefs';
const CART_KEY      = 'yv2_cart';
const WISHLIST_KEY  = 'yv2_wishlist';

const defaultProfile = {
  firstName: '',
  middleName: '',
  lastName: '',
  extension: '',
  displayName: '',
  phone: '',
  bio: '',
  email: 'guest@youversion2.com',
  password: '',
  addresses: []
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
  return new Promise(async (resolve) => {
    try {
      const ustr = localStorage.getItem('user');
      if (!ustr) return resolve({ ...defaultProfile });
      const u = JSON.parse(ustr);
      if (!u || !u.id) return resolve({ ...defaultProfile });
      
      const res = await fetch(`http://127.0.0.1:5000/api/user/${u.id}`);
      if (res.ok) {
        const data = await res.json();
        const profile = {
          ...defaultProfile,
          firstName: data.fname || '',
          middleName: data.mname || '',
          lastName: data.lname || '',
          extension: data.extension || '',
          email: data.email || '',
          profileImage: data.profile_image || '',
          addresses: data.addresses || [],
          // Bio, phone, etc could be pulled here if they existed in DB
        };
        // update local localStorage user cache to reflect DB
        u.fname = data.fname;
        u.mname = data.mname;
        u.lname = data.lname;
        u.extension = data.extension;
        u.email = data.email;
        u.profile_image = data.profile_image;
        localStorage.setItem('user', JSON.stringify(u));
        resolve(profile);
      } else {
        resolve({ ...defaultProfile });
      }
    } catch {
      resolve({ ...defaultProfile });
    }
  });
}

function saveProfile(data) {
  // We'll leave this as a stub since we haven't created a PUT /api/user endpoint yet.
  showToast('Profile saving is disabled in this demo (No PUT endpoint).', 'warning');
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
  
  const updateAvatar = (containerId, initialSpanId, pImage) => {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (pImage) {
      container.innerHTML = `<img src="http://127.0.0.1:5000${pImage}" style="width: 100%; height: 100%; object-fit: cover;">`;
    } else {
      container.innerHTML = `<span id="${initialSpanId}">${initials.toUpperCase() || '?'}</span>`;
      if (containerId === 'sidebar-avatar') {
        container.innerHTML += `<div class="avatar-edit-badge"><i data-lucide="pen"></i></div>`;
      }
    }
  };
  
  updateAvatar('sidebar-avatar', 'sidebar-initials', profile.profileImage);
  
  // Also update header icon
  const headerBtn = document.getElementById('profile-toggle');
  if (headerBtn) {
    if (profile.profileImage) {
      headerBtn.innerHTML = `<img src="http://127.0.0.1:5000${profile.profileImage}" style="width: 28px; height: 28px; border-radius: 50%; object-fit: cover; border: 1.5px solid var(--primary-color);">`;
    } else {
      headerBtn.innerHTML = `<i data-lucide="user" class="avatar-img" title="Account Settings"></i>`;
      lucide.createIcons();
    }
  }
  
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
async function populateForms() {
  const profile = await loadProfile();
  const prefs   = loadPrefs();

  // Personal Info
  setVal('first-name',   profile.firstName);
  setVal('middle-name',  profile.middleName);
  setVal('last-name',    profile.lastName);
  setVal('extension',    profile.extension);
  setVal('display-name', profile.displayName);
  setVal('phone',        profile.phone);
  setVal('bio',          profile.bio);

  // Addresses
  renderAddresses(profile.addresses);

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

// Address Logic
function renderAddresses(addresses) {
  const container = document.getElementById('address-list-container');
  if (!container) return;
  if (!addresses || addresses.length === 0) {
    container.innerHTML = `<div style="padding: 2rem; text-align: center; color: var(--text-light);">No addresses found. Add one above!</div>`;
    return;
  }
  
  let html = `<div style="display: flex; flex-direction: column; gap: 1rem; padding: 1rem;">`;
  addresses.forEach(addr => {
    html += `
      <div style="border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; display: flex; justify-content: space-between; align-items: flex-start; ${addr.is_default ? 'border-color: var(--primary-color); background: #f0f7ff;' : ''}">
        <div>
          ${addr.is_default ? `<span style="background: var(--primary-color); color: white; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600; margin-bottom: 0.5rem; display: inline-block;">DEFAULT</span>` : ''}
          <div style="font-weight: 500;">${addr.street}, ${addr.barangay}</div>
          <div style="color: var(--text-secondary); font-size: 0.9rem;">${addr.city}, ${addr.province} ${addr.zipcode}</div>
          <div style="color: var(--text-secondary); font-size: 0.9rem;">${addr.country}</div>
          ${!addr.is_default ? `<button class="btn-default-addr" data-id="${addr.id}" style="background:none; border:none; color: var(--primary-color); cursor: pointer; padding: 0.5rem 0; font-size: 0.8rem; font-weight: 600; text-decoration: underline; margin-top: 0.5rem;">Set as Default</button>` : ''}
        </div>
        <button class="btn-delete-addr" data-id="${addr.id}" style="background:none; border:none; color: var(--danger-color); cursor: pointer; padding: 0.5rem;"><i data-lucide="trash-2"></i></button>
      </div>
    `;
  });
  html += `</div>`;
  container.innerHTML = html;
  lucide.createIcons();
  
  // Attach delete handlers
  document.querySelectorAll('.btn-delete-addr').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const id = e.currentTarget.getAttribute('data-id');
      if (confirm("Delete this address?")) {
        const u = JSON.parse(localStorage.getItem('user'));
        try {
          const res = await fetch(`http://127.0.0.1:5000/api/user/${u.id}/address/${id}`, { method: 'DELETE' });
          if (res.ok) {
            showToast('Address deleted', 'success');
            populateForms();
          }
        } catch (e) {
          console.error(e);
        }
      }
    });
  });

  // Attach default handlers
  document.querySelectorAll('.btn-default-addr').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const id = e.currentTarget.getAttribute('data-id');
      const u = JSON.parse(localStorage.getItem('user'));
      try {
        const res = await fetch(`http://127.0.0.1:5000/api/user/${u.id}/address/${id}/default`, { method: 'PUT' });
        if (res.ok) {
          showToast('Default address updated!', 'success');
          populateForms();
        }
      } catch (err) {
        console.error(err);
      }
    });
  });
}

function handleAddressSave() {
  showToast('Use the "Add Address" button instead.', 'info');
}

// Modal handling
function initAddressModal() {
  const modal = document.getElementById('address-modal');
  const btn = document.getElementById('add-address-btn');
  const closeBtn = document.getElementById('close-address-modal');
  const cancelBtn = document.getElementById('cancel-address-btn');
  const form = document.getElementById('new-address-form');
  
  if (!modal || !btn) return;
  
  // --- PSGC Cascading Dropdowns ---
  const regionSelect = document.getElementById('new-region');
  const provinceSelect = document.getElementById('new-province');
  const citySelect = document.getElementById('new-city');
  const barangaySelect = document.getElementById('new-barangay');

  async function fetchOptions(url, selectElement, defaultText) {
    try {
      const response = await fetch(url);
      const data = await response.json();
      data.sort((a, b) => a.name.localeCompare(b.name));
      selectElement.innerHTML = `<option value="">${defaultText}</option>`;
      data.forEach(item => {
        const option = document.createElement('option');
        option.value = item.code;
        option.text = item.name;
        selectElement.add(option);
      });
      selectElement.disabled = false;
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  }

  fetchOptions('https://psgc.gitlab.io/api/regions', regionSelect, 'Select Region');

  regionSelect.addEventListener('change', () => {
    provinceSelect.innerHTML = '<option value="">Select Province</option>';
    provinceSelect.disabled = true; 
    citySelect.innerHTML = '<option value="">Select City</option>';
    citySelect.disabled = true; 
    barangaySelect.innerHTML = '<option value="">Select Barangay</option>';
    barangaySelect.disabled = true; 
    if(regionSelect.value) {
      fetchOptions(`https://psgc.gitlab.io/api/regions/${regionSelect.value}/provinces`, provinceSelect, 'Select Province');
    }
  });

  provinceSelect.addEventListener('change', () => {
    citySelect.innerHTML = '<option value="">Select City</option>';
    citySelect.disabled = true;
    barangaySelect.innerHTML = '<option value="">Select Barangay</option>';
    barangaySelect.disabled = true;
    if(provinceSelect.value) {
      fetchOptions(`https://psgc.gitlab.io/api/provinces/${provinceSelect.value}/cities-municipalities`, citySelect, 'Select City');
    }
  });

  citySelect.addEventListener('change', () => {
    barangaySelect.innerHTML = '<option value="">Select Barangay</option>';
    barangaySelect.disabled = true;
    if(citySelect.value) {
      fetchOptions(`https://psgc.gitlab.io/api/cities-municipalities/${citySelect.value}/barangays`, barangaySelect, 'Select Barangay');
    }
  });
  
  // Helper function for fuzzy matching PSGC dropdowns
  async function fuzzySelect(selectElement, targetString, nextSelectToWait) {
    if (!targetString || !selectElement) return false;
    const target = targetString.toLowerCase().replace(/city of|municipality of/g, '').trim();
    let matched = false;
    for (let i = 0; i < selectElement.options.length; i++) {
      const optionText = selectElement.options[i].text.toLowerCase();
      if (optionText.includes(target) || target.includes(optionText) || 
          (target.length > 4 && (optionText.startsWith(target) || target.startsWith(optionText)))) {
        selectElement.selectedIndex = i;
        matched = true;
        break;
      }
    }
    if (matched) {
      selectElement.dispatchEvent(new Event('change'));
      if (nextSelectToWait) {
        let attempts = 0;
        await new Promise(resolve => {
          const interval = setInterval(() => {
            attempts++;
            if (nextSelectToWait.options.length > 1 || attempts > 30) {
              clearInterval(interval);
              resolve();
            }
          }, 100);
        });
      }
      return true;
    }
    return false;
  }

  const useLocationBtn = document.getElementById('use-location-btn');
  if (useLocationBtn) {
    useLocationBtn.addEventListener('click', () => {
      if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser.');
        return;
      }
      const originalText = useLocationBtn.innerHTML;
      useLocationBtn.innerHTML = 'Locating...';
      navigator.geolocation.getCurrentPosition(async (position) => {
        try {
          const { latitude, longitude } = position.coords;
          const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`);
          const data = await res.json();
          if (data && data.address) {
            const { road, postcode, city, town, municipality, state, region, village, suburb } = data.address;
            if (road) document.getElementById('new-street').value = road;
            if (postcode) document.getElementById('new-zipcode').value = postcode;
            const nomRegion = region || '';
            const nomProvince = state || '';
            const nomCity = city || town || municipality || '';
            const nomBarangay = village || suburb || '';
            const regionSuccess = await fuzzySelect(regionSelect, nomRegion, provinceSelect);
            if (regionSuccess) {
              const provSuccess = await fuzzySelect(provinceSelect, nomProvince, citySelect);
              if (provSuccess) {
                const citySuccess = await fuzzySelect(citySelect, nomCity, barangaySelect);
                if (citySuccess) {
                  await fuzzySelect(barangaySelect, nomBarangay, null);
                }
              }
            }
          }
        } catch (error) {
          console.error(error);
          alert('Failed to retrieve address from GPS.');
        } finally {
          useLocationBtn.innerHTML = originalText;
          lucide.createIcons();
        }
      }, () => {
        alert('Unable to retrieve your location. Please make sure location permissions are allowed in your browser.');
        useLocationBtn.innerHTML = originalText;
        lucide.createIcons();
      });
    });
  }

  btn.addEventListener('click', () => modal.style.display = 'flex');
  const close = () => { modal.style.display = 'none'; form.reset(); };
  closeBtn.addEventListener('click', close);
  cancelBtn.addEventListener('click', close);
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const ustr = localStorage.getItem('user');
    if (!ustr) return alert("Not logged in");
    const u = JSON.parse(ustr);
    
    const region = regionSelect.options[regionSelect.selectedIndex]?.text || '';
    const province = provinceSelect.options[provinceSelect.selectedIndex]?.text || '';
    const city = citySelect.options[citySelect.selectedIndex]?.text || '';
    const barangay = barangaySelect.options[barangaySelect.selectedIndex]?.text || '';
    
    let fullStreet = document.getElementById('new-street').value.trim();
    const houseNo = document.getElementById('new-house-number').value.trim();
    if(houseNo) fullStreet = houseNo + ' ' + fullStreet;
    
    const payload = {
      street: fullStreet,
      barangay: barangay,
      city: city,
      province: province,
      zipcode: document.getElementById('new-zipcode').value,
      is_default: document.getElementById('new-is-default').checked ? 1 : 0
    };
    
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/user/${u.id}/address`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        showToast('Address added successfully!', 'success');
        close();
        populateForms();
      } else {
        const err = await res.json();
        alert(err.error);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to add address');
    }
  });
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

  initAddressModal();

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

  // Avatar upload
  const sidebarAvatar = document.getElementById('sidebar-avatar');
  const avatarUpload = document.getElementById('avatar-upload');
  
  if (sidebarAvatar && avatarUpload) {
    sidebarAvatar.addEventListener('click', () => {
      avatarUpload.click();
    });
    
    avatarUpload.addEventListener('change', async (e) => {
      if (!e.target.files || e.target.files.length === 0) return;
      const file = e.target.files[0];
      
      const u = JSON.parse(localStorage.getItem('user'));
      if (!u) return alert("Not logged in");
      
      const formData = new FormData();
      formData.append('avatar', file);
      
      try {
        const res = await fetch(`http://127.0.0.1:5000/api/user/${u.id}/avatar`, {
          method: 'POST',
          body: formData
        });
        
        if (res.ok) {
          showToast('Profile photo updated!', 'success');
          populateForms(); // re-fetch and render
        } else {
          const err = await res.json();
          alert(err.error || 'Upload failed');
        }
      } catch (err) {
        console.error(err);
        alert('Failed to connect to server.');
      }
    });
  }

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
