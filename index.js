// BOOK DATABASE (MOCK DATA)
const books = [
  {
    id: 1,
    title: "You Version 2: Creating a Better Life with the Six Phases of Software Development (Hardcover)",
    author: "Ollie G. Baldemor",
    genre: "Print",
    price: 200.00,
    originalPrice: 250.00,
    rating: 5.0,
    reviewsCount: 242,
    cover: "assets/cover.jpg",
    pages: 280,
    publisher: "Ollie G. Baldemor Publishing (2026)",
    isbn: "978-971-9872-01-3",
    description: "Why do we constantly update our phone apps, computer operational systems, and databases, yet leave our personal habits running on legacy code? Ollie G. Baldemor introduces an inspiring personal development roadmap, showing how you can debug your mind and design a balanced, successful life using the six core phases of software development.",
    sampleText: "Introduction: System Version 2.0\n\nTake a look at your phone. Right now, there are probably several apps waiting in the download queue, preparing to receive their latest version updates. Developers spent hundreds of hours tracking logs, writing tests, and deploying code to make those systems faster, more secure, and more stable.\n\nNow, ask yourself: when was the last time you ran a system update on your own life? Are you still running on legacy software from your childhood or early career? Are your physical habits, financial tracking, or relationship modules crashing on a weekly basis?\n\nYou Version 2 is a systematic guide to debugging your life, using the exact same six phases that engineers use to build the world's most robust software.",
    reviews: [
      { user: "Robert J.", rating: 5, comment: "An absolutely brilliant concept! The comparison between debugging code and refining habits is spot on." },
      { user: "Maria C.", rating: 5, comment: "I work in tech and this is by far the most logical, actionable self-help book I have ever read." },
      { user: "Kevin A.", rating: 5, comment: "Love the 5Fs concept. It gave me a clear framework to see where my life was out of balance." }
    ]
  }
];

// STATE MANAGEMENT
class AppState {
  constructor() {
    this.cart = this.loadCartFromStorage();
    this.wishlist = this.loadWishlistFromStorage();

    this.promoApplied = false;
    this.currentTestimonialIndex = 0;
  }

  loadCartFromStorage() {
    try {
      const stored = localStorage.getItem('yv2_cart');
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      return [];
    }
  }

  saveCartToStorage() {
    localStorage.setItem('yv2_cart', JSON.stringify(this.cart));
  }

  loadWishlistFromStorage() {
    try {
      const stored = localStorage.getItem('yv2_wishlist');
      return stored ? new Set(JSON.parse(stored)) : new Set();
    } catch (e) {
      return new Set();
    }
  }

  saveWishlistToStorage() {
    localStorage.setItem('yv2_wishlist', JSON.stringify(Array.from(this.wishlist)));
  }
}

const state = new AppState();

// UI CONTROL & RENDERING CLASS
class BookstoreUI {
  constructor() {
    this.initDOMRefs();
    this.initEventListeners();
    this.render();
  }

  initDOMRefs() {
    // Nav & Search

    this.mobileDrawer = document.getElementById('mobile-drawer');
    this.mobileMenuTrigger = document.getElementById('mobile-menu-trigger');
    this.closeMobileDrawer = document.getElementById('close-mobile-drawer');

    // Badges
    this.cartBadge = document.getElementById('cart-badge');
    this.wishlistBadge = document.getElementById('wishlist-badge');

    // Cart Drawer
    this.cartDrawer = document.getElementById('cart-drawer');
    this.cartOverlay = document.getElementById('cart-overlay');
    this.cartToggleBtn = document.getElementById('cart-toggle-btn');
    this.closeCartBtn = document.getElementById('close-cart-btn');
    this.cartItemsContainer = document.getElementById('cart-items-container');
    this.cartEmptyState = document.getElementById('cart-empty-state');
    this.cartSummaryFooter = document.getElementById('cart-summary-footer');
    this.cartSubtotal = document.getElementById('cart-subtotal');
    this.cartDiscount = document.getElementById('cart-discount');
    this.cartShipping = document.getElementById('cart-shipping');
    this.cartTotal = document.getElementById('cart-total');
    this.discountRow = document.getElementById('discount-row');
    this.promoInput = document.getElementById('promo-input');
    this.applyPromoBtn = document.getElementById('apply-promo-btn');
    this.promoAppliedMsg = document.getElementById('promo-applied-msg');
    this.checkoutTriggerBtn = document.getElementById('checkout-trigger-btn');
    this.cartCountTitle = document.getElementById('cart-count-title');

    // Detail Modal
    this.detailModalOverlay = document.getElementById('detail-modal-overlay');
    this.detailModal = document.getElementById('detail-modal');
    this.closeDetailModal = document.getElementById('close-detail-modal');
    this.modalBookImg = document.getElementById('modal-book-img');
    this.modalBookGenre = document.getElementById('modal-book-genre');
    this.modalTitle = document.getElementById('modal-book-title');
    this.modalAuthor = document.getElementById('modal-book-author');
    this.modalPrice = document.getElementById('modal-price');
    this.modalOldPrice = document.getElementById('modal-old-price');
    this.modalDesc = document.getElementById('modal-book-desc');
    this.modalSpecPages = document.getElementById('modal-spec-pages');
    this.modalSpecPublisher = document.getElementById('modal-spec-publisher');
    this.modalSpecIsbn = document.getElementById('modal-spec-isbn');
    this.modalQtyInput = document.getElementById('modal-qty-input');
    this.modalQtyMinus = document.getElementById('modal-qty-minus');
    this.modalQtyPlus = document.getElementById('modal-qty-plus');
    this.modalAddToCartBtn = document.getElementById('modal-add-to-cart-btn');
    this.modalChatBtn = document.getElementById('modal-chat-btn');
    this.modalWishlistBtn = document.getElementById('modal-wishlist-btn');
    this.modalTabs = document.querySelectorAll('.tab-btn');

    // Checkout Wizard Modal
    this.checkoutModalOverlay = document.getElementById('checkout-modal-overlay');
    this.closeCheckoutModal = document.getElementById('close-checkout-modal');
    this.checkoutFormWizard = document.getElementById('checkout-wizard-form');
    this.checkoutSummaryList = document.getElementById('checkout-summary-list');
    this.checkoutSubtotal = document.getElementById('checkout-subtotal');
    this.checkoutDiscount = document.getElementById('checkout-discount');
    this.checkoutDiscountRow = document.getElementById('checkout-discount-row');
    this.checkoutShipping = document.getElementById('checkout-shipping');
    this.checkoutTotalPrice = document.getElementById('checkout-total-price');

    // Checkout steps & wizard buttons
    this.shippingNextBtn = document.getElementById('shipping-next-btn');
    this.paymentBackBtn = document.getElementById('payment-back-btn');
    this.paymentSubmitBtn = document.getElementById('payment-submit-btn');
    this.cancelCheckoutBtn = document.getElementById('cancel-checkout-btn');
    this.successCloseBtn = document.getElementById('success-close-btn');



    // Shop Grid
    this.bookGrid = document.getElementById('book-grid');
    this.emptyState = document.getElementById('empty-state');

    // Testimonials Carousel
    this.prevTestimonial = document.getElementById('prev-testimonial');
    this.nextTestimonial = document.getElementById('next-testimonial');
    this.testimonialSlides = document.querySelectorAll('.testimonial-slide');
    this.carouselDots = document.querySelectorAll('.carousel-dots .dot');

    // Wishlist Toggle badge trigger
    this.wishlistToggleBtn = document.getElementById('wishlist-toggle-btn');

    // Newsletter & Featured Book Triggers
    this.newsletterForm = document.getElementById('newsletter-form');
    this.newsletterSuccess = document.getElementById('newsletter-success');
    this.heroBookTrigger = document.getElementById('hero-book-trigger');
    this.heroFeaturedBtn = document.getElementById('hero-featured-btn');
  }

  initEventListeners() {
    // Mobile Navigation Drawer Toggle
    this.mobileMenuTrigger?.addEventListener('click', () => this.mobileDrawer.classList.remove('hidden'));
    this.closeMobileDrawer?.addEventListener('click', () => this.mobileDrawer.classList.add('hidden'));

    // Cart Drawer Toggle
    this.cartToggleBtn?.addEventListener('click', () => this.toggleCartDrawer(true));
    this.closeCartBtn?.addEventListener('click', () => this.toggleCartDrawer(false));
    this.cartOverlay?.addEventListener('click', () => this.toggleCartDrawer(false));

    // Cart Promo Apply
    this.applyPromoBtn?.addEventListener('click', () => this.handlePromoApply());

    // Cart checkout trigger
    this.checkoutTriggerBtn?.addEventListener('click', () => this.openCheckoutWizard());

    // Detail Modal actions
    this.closeDetailModal?.addEventListener('click', () => this.toggleDetailModal(false));
    this.detailModalOverlay?.addEventListener('click', (e) => {
      if (e.target === this.detailModalOverlay) this.toggleDetailModal(false);
    });

    // Detail Modal Qty adjustment
    this.modalQtyMinus?.addEventListener('click', () => {
      let qty = parseInt(this.modalQtyInput.value);
      if (qty > 1) this.modalQtyInput.value = qty - 1;
    });
    this.modalQtyPlus?.addEventListener('click', () => {
      let qty = parseInt(this.modalQtyInput.value);
      if (qty < 10) this.modalQtyInput.value = qty + 1;
    });

    // Modal Tabs trigger
    if (this.modalTabs) {
      this.modalTabs.forEach(tab => {
        tab.addEventListener('click', (e) => this.handleModalTabClick(e.target));
      });
    }

    // Checkout modal actions
    this.closeCheckoutModal?.addEventListener('click', () => this.toggleCheckoutWizard(false));
    this.cancelCheckoutBtn?.addEventListener('click', () => this.toggleCheckoutWizard(false));
    this.checkoutModalOverlay?.addEventListener('click', (e) => {
      if (e.target === this.checkoutModalOverlay) this.toggleCheckoutWizard(false);
    });

    // Checkout Wizard Flow buttons
    this.shippingNextBtn?.addEventListener('click', () => this.validateAndAdvanceStep(1));
    this.paymentBackBtn?.addEventListener('click', () => this.changeStep(2, 1));
    this.paymentSubmitBtn?.addEventListener('click', () => this.processCheckoutPayment());
    this.successCloseBtn?.addEventListener('click', () => {
      this.toggleCheckoutWizard(false);
      this.scrollToSection('shop-section');
    });

    // Testimonials Carousel Actions
    this.prevTestimonial?.addEventListener('click', () => this.shiftTestimonial(-1));
    this.nextTestimonial?.addEventListener('click', () => this.shiftTestimonial(1));
    if (this.carouselDots) {
      this.carouselDots.forEach(dot => {
        dot.addEventListener('click', (e) => {
          const slideIndex = parseInt(e.target.getAttribute('data-slide'));
          this.setTestimonialIndex(slideIndex);
        });
      });
    }

    // Wishlist Toggle Header click
    this.wishlistToggleBtn?.addEventListener('click', () => {
      window.location.href = "login.html"; 
    });
    
    // Hero Book click triggers detail preview
    this.heroBookTrigger?.addEventListener('click', () => this.openDetailModal(1));
    this.heroFeaturedBtn?.addEventListener('click', (e) => {
      e.preventDefault();
      this.openDetailModal(1);
    });

    // Newsletter Submission
    this.newsletterForm?.addEventListener('submit', (e) => {
      e.preventDefault();
      const emailInput = document.getElementById('newsletter-email');
      if (emailInput && emailInput.value.trim().length > 0) {
        this.newsletterForm.classList.add('hidden');
        this.newsletterSuccess.classList.remove('hidden');
        this.createToast("Successfully subscribed to newsletter! Checked inbox for code.", "success");
      }
    });
  }

  // STATE-DRIVEN RENDER FUNCTION
  render() {
    this.updateBadges();
    this.renderBooksGrid();
    this.renderCartDrawer();
  }

  // HEADER BADGE UPDATES
  updateBadges() {
    const totalCartCount = state.cart.reduce((sum, item) => sum + item.quantity, 0);
    this.cartBadge.innerText = totalCartCount;
    this.wishlistBadge.innerText = state.wishlist.size;
  }

  // DYNAMIC BOOK GRID GENERATOR
  renderBooksGrid() {
    this.bookGrid.innerHTML = '';

    if (books.length === 0) {
      this.emptyState.classList.remove('hidden');
      this.bookGrid.classList.add('hidden');
      return;
    } else {
      this.emptyState.classList.add('hidden');
      this.bookGrid.classList.remove('hidden');
    }

    books.forEach(book => {
      const isWishlisted = state.wishlist.has(book.id);
      
      const card = document.createElement('div');
      card.className = 'book-card';
      card.innerHTML = `
        <div class="book-card-header">
          <div class="card-img-wrapper" onclick="app.openDetailModal(${book.id})">
            <img src="${book.cover}" alt="${book.title}" loading="lazy">
          </div>
          <div class="card-actions-overlay">
            <button class="overlay-action-btn ${isWishlisted ? 'wishlisted' : ''}" onclick="app.toggleWishlist(${book.id})" title="Add to Wishlist">
              <i data-lucide="heart"></i>
            </button>
          </div>
          <span class="card-tag">${book.genre}</span>
        </div>
        <div class="book-card-body">
          <span class="card-author">${book.author}</span>
          <h4 class="card-title" onclick="app.openDetailModal(${book.id})">${book.title}</h4>
          
          <div class="card-rating">
            <i data-lucide="star" style="fill:#FBC02D; color:#FBC02D;"></i>
            <span>${book.rating.toFixed(2)}</span>
          </div>

          <div class="card-footer-row">
            <div class="card-price-group">
              <span class="price">₱${book.price.toFixed(2)}</span>
              <span class="old-price">₱${book.originalPrice.toFixed(2)}</span>
            </div>
            <button class="card-add-btn" onclick="app.addToCart(${book.id})" title="Add to Shopping Cart">
              <i data-lucide="plus"></i>
            </button>
          </div>
        </div>
      `;
      this.bookGrid.appendChild(card);
    });

    lucide.createIcons();
  }

  // SIDE DRAWER - CART RENDER
  renderCartDrawer() {
    this.cartItemsContainer.innerHTML = '';

    if (state.cart.length === 0) {
      this.cartEmptyState.classList.remove('hidden');
      this.cartSummaryFooter.classList.add('hidden');
      this.cartCountTitle.innerText = "0";
      return;
    }

    this.cartEmptyState.classList.add('hidden');
    this.cartSummaryFooter.classList.remove('hidden');

    let subtotal = 0;
    let itemCount = 0;

    state.cart.forEach(cartItem => {
      const book = books.find(b => b.id === cartItem.bookId);
      if (!book) return;

      const itemCost = book.price * cartItem.quantity;
      subtotal += itemCost;
      itemCount += cartItem.quantity;

      const itemRow = document.createElement('div');
      itemRow.className = 'cart-item';
      itemRow.innerHTML = `
        <img src="${book.cover}" alt="" class="cart-item-img">
        <div class="cart-item-details">
          <h5 class="cart-item-title">${book.title}</h5>
          <p class="cart-item-author">By ${book.author}</p>
          <div class="cart-item-controls">
            <div class="cart-item-qty">
              <button onclick="app.updateCartQty(${book.id}, ${cartItem.quantity - 1})"><i data-lucide="minus"></i></button>
              <input type="text" value="${cartItem.quantity}" readonly>
              <button onclick="app.updateCartQty(${book.id}, ${cartItem.quantity + 1})"><i data-lucide="plus"></i></button>
            </div>
            <span class="cart-item-price">₱${itemCost.toFixed(2)}</span>
          </div>
        </div>
        <button class="cart-item-remove-btn" onclick="app.removeFromCart(${book.id})" title="Remove item">
          <i data-lucide="trash-2"></i>
        </button>
      `;
      this.cartItemsContainer.appendChild(itemRow);
    });

    this.cartCountTitle.innerText = itemCount;

    // Pricing calculation
    let discount = 0;
    if (state.promoApplied) {
      discount = subtotal * 0.15;
      this.discountRow.classList.remove('hidden');
      this.cartDiscount.innerText = `-₱${discount.toFixed(2)}`;
    } else {
      this.discountRow.classList.add('hidden');
    }

    // Shipping is free on orders above $35
    const shippingFee = (subtotal - discount) >= 35 ? 0.00 : 4.99;
    this.cartShipping.innerText = shippingFee === 0 ? 'FREE' : `₱${shippingFee.toFixed(2)}`;

    const totalVal = subtotal - discount + shippingFee;
    this.cartSubtotal.innerText = `₱${subtotal.toFixed(2)}`;
    this.cartTotal.innerText = `₱${totalVal.toFixed(2)}`;

    lucide.createIcons();
  }

  toggleCartDrawer(open) {
    if (open) {
      this.cartDrawer.classList.remove('hidden');
      this.cartOverlay.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
    } else {
      this.cartDrawer.classList.add('hidden');
      this.cartOverlay.classList.add('hidden');
      document.body.style.overflow = '';
    }
  }

  // CART LOGIC WRAPPERS
  addToCart(bookId, qty = 1) {
    const existing = state.cart.find(item => item.bookId === bookId);
    const book = books.find(b => b.id === bookId);

    if (existing) {
      if (existing.quantity + qty > 10) {
        this.createToast("Maximum of 10 copies per title limit reached.", "warning");
        return;
      }
      existing.quantity += qty;
    } else {
      state.cart.push({ bookId, quantity: qty });
    }

    state.saveCartToStorage();
    this.render();
    this.createToast(`Added "${book.title}" to shopping cart!`, "success");
  }

  updateCartQty(bookId, newQty) {
    if (newQty < 1) {
      this.removeFromCart(bookId);
      return;
    }
    if (newQty > 10) {
      this.createToast("Maximum of 10 copies per title limit reached.", "warning");
      return;
    }
    const item = state.cart.find(item => item.bookId === bookId);
    if (item) {
      item.quantity = newQty;
      state.saveCartToStorage();
      this.render();
    }
  }

  removeFromCart(bookId) {
    const book = books.find(b => b.id === bookId);
    state.cart = state.cart.filter(item => item.bookId !== bookId);
    state.saveCartToStorage();
    this.render();
    this.createToast(`Removed "${book.title}" from shopping cart.`, "info");
  }

  handlePromoApply() {
    const code = this.promoInput.value.trim().toUpperCase();
    if (code === 'READ15') {
      state.promoApplied = true;
      this.promoAppliedMsg.innerText = "Coupon code READ15 applied! 15% discount active.";
      this.promoAppliedMsg.className = "promo-msg success";
      this.promoAppliedMsg.classList.remove('hidden');
      this.createToast("Promo code applied successfully!", "success");
      this.renderCartDrawer();
    } else {
      this.createToast("Invalid coupon code.", "warning");
    }
  }

  // WISHLIST TOGGLE LOGIC
  toggleWishlist(bookId) {
    const book = books.find(b => b.id === bookId);
    if (state.wishlist.has(bookId)) {
      state.wishlist.delete(bookId);
      this.createToast(`Removed "${book.title}" from Wishlist.`, "info");
    } else {
      state.wishlist.add(bookId);
      this.createToast(`Bookmarked "${book.title}" to Wishlist!`, "success");
    }
    state.saveWishlistToStorage();
    this.updateBadges();
    this.renderBooksGrid();
  }

  showWishlistNotification() {
    if (state.wishlist.size === 0) {
      this.createToast("Your wishlist is currently empty.", "info");
      return;
    }
    const titles = [];
    state.wishlist.forEach(id => {
      const book = books.find(b => b.id === id);
      if (book) titles.push(book.title);
    });
    this.createToast(`Wishlist Books: ${titles.join(', ')}`, "success");
  }

  // BOOK DETAILS MODAL TRIGGERS
  openDetailModal(bookId) {
    const book = books.find(b => b.id === bookId);
    if (!book) return;

    // Load elements
    this.modalBookImg.src = book.cover;
    this.modalBookImg.alt = book.title;
    this.modalBookGenre.innerText = book.genre;
    this.modalTitle.innerText = book.title;
    this.modalAuthor.innerText = `By ${book.author}`;
    this.modalDesc.innerText = book.description;
    this.modalSpecPages.innerHTML = `<i data-lucide="file-text"></i> ${book.pages} Pages`;
    this.modalSpecPublisher.innerHTML = `<i data-lucide="printer"></i> ${book.publisher}`;
    this.modalSpecIsbn.innerHTML = `<i data-lucide="hash"></i> ISBN: ${book.isbn}`;

    this.modalPrice.innerText = `₱${book.price.toFixed(2)}`;
    
    if (book.originalPrice) {
      this.modalOldPrice.innerText = `₱${book.originalPrice.toFixed(2)}`;
      this.modalOldPrice.style.display = 'inline-block';
    } else {
      this.modalOldPrice.style.display = 'none';
    }

    // Reset tabs to tab 1
    this.modalTabs.forEach(t => t.classList.remove('active'));
    this.modalTabs[0].classList.add('active');
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('tab-description').classList.add('active');

    // Reset qty selector
    this.modalQtyInput.value = 1;

    // Assign dynamic add button actions
    this.modalAddToCartBtn.onclick = () => {
      const quantity = parseInt(this.modalQtyInput.value);
      this.addToCart(book.id, quantity);
      this.toggleDetailModal(false);
    };

    // Assign wishlist bookmark trigger
    const wishlisted = state.wishlist.has(book.id);
    this.modalWishlistBtn.className = `btn btn-outline icon-only-btn ${wishlisted ? 'wishlisted' : ''}`;
    this.modalWishlistBtn.onclick = () => {
      this.toggleWishlist(book.id);
      const isWishlisted = state.wishlist.has(book.id);
      this.modalWishlistBtn.className = `btn btn-outline icon-only-btn ${isWishlisted ? 'wishlisted' : ''}`;
    };

    if (this.modalChatBtn) {
      this.modalChatBtn.onclick = () => {
        const sellerId = book.seller_id || 1;
        window.location.href = `chat.html?seller_id=${sellerId}`;
      };
    }

    this.toggleDetailModal(true);
    lucide.createIcons();
  }

  toggleDetailModal(open) {
    if (open) {
      this.detailModalOverlay.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
    } else {
      this.detailModalOverlay.classList.add('hidden');
      document.body.style.overflow = '';
    }
  }

  handleModalTabClick(clickedTab) {
    this.modalTabs.forEach(t => t.classList.remove('active'));
    clickedTab.classList.add('active');

    const targetTabId = clickedTab.getAttribute('data-tab');
    document.querySelectorAll('.tab-content').forEach(content => {
      content.classList.remove('active');
    });
    document.getElementById(targetTabId).classList.add('active');
    lucide.createIcons();
  }

  // CHECKOUT MODAL FLOW WIZARD
  openCheckoutWizard() {
    if (state.cart.length === 0) {
      this.createToast("Shopping cart is empty.", "warning");
      return;
    }
    
    // Close cart drawer
    this.toggleCartDrawer(false);

    // Populate checkout panel details
    this.checkoutSummaryList.innerHTML = '';
    let subtotal = 0;
    
    state.cart.forEach(cartItem => {
      const book = books.find(b => b.id === cartItem.bookId);
      if (!book) return;
      
      const rowPrice = book.price * cartItem.quantity;
      subtotal += rowPrice;

      const element = document.createElement('div');
      element.className = 'checkout-summary-item';
      element.innerHTML = `
        <img src="${book.cover}" alt="">
        <div class="checkout-summary-item-info">
          <h6>${book.title}</h6>
          <p>Qty: ${cartItem.quantity}</p>
        </div>
        <span class="checkout-summary-item-price">₱${rowPrice.toFixed(2)}</span>
      `;
      this.checkoutSummaryList.appendChild(element);
    });

    let discount = 0;
    if (state.promoApplied) {
      discount = subtotal * 0.15;
      this.checkoutDiscountRow.classList.remove('hidden');
      this.checkoutDiscount.innerText = `-₱${discount.toFixed(2)}`;
    } else {
      this.checkoutDiscountRow.classList.add('hidden');
    }

    const shipping = (subtotal - discount) >= 35 ? 0.00 : 4.99;
    const finalTotal = subtotal - discount + shipping;

    this.checkoutSubtotal.innerText = `₱${subtotal.toFixed(2)}`;
    this.checkoutShipping.innerText = shipping === 0 ? 'FREE' : `₱${shipping.toFixed(2)}`;
    this.checkoutTotalPrice.innerText = `₱${finalTotal.toFixed(2)}`;

    // Reset Wizard steps
    this.changeStep(2, 1);
    this.changeStep(3, 1);
    this.checkoutFormWizard.reset();

    // ── Pre-fill shipping info from saved profile (yv2_profile) ──
    this.prefillShippingFromProfile();

    this.toggleCheckoutWizard(true);
  }

  // Read yv2_profile from localStorage and populate the checkout shipping fields
  prefillShippingFromProfile() {
    const hint = document.getElementById('checkout-profile-hint');
    try {
      const stored = localStorage.getItem('yv2_profile');
      if (!stored) {
        if (hint) hint.style.display = 'flex';
        return;
      }
      const profile = JSON.parse(stored);

      const set = (id, val) => {
        const el = document.getElementById(id);
        if (el && val) el.value = val;
      };

      const hasAddress = !!(profile.street || profile.city);

      set('bill-fname',   profile.firstName);
      set('bill-lname',   profile.lastName);
      set('bill-email',   profile.email);
      set('bill-address', profile.street);
      set('bill-city',    profile.city);
      set('bill-zip',     profile.zipcode);

      // Show hint only if address info is missing
      if (hint) hint.style.display = hasAddress ? 'none' : 'flex';
    } catch (e) {
      if (hint) hint.style.display = 'flex';
    }
  }


  toggleCheckoutWizard(open) {
    if (open) {
      this.checkoutModalOverlay.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
    } else {
      this.checkoutModalOverlay.classList.add('hidden');
      document.body.style.overflow = '';
    }
  }

  // WIZARD FORM VAL & FLOW ACTIONS
  validateAndAdvanceStep(currentStep) {
    if (currentStep === 1) {
      const inputs = [
        document.getElementById('bill-fname'),
        document.getElementById('bill-lname'),
        document.getElementById('bill-email'),
        document.getElementById('bill-address'),
        document.getElementById('bill-city'),
        document.getElementById('bill-zip')
      ];

      // Validate inputs
      let isValid = true;
      inputs.forEach(input => {
        if (!input.checkValidity()) {
          input.reportValidity();
          isValid = false;
        }
      });

      if (isValid) {
        // If "save to profile" checkbox is checked, persist shipping fields to yv2_profile
        const saveCheckbox = document.getElementById('save-shipping-checkbox');
        if (saveCheckbox && saveCheckbox.checked) {
          try {
            const existing = JSON.parse(localStorage.getItem('yv2_profile') || '{}');
            const fname = document.getElementById('bill-fname')?.value.trim();
            const lname = document.getElementById('bill-lname')?.value.trim();
            const email = document.getElementById('bill-email')?.value.trim();
            const street = document.getElementById('bill-address')?.value.trim();
            const city   = document.getElementById('bill-city')?.value.trim();
            const zip    = document.getElementById('bill-zip')?.value.trim();
            const updated = {
              ...existing,
              ...(fname  && { firstName: fname }),
              ...(lname  && { lastName: lname }),
              ...(email  && { email }),
              ...(street && { street }),
              ...(city   && { city }),
              ...(zip    && { zipcode: zip }),
            };
            localStorage.setItem('yv2_profile', JSON.stringify(updated));
            this.createToast('Shipping address saved to your profile!', 'success');
          } catch (e) {}
        }
        this.changeStep(1, 2);
      }
    }
  }

  changeStep(from, to) {
    // Hide old step
    const oldStep = document.getElementById(`checkout-step-${from}`);
    if (oldStep) oldStep.classList.remove('active-step');

    // Show new step
    const newStep = document.getElementById(`checkout-step-${to}`);
    if (newStep) newStep.classList.add('active-step');

    // Update Progress bar indicators
    const indFrom = document.getElementById(`step-ind-${from}`);
    const indTo = document.getElementById(`step-ind-${to}`);
    const line = document.getElementById(`step-line-${Math.min(from, to)}`);

    if (to > from) {
      // Progressing forward
      if (indFrom) {
        indFrom.classList.remove('active');
        indFrom.classList.add('completed');
      }
      if (indTo) indTo.classList.add('active');
      if (line) line.classList.add('completed');
    } else {
      // Retreating backward
      if (indFrom) {
        indFrom.classList.remove('active');
      }
      if (indTo) {
        indTo.classList.remove('completed');
        indTo.classList.add('active');
      }
      if (line) line.classList.remove('completed');
    }
  }

  processCheckoutPayment() {
    // Process payment success simulation
    const payBtn = this.paymentSubmitBtn;
    payBtn.disabled = true;
    payBtn.innerHTML = `<span style="display:inline-flex; align-items:center; gap:8px;"><i data-lucide="loader" style="animation: floating 1s linear infinite;"></i> Processing...</span>`;
    lucide.createIcons();

    setTimeout(() => {
      // Reset button
      payBtn.disabled = false;
      payBtn.innerHTML = `Complete Purchase <i data-lucide="check"></i>`;

      // Set Receipt values
      const orderId = `#YV-${Math.floor(100000 + Math.random() * 900000)}`;
      document.getElementById('receipt-order-id').innerText = orderId;
      document.getElementById('receipt-total-paid').innerText = this.checkoutTotalPrice.innerText;
      
      const deliveryDate = new Date();
      deliveryDate.setDate(deliveryDate.getDate() + 2);
      document.getElementById('receipt-delivery').innerText = deliveryDate.toLocaleDateString(undefined, {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
      });

      // Clear State
      state.cart = [];
      state.promoApplied = false;
      state.saveCartToStorage();
      this.render();

      this.changeStep(2, 3);
      this.createToast("Order completed successfully!", "success");
      lucide.createIcons();
    }, 1500);
  }

  // TESTIMONIAL CAROUSEL SLIDERS
  shiftTestimonial(offset) {
    let nextIndex = state.currentTestimonialIndex + offset;
    if (nextIndex < 0) nextIndex = this.testimonialSlides.length - 1;
    if (nextIndex >= this.testimonialSlides.length) nextIndex = 0;
    this.setTestimonialIndex(nextIndex);
  }

  setTestimonialIndex(index) {
    state.currentTestimonialIndex = index;
    this.testimonialSlides.forEach((slide, i) => {
      if (i === index) {
        slide.classList.add('active');
      } else {
        slide.classList.remove('active');
      }
    });

    this.carouselDots.forEach((dot, i) => {
      if (i === index) {
        dot.classList.add('active');
      } else {
        dot.classList.remove('active');
      }
    });
  }

  // HELPER INTERACTION FUNCTIONS
  scrollToSection(id) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }

  createToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'info';
    if (type === 'success') icon = 'check-circle';
    if (type === 'warning') icon = 'alert-triangle';

    toast.innerHTML = `
      <div class="toast-icon"><i data-lucide="${icon}"></i></div>
      <div class="toast-message">${message}</div>
      <div class="toast-close" onclick="this.parentElement.remove()"><i data-lucide="x"></i></div>
    `;

    container.appendChild(toast);
    lucide.createIcons();

    // Trigger Slide Out & Self Destroy
    setTimeout(() => {
      toast.style.animation = 'fadeOutToast 0.4s cubic-bezier(0.4, 0, 1, 1) forwards';
      setTimeout(() => toast.remove(), 400);
    }, 3500);
  }

  // FOOTER CATEGORY FILTER UTILITY
  setCategory(genre) {
    this.categoryPills.forEach(p => {
      if (p.getAttribute('data-category') === genre) {
        p.classList.add('active');
      } else {
        p.classList.remove('active');
      }
    });
    state.activeCategory = genre;
    this.renderBooksGrid();
  }
}

// Instantiate UI instance
let app;
window.addEventListener('DOMContentLoaded', () => {
  app = new BookstoreUI();
  // Expose methods globally for HTML event handlers
  window.app = app;
  
  // Header Avatar UI update
  try {
    const ustr = localStorage.getItem('user');
    if (ustr) {
      const u = JSON.parse(ustr);
      if (u.profile_image) {
        const profileBtn = document.getElementById('profile-toggle');
        if (profileBtn) {
          profileBtn.innerHTML = `<img src="${u.profile_image}" style="width: 28px; height: 28px; border-radius: 50%; object-fit: cover; border: 1.5px solid var(--primary-color);">`;
        }
      }
    }
  } catch(e) {}
});
