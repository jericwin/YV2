/**
 * auth.js — keeps the browser's saved user (localStorage "user") in sync with the server session.
 * Buyer and seller pages require a session; seller pages also require the seller role.
 * window.YVSession resolves to the logged-in user (or null).
 */
(function () {
  const path = window.location.pathname;
  const inBuyer = /\/buyer\//.test(path);
  const inSeller = /\/seller\//.test(path);
  const prefix = inBuyer || inSeller ? '../' : '';

  window.YVSession = fetch('/api/me', { cache: 'no-store', credentials: 'same-origin' })
    .then((res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(({ user }) => {
      if (user) {
        let saved = {};
        try { saved = JSON.parse(localStorage.getItem('user')) || {}; } catch (e) { /* ignore */ }
        localStorage.setItem('user', JSON.stringify({ ...saved, ...user }));
      } else {
        localStorage.removeItem('user');
      }

      if ((inBuyer || inSeller) && !user) {
        window.location.replace(`${prefix}login.html`);
      } else if (inSeller && user.role !== 'seller') {
        window.location.replace(`${prefix}buyer/index.html`);
      }
      return user;
    })
    // No API (e.g. static preview): leave the page as it is
    .catch(() => null);
})();
