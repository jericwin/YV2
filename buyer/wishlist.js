/**
 * wishlist.js — Buyer Wishlist Page Logic
 * Reads from localStorage (yv2_wishlist) and renders saved books.
 * Piggybacks on the shared `books` array and AppState from index.js.
 */

// ── Helpers ──────────────────────────────────────────────────────────────────

function loadWishlist() {
  try {
    const stored = localStorage.getItem('yv2_wishlist');
    return stored ? new Set(JSON.parse(stored)) : new Set();
  } catch { return new Set(); }
}

function saveWishlist(set) {
  localStorage.setItem('yv2_wishlist', JSON.stringify(Array.from(set)));
}

function loadCart() {
  try {
    const stored = localStorage.getItem('yv2_cart');
    return stored ? JSON.parse(stored) : [];
  } catch { return []; }
}

function saveCart(cart) {
  localStorage.setItem('yv2_cart', JSON.stringify(cart));
}

function addToCart(bookId) {
  const cart = loadCart();
  const existing = cart.find(i => i.bookId === bookId);
  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({ bookId, quantity: 1 });
  }
  saveCart(cart);
  updateCartBadge();
}

// ── Badge Updates ─────────────────────────────────────────────────────────────

function updateBadges() {
  const wishlist = loadWishlist();
  const cart = loadCart();
  const totalQty = cart.reduce((s, i) => s + i.quantity, 0);

  const wb = document.getElementById('wishlist-badge');
  const cb = document.getElementById('cart-badge');
  if (wb) wb.innerText = wishlist.size;
  if (cb) cb.innerText = totalQty;
}

function updateCartBadge() {
  const cart = loadCart();
  const totalQty = cart.reduce((s, i) => s + i.quantity, 0);
  const cb = document.getElementById('cart-badge');
  if (cb) cb.innerText = totalQty;
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const iconMap = { success: 'check-circle', info: 'info', warning: 'alert-triangle', error: 'x-circle' };
  const colorMap = { success: '#1565C0', info: '#0ea5e9', warning: '#f59e0b', error: '#ef4444' };

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.cssText = `
    display:flex; align-items:center; gap:0.75rem;
    background:#fff; border:1.5px solid ${colorMap[type]};
    border-radius:12px; padding:0.85rem 1.1rem;
    box-shadow:0 8px 24px rgba(0,0,0,0.12); min-width:260px; max-width:360px;
    animation:fadeInToast 0.35s cubic-bezier(0.34,1.56,0.64,1) forwards;
  `;
  toast.innerHTML = `
    <span style="color:${colorMap[type]};display:flex;flex-shrink:0"><i data-lucide="${iconMap[type]}"></i></span>
    <span style="font-size:0.88rem;font-weight:500;color:#1F2937;flex:1">${message}</span>
  `;
  container.appendChild(toast);
  lucide.createIcons();

  setTimeout(() => {
    toast.style.animation = 'fadeOutToast 0.4s cubic-bezier(0.4,0,1,1) forwards';
    setTimeout(() => toast.remove(), 400);
  }, 3500);
}

// ── Sort helper ───────────────────────────────────────────────────────────────

function getSortedBooks(wishlistIds, sortVal) {
  const wishlistBooks = books.filter(b => wishlistIds.has(b.id));
  switch (sortVal) {
    case 'price-asc':  return wishlistBooks.sort((a, b) => a.price - b.price);
    case 'price-desc': return wishlistBooks.sort((a, b) => b.price - a.price);
    case 'rating':     return wishlistBooks.sort((a, b) => b.rating - a.rating);
    default:           return wishlistBooks; // "added" = Set insertion order
  }
}

// ── Render ────────────────────────────────────────────────────────────────────

function renderWishlist() {
  const wishlist = loadWishlist();
  const grid     = document.getElementById('wishlist-grid');
  const empty    = document.getElementById('wishlist-empty');
  const toolbar  = document.getElementById('wishlist-toolbar');
  const heroBadge = document.getElementById('hero-count-badge');
  const sortVal  = document.getElementById('wishlist-sort')?.value ?? 'added';

  if (heroBadge) heroBadge.innerText = `${wishlist.size} saved book${wishlist.size !== 1 ? 's' : ''}`;
  updateBadges();

  if (wishlist.size === 0) {
    grid.innerHTML = '';
    grid.classList.add('hidden');
    toolbar.classList.add('hidden');
    empty.classList.remove('hidden');
    return;
  }

  toolbar.classList.remove('hidden');
  empty.classList.add('hidden');
  grid.classList.remove('hidden');

  const sorted = getSortedBooks(wishlist, sortVal);
  grid.innerHTML = '';

  sorted.forEach(book => {
    const card = document.createElement('div');
    card.className = 'wishlist-card';
    card.innerHTML = `
      <div class="wishlist-card-img-wrap" onclick="openBookDetail(${book.id})">
        <img src="../${book.cover}" alt="${book.title}" loading="lazy">
        <button class="wishlist-remove-btn" onclick="event.stopPropagation(); removeFromWishlist(${book.id})" title="Remove from Wishlist">
          <i data-lucide="heart-off"></i>
        </button>
        <span class="wishlist-card-tag">${book.genre}</span>
      </div>
      <div class="wishlist-card-body">
        <span class="wishlist-card-author">${book.author}</span>
        <h4 class="wishlist-card-title" onclick="openBookDetail(${book.id})">${book.title}</h4>
        <div class="wishlist-card-rating">
          <i data-lucide="star"></i>
          <span>${book.rating.toFixed(2)} (${book.reviewsCount} reviews)</span>
        </div>
        <div class="wishlist-card-footer">
          <div class="wishlist-card-price-group">
            <span class="wishlist-card-price">₱${book.price.toFixed(2)}</span>
            <span class="wishlist-card-old-price">₱${book.originalPrice.toFixed(2)}</span>
          </div>
          <button class="wishlist-add-cart-btn" onclick="handleAddToCart(${book.id})">
            <i data-lucide="shopping-bag"></i> Add
          </button>
        </div>
      </div>
    `;
    grid.appendChild(card);
  });

  lucide.createIcons();
}

// ── Actions ───────────────────────────────────────────────────────────────────

function removeFromWishlist(bookId) {
  const wishlist = loadWishlist();
  const book = books.find(b => b.id === bookId);
  wishlist.delete(bookId);
  saveWishlist(wishlist);
  showToast(`Removed "${book?.title ?? 'book'}" from wishlist.`, 'info');
  renderWishlist();
}

function handleAddToCart(bookId) {
  const book = books.find(b => b.id === bookId);
  addToCart(bookId);
  showToast(`"${book?.title ?? 'Book'}" added to cart!`, 'success');
}

function clearAllWishlist() {
  if (loadWishlist().size === 0) return;
  saveWishlist(new Set());
  showToast('Wishlist cleared.', 'info');
  renderWishlist();
}

function openBookDetail(bookId) {
  // Navigate back to the shop with the book modal trigger via query param
  window.location.href = `index.html?book=${bookId}`;
}

// ── Init ──────────────────────────────────────────────────────────────────────

window.addEventListener('DOMContentLoaded', () => {
  // Mobile drawer
  const mobileMenuTrigger = document.getElementById('mobile-menu-trigger');
  const closeMobileDrawer = document.getElementById('close-mobile-drawer');
  const mobileDrawer      = document.getElementById('mobile-drawer');
  if (mobileMenuTrigger) mobileMenuTrigger.addEventListener('click', () => mobileDrawer.classList.remove('hidden'));
  if (closeMobileDrawer) closeMobileDrawer.addEventListener('click', () => mobileDrawer.classList.add('hidden'));

  // Sort
  const sortSelect = document.getElementById('wishlist-sort');
  if (sortSelect) sortSelect.addEventListener('change', renderWishlist);

  // Clear all
  const clearBtn = document.getElementById('clear-all-btn');
  if (clearBtn) clearBtn.addEventListener('click', clearAllWishlist);

  // Initial render
  renderWishlist();
});
