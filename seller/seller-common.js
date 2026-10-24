/**
 * seller-common.js — shared helpers for every seller dashboard page.
 * Load after ../auth.js. Exposes window.YV.
 */
(function () {
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));

  async function api(path, options = {}) {
    const opts = { credentials: 'same-origin', ...options };
    if (opts.body && typeof opts.body !== 'string' && !(opts.body instanceof FormData)) {
      opts.headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
      opts.body = JSON.stringify(opts.body);
    }
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    if (res.status === 401) {
      localStorage.removeItem('user');
      window.location.replace('../login.html');
      throw new Error('Please log in again.');
    }
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  }

  const money = (value) => `₱${Number(value || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const parseDate = (value) => (value ? new Date(value) : null);
  const fmtDate = (value, withTime = false) => {
    const d = parseDate(value);
    if (!d || isNaN(d)) return '—';
    const opts = { month: 'short', day: 'numeric', year: 'numeric' };
    if (withTime) Object.assign(opts, { hour: 'numeric', minute: '2-digit' });
    return d.toLocaleString(undefined, opts);
  };
  const timeAgo = (value) => {
    const d = parseDate(value);
    if (!d || isNaN(d)) return '';
    const s = Math.max(0, (Date.now() - d.getTime()) / 1000);
    if (s < 60) return 'just now';
    const units = [[86400 * 30, 'month'], [86400 * 7, 'week'], [86400, 'day'], [3600, 'hour'], [60, 'minute']];
    for (const [size, name] of units) {
      if (s >= size) {
        const n = Math.floor(s / size);
        return `${n} ${name}${n === 1 ? '' : 's'} ago`;
      }
    }
    return 'just now';
  };

  const STATUS_CLASS = { Pending: 'pending', Processing: 'pending', Shipped: 'shipped', Delivered: 'completed', Cancelled: 'cancelled' };
  const statusBadge = (status) => `<span class="status-badge ${STATUS_CLASS[status] || ''}">${esc(status)}</span>`;
  const initials = (f, l) => `${(f || '?')[0] || ''}${(l || '')[0] || ''}`.toUpperCase();
  const avatar = (user, size = 36) => (user && user.profile_image
    ? `<img src="${esc(user.profile_image)}" alt="" style="width:${size}px;height:${size}px;border-radius:50%;object-fit:cover;">`
    : `<span class="initials-avatar" style="width:${size}px;height:${size}px;">${esc(initials(user?.fname, user?.lname))}</span>`);
  const param = (name) => new URLSearchParams(window.location.search).get(name);

  function toast(message, type = 'success') {
    let box = document.getElementById('yv-toasts');
    if (!box) {
      box = document.createElement('div');
      box.id = 'yv-toasts';
      box.className = 'toast-container';
      box.setAttribute('aria-live', 'polite');
      document.body.appendChild(box);
    }
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    const icon = type === 'success' ? 'check-circle' : type === 'warning' ? 'alert-triangle' : 'info';
    el.innerHTML = `<div class="toast-icon"><i data-lucide="${icon}"></i></div><div class="toast-message">${esc(message)}</div>`;
    box.appendChild(el);
    if (window.lucide) lucide.createIcons();
    setTimeout(() => {
      el.style.animation = 'fadeOutToast 0.4s ease forwards';
      setTimeout(() => el.remove(), 400);
    }, 3500);
  }

  const emptyRow = (cols, text) => `<tr><td colspan="${cols}" class="empty-cell">${esc(text)}</td></tr>`;

  // ── Page chrome: header user, notifications badge, logout, settings link ──
  const ready = (window.YVSession || Promise.resolve(null)).then((user) => {
    if (!user || user.role !== 'seller') return user;

    const name = document.querySelector('.dashboard-header .user-info h6');
    const role = document.querySelector('.dashboard-header .user-info p');
    if (name) name.textContent = `${user.fname} ${user.lname}`;
    if (role) role.textContent = `${(user.team_role || 'admin').replace(/^./, (c) => c.toUpperCase())} · Seller`;
    const img = document.querySelector('.dashboard-header .user-avatar');
    if (img) {
      if (user.profile_image) {
        img.src = user.profile_image;
      } else {
        const span = document.createElement('span');
        span.className = 'initials-avatar user-avatar';
        span.textContent = initials(user.fname, user.lname);
        img.replaceWith(span);
      }
    }

    const badge = document.querySelector('.dashboard-header a[href="seller-notifications.html"] .badge');
    if (badge) {
      api('/api/notifications').then(({ unread }) => {
        badge.textContent = unread;
        badge.style.display = unread ? '' : 'none';
      }).catch(() => { badge.style.display = 'none'; });
    }
    return user;
  });

  // The sidebar's Settings entry on some pages was a dead "#" link
  document.querySelectorAll('.sidebar-footer a.nav-item[href="#"]').forEach((a) => {
    a.setAttribute('href', 'seller-settings.html');
  });

  // Logging out also ends the server session
  document.querySelectorAll('a.nav-item[href="../login.html"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      localStorage.removeItem('user');
      fetch('/logout', { method: 'POST', keepalive: true }).finally(() => {
        window.location.href = '../login.html';
      });
    });
  });

  // Header search filters the main table rows on pages that have one
  const search = document.querySelector('.dashboard-header .header-search input');
  if (search) {
    search.addEventListener('input', () => {
      const q = search.value.trim().toLowerCase();
      document.querySelectorAll('.dashboard-content .data-table tbody tr, .dashboard-content [data-searchable]').forEach((row) => {
        if (row.querySelector('.empty-cell')) return;
        row.style.display = !q || row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }

  window.YV = { api, esc, money, fmtDate, timeAgo, statusBadge, initials, avatar, param, toast, emptyRow, ready };
})();
