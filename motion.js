/**
 * motion.js — shared interaction & animation layer for YouVersion 2.
 * Purely presentational: it never touches cart, auth or API logic.
 * Everything degrades gracefully without JS and respects prefers-reduced-motion.
 */
(function () {
  const root = document.documentElement;
  root.classList.add('js');

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  // ── Split headlines into masked words ─────────────────────────────────────
  function splitText(el) {
    let index = 0;
    const walk = (node) => {
      Array.from(node.childNodes).forEach((child) => {
        if (child.nodeType === Node.TEXT_NODE) {
          const parts = child.textContent.split(/(\s+)/);
          const frag = document.createDocumentFragment();
          parts.forEach((part) => {
            if (!part) return;
            if (/^\s+$/.test(part)) {
              frag.appendChild(document.createTextNode(' '));
              return;
            }
            const mask = document.createElement('span');
            mask.className = 'split-mask';
            const word = document.createElement('span');
            word.className = 'split-word';
            word.style.setProperty('--w', index++);
            word.textContent = part;
            mask.appendChild(word);
            frag.appendChild(mask);
          });
          child.replaceWith(frag);
        } else if (child.nodeType === Node.ELEMENT_NODE && child.tagName !== 'svg' && !child.hasAttribute('data-lucide')) {
          walk(child);
        }
      });
    };
    if (!el.getAttribute('aria-label')) el.setAttribute('aria-label', el.textContent.replace(/\s+/g, ' ').trim());
    walk(el);
  }
  document.querySelectorAll('[data-split]').forEach(splitText);

  // ── Auto-stagger children ─────────────────────────────────────────────────
  document.querySelectorAll('[data-stagger]').forEach((group) => {
    Array.from(group.children).forEach((child, i) => {
      if (!child.hasAttribute('data-reveal')) child.setAttribute('data-reveal', group.dataset.stagger || '');
      child.style.setProperty('--i', i);
    });
  });

  // ── Reveal on scroll ──────────────────────────────────────────────────────
  const revealTargets = document.querySelectorAll('[data-reveal], [data-split]');
  if (!('IntersectionObserver' in window) || reduceMotion) {
    revealTargets.forEach((el) => el.classList.add('is-visible'));
  } else {
    // Fully clipped elements never report as intersecting, so clip reveals watch their parent.
    const proxies = new Map();
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          (proxies.get(entry.target) || [entry.target]).forEach((el) => el.classList.add('is-visible'));
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    revealTargets.forEach((el) => {
      if (el.dataset.reveal === 'clip' && el.parentElement) {
        const watched = el.parentElement;
        proxies.set(watched, (proxies.get(watched) || [watched.hasAttribute('data-reveal') ? watched : null].filter(Boolean)).concat(el));
        io.observe(watched);
      } else {
        io.observe(el);
      }
    });
  }

  // ── Count-up numbers ──────────────────────────────────────────────────────
  function runCounter(el) {
    const target = parseFloat(el.dataset.count);
    const decimals = parseInt(el.dataset.decimals || '0', 10);
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const format = (v) => prefix + v.toFixed(decimals) + suffix;
    if (reduceMotion) { el.textContent = format(target); return; }
    const duration = 1600;
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 4);
      el.textContent = format(target * eased);
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
  const counters = document.querySelectorAll('[data-count]');
  if ('IntersectionObserver' in window) {
    const cio = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) { runCounter(entry.target); cio.unobserve(entry.target); }
      });
    }, { threshold: 0.6 });
    counters.forEach((el) => cio.observe(el));
  } else {
    counters.forEach(runCounter);
  }

  // ── Header state, scroll progress & parallax (single rAF loop) ────────────
  const header = document.querySelector('.app-header');
  const progress = document.createElement('div');
  progress.className = 'scroll-progress';
  progress.setAttribute('aria-hidden', 'true');
  document.body.appendChild(progress);

  const parallaxEls = reduceMotion ? [] : Array.from(document.querySelectorAll('[data-parallax]'));
  let lastY = window.scrollY;
  let ticking = false;

  function onScroll() {
    const y = window.scrollY;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.transform = `scaleX(${max > 0 ? y / max : 0})`;

    if (header) {
      header.classList.toggle('is-scrolled', y > 24);
      const menuOpen = document.getElementById('mobile-drawer') && !document.getElementById('mobile-drawer').classList.contains('hidden');
      if (y > lastY && y > 400 && !menuOpen) header.classList.add('is-hidden');
      else if (y < lastY - 4 || y < 400) header.classList.remove('is-hidden');
    }
    lastY = y;

    const vh = window.innerHeight;
    parallaxEls.forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.bottom < -200 || rect.top > vh + 200) return;
      const speed = parseFloat(el.dataset.parallax) || 0.15;
      const offset = (rect.top + rect.height / 2 - vh / 2) * speed;
      el.style.transform = `translate3d(0, ${offset.toFixed(1)}px, 0)`;
    });
    ticking = false;
  }
  window.addEventListener('scroll', () => {
    if (!ticking) { ticking = true; requestAnimationFrame(onScroll); }
  }, { passive: true });
  onScroll();

  // ── 3D tilt & magnetic hover (desktop pointers only) ──────────────────────
  if (finePointer && !reduceMotion) {
    document.querySelectorAll('[data-tilt]').forEach((el) => {
      const strength = parseFloat(el.dataset.tilt) || 12;
      el.addEventListener('pointermove', (e) => {
        const r = el.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width - 0.5;
        const py = (e.clientY - r.top) / r.height - 0.5;
        el.style.transform = `perspective(900px) rotateY(${px * strength}deg) rotateX(${-py * strength}deg)`;
      });
      el.addEventListener('pointerleave', () => { el.style.transform = ''; });
    });

    document.querySelectorAll('[data-magnetic]').forEach((el) => {
      el.addEventListener('pointermove', (e) => {
        const r = el.getBoundingClientRect();
        const dx = e.clientX - (r.left + r.width / 2);
        const dy = e.clientY - (r.top + r.height / 2);
        el.style.transform = `translate(${dx * 0.18}px, ${dy * 0.25}px)`;
      });
      el.addEventListener('pointerleave', () => { el.style.transform = ''; });
    });

    // Hero scene follows the cursor in layers
    const scene = document.querySelector('[data-scene]');
    if (scene) {
      const layers = scene.querySelectorAll('[data-depth]');
      scene.addEventListener('pointermove', (e) => {
        const r = scene.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width - 0.5;
        const py = (e.clientY - r.top) / r.height - 0.5;
        layers.forEach((layer) => {
          const d = parseFloat(layer.dataset.depth);
          layer.style.translate = `${(px * d).toFixed(1)}px ${(py * d).toFixed(1)}px`;
        });
      });
      scene.addEventListener('pointerleave', () => layers.forEach((l) => { l.style.translate = ''; }));
    }
  }

  // ── Accordion (5Fs) ───────────────────────────────────────────────────────
  document.querySelectorAll('[data-accordion]').forEach((acc) => {
    const items = acc.querySelectorAll('.framework-item');
    items.forEach((item) => {
      const trigger = item.querySelector('.framework-trigger');
      if (!trigger) return;
      trigger.addEventListener('click', () => {
        const willOpen = !item.classList.contains('is-open');
        items.forEach((other) => {
          other.classList.remove('is-open');
          other.querySelector('.framework-trigger')?.setAttribute('aria-expanded', 'false');
        });
        if (willOpen) {
          item.classList.add('is-open');
          trigger.setAttribute('aria-expanded', 'true');
        }
      });
    });
  });

  // ── Hero terminal: "installing" the 5Fs ───────────────────────────────────
  document.querySelectorAll('[data-terminal]').forEach((term) => {
    const status = term.querySelector('.terminal-status');
    const bar = term.querySelector('.terminal-bar span');
    const steps = (term.dataset.terminal || '').split('|').filter(Boolean);
    if (!status || !steps.length) return;
    let i = 0;
    const show = () => {
      const done = i % (steps.length + 1);
      if (done === steps.length) {
        status.innerHTML = '<span class="ok">✓</span> you@2.0 ready — there\'s still more becoming ahead';
        bar.style.setProperty('--p', '100%');
      } else {
        status.textContent = `installing ${steps[done]}…`;
        bar.style.setProperty('--p', `${Math.round((done / steps.length) * 100)}%`);
      }
      i++;
    };
    show();
    if (!reduceMotion) setInterval(show, 1600);
  });

  // ── Escape closes whichever overlay is open ───────────────────────────────
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const pairs = [
      ['checkout-modal-overlay', 'close-checkout-modal'],
      ['detail-modal-overlay', 'close-detail-modal'],
      ['cart-drawer', 'close-cart-btn'],
      ['mobile-drawer', 'close-mobile-drawer']
    ];
    for (const [panelId, closeId] of pairs) {
      const panel = document.getElementById(panelId);
      if (panel && !panel.classList.contains('hidden')) {
        document.getElementById(closeId)?.click();
        break;
      }
    }
  });

  // Close the mobile drawer after choosing an in-page link
  document.querySelectorAll('#mobile-drawer a[href^="#"]').forEach((link) => {
    link.addEventListener('click', () => {
      if (link.getAttribute('href') !== '#') document.getElementById('mobile-drawer')?.classList.add('hidden');
    });
  });

  // ── Page transitions between internal pages ───────────────────────────────
  if (!reduceMotion) {
    document.addEventListener('click', (e) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const link = e.target.closest('a[href]');
      if (!link || link.target === '_blank' || link.hasAttribute('download')) return;
      const href = link.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:') || href.startsWith('javascript:')) return;
      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (url.pathname === window.location.pathname && url.hash) return;
      e.preventDefault();
      root.classList.add('is-leaving');
      setTimeout(() => { window.location.href = url.href; }, 520);
    });
    // Restore when coming back through the bfcache
    window.addEventListener('pageshow', (e) => {
      if (e.persisted) root.classList.remove('is-leaving');
    });
  }
})();
