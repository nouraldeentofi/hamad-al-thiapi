/* Dr. Hamad Al-Thiapi — site behaviour (vanilla, no frameworks) */
(() => {
  'use strict';
  const d = document, root = d.documentElement, body = d.body;
  const mq = q => window.matchMedia(q);
  const reduce = mq('(prefers-reduced-motion: reduce)');
  const phone = mq('(max-width: 599px)');
  const supports = p => window.CSS && CSS.supports && CSS.supports(p);
  const hasView = supports('animation-timeline: view()');
  const hasScroll = supports('animation-timeline: scroll()');
  const NS = 'http://www.w3.org/2000/svg';
  const store = {
    get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} }
  };
  const session = {
    set: (k, v) => { try { sessionStorage.setItem(k, v); } catch (e) {} }
  };
  const raf = fn => { let q = false; return (...a) => { if (q) return; q = true; requestAnimationFrame(() => { q = false; fn(...a); }); }; };
  const headerH = () => parseFloat(getComputedStyle(root).getPropertyValue('--header-h')) || 70;

  /* ---------------- theme ---------------- */
  const themeBtn = d.querySelector('[data-theme-toggle]');
  const themeMeta = d.querySelector('meta[name="theme-color"]');
  const syncTheme = () => {
    const dark = root.getAttribute('data-theme') === 'dark';
    if (themeBtn) themeBtn.setAttribute('aria-pressed', String(dark));
    if (themeMeta) themeMeta.setAttribute('content', dark ? '#12111d' : '#1b1a2e');
  };
  if (themeBtn) themeBtn.addEventListener('click', () => {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    store.set('theme', next);
    syncTheme();
  });
  syncTheme();

  /* ---------------- language: remember choice, keep the reader's place ---------------- */
  d.querySelectorAll('[data-lang-switch]').forEach(a => a.addEventListener('click', () => {
    store.set('lang', a.getAttribute('data-lang-switch'));
    const secs = d.querySelectorAll('[data-section]');
    const top = headerH() + 20;
    let idx = 0, frac = 0;
    for (let i = 0; i < secs.length; i++) {
      const r = secs[i].getBoundingClientRect();
      if (r.bottom > top) { idx = i; frac = Math.max(0, Math.min(1, (top - r.top) / Math.max(1, r.height))); break; }
    }
    session.set('langpos', JSON.stringify({ page: body.getAttribute('data-page'), idx, frac, y: window.scrollY }));
  }));

  /* ---------------- header glass + scroll fallbacks ---------------- */
  const header = d.querySelector('[data-header]');
  const progress = d.querySelector('.progress');
  const heroOut = d.querySelectorAll('[data-hero-out]');
  const heroVis = d.querySelectorAll('[data-hero-visual]');
  const onScroll = () => {
    const y = window.scrollY;
    if (header) header.classList.toggle('is-scrolled', y > 8);
    if (!hasScroll && !reduce.matches) {
      const max = Math.max(1, d.documentElement.scrollHeight - window.innerHeight);
      if (progress) progress.style.transform = 'scaleX(' + Math.min(1, y / max).toFixed(4) + ')';
      const vh = window.innerHeight;
      const q = Math.min(1, y / (0.8 * vh));
      heroOut.forEach(el => { el.style.opacity = (1 - 0.88 * q).toFixed(3); el.style.transform = 'translateY(' + (-40 * q).toFixed(1) + 'px) scale(' + (1 - 0.02 * q).toFixed(4) + ')'; });
      const v = Math.min(1, y / (0.95 * vh));
      heroVis.forEach(el => { el.style.opacity = (1 - 0.75 * v).toFixed(3); el.style.transform = 'translateY(' + (60 * v).toFixed(1) + 'px) scale(' + (1 - 0.1 * v).toFixed(4) + ')'; });
    }
  };
  window.addEventListener('scroll', raf(onScroll), { passive: true });
  onScroll();

  /* ---------------- reveal fallback (browsers without scroll-driven animations) ---------------- */
  if (!hasView && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
    }), { rootMargin: '0px 0px -6% 0px', threshold: 0.08 });
    d.querySelectorAll('[data-reveal], .ch').forEach(el => io.observe(el));
  }

  /* ---------------- numbers count up ---------------- */
  const fmt = (n, dec) => n.toLocaleString('en-US', { minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0 });
  const counts = d.querySelectorAll('.count[data-count]');
  if (counts.length && 'IntersectionObserver' in window) {
    const run = el => {
      const target = +el.getAttribute('data-count'), dec = +(el.getAttribute('data-dec') || 0);
      if (reduce.matches) { el.textContent = fmt(target, dec); return; }
      const t0 = performance.now(), dur = 1800;
      const step = now => {
        const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
        el.textContent = fmt(dec ? target * e : Math.round(target * e), dec);
        if (k < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };
    const ioc = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting) { run(e.target); ioc.unobserve(e.target); }
    }), { threshold: 0.5 });
    counts.forEach(el => {
      const w = el.getBoundingClientRect().width;
      el.style.minInlineSize = Math.ceil(w + 1) + 'px';
      const r = el.getBoundingClientRect();
      if (!reduce.matches && (r.top > window.innerHeight || r.bottom < 0)) el.textContent = fmt(0, +(el.getAttribute('data-dec') || 0));
      ioc.observe(el);
    });
  }

  /* ---------------- the night sky: light packets travelling along the routes ---------------- */
  const skies = [];
  class Sky {
    constructor(el) {
      this.el = el;
      this.svg = el.querySelector('svg');
      this.layer = el.querySelector('.packets');
      this.items = [];
      this.on = false;
      this.scale = 1;
      if (!this.svg || !this.layer) return;
      const vb = this.svg.viewBox.baseVal;
      this.vb = vb;
      el.querySelectorAll('path.route').forEach((p, i) => {
        const n = +(p.getAttribute('data-packets') || 0);
        if (!n) return;
        let len = 0;
        try { len = p.getTotalLength(); } catch (e) { return; }
        if (!len) return;
        const N = 72, pts = new Float32Array((N + 1) * 2);
        for (let k = 0; k <= N; k++) { const q = p.getPointAtLength(len * k / N); pts[2 * k] = q.x; pts[2 * k + 1] = q.y; }
        const speed = (+(p.getAttribute('data-speed') || 8)) / 100;
        const delay = parseFloat(getComputedStyle(p).animationDelay) || 0.5;
        for (let j = 0; j < n; j++) {
          const g = d.createElementNS(NS, 'g');
          const glow = d.createElementNS(NS, 'circle'); glow.setAttribute('class', 'pk-glow');
          const core = d.createElementNS(NS, 'circle'); core.setAttribute('class', 'pk-core');
          g.append(glow, core);
          g.setAttribute('opacity', '0');
          this.layer.appendChild(g);
          this.items.push({ g, glow, core, pts, N, speed, phase: (i * 0.37 + j * 0.5) % 1.6, start: delay + 2.6, gap: 0.55 + (i % 4) * 0.18, back: p.classList.contains('route--back') });
        }
      });
      this.resize();
    }
    resize() {
      if (!this.svg) return;
      const r = this.svg.getBoundingClientRect();
      if (!r.width || !this.vb || !this.vb.width) return;
      const slice = (this.svg.getAttribute('preserveAspectRatio') || '').indexOf('slice') > -1;
      const sx = r.width / this.vb.width, sy = r.height / this.vb.height;
      this.scale = slice ? Math.max(sx, sy) : Math.min(sx, sy);
      const core = 2.3 / this.scale, glow = 6.5 / this.scale;
      this.items.forEach(it => { it.core.setAttribute('r', core.toFixed(2)); it.glow.setAttribute('r', glow.toFixed(2)); });
    }
    frame(t) {
      for (const it of this.items) {
        if (t < it.start) continue;
        const cyc = 1 + it.gap;
        const u = ((t - it.start) * it.speed + it.phase) % cyc;
        if (u > 1) { if (it.vis) { it.g.setAttribute('opacity', '0'); it.vis = false; } continue; }
        const f = u * it.N, i = Math.min(it.N - 1, Math.floor(f)), fr = f - i, P = it.pts;
        const x = P[2 * i] + (P[2 * i + 2] - P[2 * i]) * fr;
        const y = P[2 * i + 1] + (P[2 * i + 3] - P[2 * i + 1]) * fr;
        it.g.setAttribute('transform', 'translate(' + x.toFixed(1) + ' ' + y.toFixed(1) + ')');
        it.g.setAttribute('opacity', Math.min(1, u * 7, (1 - u) * 7).toFixed(2));
        it.vis = true;
      }
    }
  }
  const t0 = performance.now();
  let looping = false;
  const loop = now => {
    const t = (now - t0) / 1000;
    let any = false;
    for (const s of skies) if (s.on) { s.frame(t); any = true; }
    if (any && !d.hidden) requestAnimationFrame(loop); else looping = false;
  };
  const kick = () => { if (!looping && !reduce.matches) { looping = true; requestAnimationFrame(loop); } };
  if (!reduce.matches && 'IntersectionObserver' in window) {
    d.querySelectorAll('.sky').forEach(el => { const s = new Sky(el); if (s.items.length) skies.push(s); });
    const ios = new IntersectionObserver(es => es.forEach(e => {
      const s = skies.find(x => x.el === e.target);
      if (s) { s.on = e.isIntersecting; if (s.on) kick(); }
    }), { rootMargin: '80px' });
    skies.forEach(s => ios.observe(s.el));
    window.addEventListener('resize', raf(() => skies.forEach(s => s.resize())));
    d.addEventListener('visibilitychange', () => { if (!d.hidden) kick(); });
  }

  /* ---------------- swipe rows on phones: dots, centred card, auto-rotate ---------------- */
  d.querySelectorAll('[data-swipe]').forEach(row => {
    const cards = Array.from(row.children);
    const dotsEl = row.nextElementSibling && row.nextElementSibling.classList.contains('dots') ? row.nextElementSibling : null;
    const dots = dotsEl ? Array.from(dotsEl.children) : [];
    let active = -1, lastTouch = 0, visible = false, seenAt = 0;
    const head = row.closest('section') && row.closest('section').querySelector('.sec-title');
    if (head) row.setAttribute('aria-label', head.textContent.trim());
    const focusable = () => { if (phone.matches) { row.tabIndex = 0; row.setAttribute('role', 'group'); } else { row.removeAttribute('tabindex'); row.removeAttribute('role'); } };
    focusable();
    const setActive = i => { if (i === active) return; active = i; dots.forEach((dt, k) => dt.classList.toggle('on', k === i)); };
    const update = () => {
      if (!phone.matches) { cards.forEach(c => { c.style.transform = ''; c.style.opacity = ''; }); return; }
      const rr = row.getBoundingClientRect(), cx = rr.left + rr.width / 2;
      let best = 0, bd = Infinity;
      cards.forEach((c, k) => {
        const r = c.getBoundingClientRect(), dd = Math.abs(r.left + r.width / 2 - cx);
        if (dd < bd) { bd = dd; best = k; }
        if (!hasView && !reduce.matches) {
          const ratio = Math.min(1, dd / Math.max(1, rr.width));
          c.style.transform = 'scale(' + (1 - 0.1 * ratio).toFixed(3) + ')';
          c.style.opacity = (1 - 0.5 * ratio).toFixed(3);
        }
      });
      setActive(best);
    };
    row.addEventListener('scroll', raf(update), { passive: true });
    ['pointerdown', 'touchstart', 'wheel', 'keydown'].forEach(ev => row.addEventListener(ev, () => { lastTouch = performance.now(); }, { passive: true }));
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(es => { const v = es[0].isIntersecting; if (v && !visible) seenAt = performance.now(); visible = v; }, { threshold: 0.5 }).observe(row);
    }
    let lastMove = 0;
    setInterval(() => {
      if (!phone.matches || !visible || reduce.matches || d.hidden || cards.length < 2) return;
      const now = performance.now();
      if (now - lastTouch < 9000 || now - seenAt < 3800 || now - lastMove < 5000) return;
      lastMove = now;
      const next = cards[(Math.max(0, active) + 1) % cards.length];
      const rr = row.getBoundingClientRect(), r = next.getBoundingClientRect();
      row.scrollBy({ left: (r.left + r.width / 2) - (rr.left + rr.width / 2), behavior: 'smooth' });
    }, 400);
    phone.addEventListener && phone.addEventListener('change', () => { focusable(); update(); });
    window.addEventListener('resize', raf(update));
    update();
  });

  /* ---------------- journey: on phones the rest of a chapter opens below its button ---------------- */
  d.querySelectorAll('.ch-toggle').forEach(btn => btn.addEventListener('click', () => {
    const box = d.getElementById(btn.getAttribute('aria-controls'));
    const open = btn.getAttribute('aria-expanded') !== 'true';
    btn.setAttribute('aria-expanded', String(open));
    if (box) box.classList.toggle('is-open', open);
  }));

  /* ---------------- research diagram: classic BGP vs SDN ---------------- */
  class Diagram {
    constructor(el) {
      this.el = el;
      this.svg = el.querySelector('.dg-svg');
      this.pulsesG = el.querySelector('.dg-pulses');
      this.pktG = el.querySelector('.dg-packets');
      this.fill = el.querySelector('.dg-time-fill');
      this.btns = Array.from(el.querySelectorAll('.seg-btn'));
      this.paths = {};
      el.querySelectorAll('.dg-path').forEach(p => { const k = p.getAttribute('class').match(/dg-path--(\w+)/)[1]; this.paths[k] = p; });
      this.nodes = {};
      el.querySelectorAll('[data-n]').forEach(n => {
        let x, y;
        if (n.tagName.toLowerCase() === 'circle') { x = +n.getAttribute('cx'); y = +n.getAttribute('cy'); }
        else { const m = (n.getAttribute('transform') || '').match(/translate\(([-\d.]+)[ ,]+([-\d.]+)\)/); x = +m[1]; y = +m[2]; }
        this.nodes[n.getAttribute('data-n')] = { el: n, x, y };
      });
      this.route = {
        old: ['S', 'A1', 'B1', 'B2', 'C1', 'T'],
        new: ['S', 'A2', 'D1', 'D2', 'C2', 'T']
      };
      this.mode = 'bgp';
      this.picked = false;
      this.visible = false;
      this.elapsed = 0;
      this.last = 0;
      this.flow = 'old';
      this.flowAlpha = 1;
      this.pulses = [];
      this.pkts = [];
      for (let i = 0; i < 3; i++) {
        const c = d.createElementNS(NS, 'circle');
        c.setAttribute('r', '4'); c.setAttribute('class', 'dg-pkt'); c.setAttribute('opacity', '0');
        this.pktG.appendChild(c); this.pkts.push(c);
      }
      this.btns.forEach(b => b.addEventListener('click', () => { this.picked = true; this.setMode(b.getAttribute('data-mode')); }));
      this.setMode('bgp');
      if ('IntersectionObserver' in window) {
        new IntersectionObserver(es => {
          this.visible = es[0].isIntersecting;
          if (this.visible && !this.running && !reduce.matches) { this.running = true; this.last = performance.now(); requestAnimationFrame(t => this.tick(t)); }
        }, { threshold: 0.25 }).observe(el);
      }
    }
    setMode(m) {
      this.mode = m;
      this.el.setAttribute('data-mode', m);
      this.btns.forEach(b => b.setAttribute('aria-pressed', String(b.getAttribute('data-mode') === m)));
      this.reset();
      if (reduce.matches) this.staticEnd();
    }
    timeline() {
      return this.mode === 'bgp' ? [
        [1.6, () => this.breakLink('B2')],
        [1.7, () => { this.pulse('B2', 'B1', .55); this.pulse('B2', 'B3', .55); }],
        [2.3, () => { this.busy(['B1', 'B3']); this.pulse('B1', 'A1', .65); this.pulse('B3', 'D3', .65); this.off('old'); }],
        [3.0, () => { this.busy(['A1', 'D3']); this.on('trial'); }],
        [3.9, () => { this.pulse('D3', 'D2', .5); this.pulse('A1', 'A2', .45); }],
        [4.5, () => { this.busy(['D2', 'A2']); this.pulse('D2', 'C2', .5); this.pulse('A2', 'D1', .5); }],
        [5.2, () => { this.busy(['D1', 'C2']); this.off('trial'); }],
        [5.6, () => { this.on('new'); this.clearBusy(); }],
        [6.4, () => { this.flow = 'new'; }],
        [9.8, () => this.next()]
      ] : [
        [1.6, () => this.breakLink('B2')],
        [1.7, () => this.pulse('B2', 'K', .45)],
        [2.15, () => this.busy(['K'])],
        [2.35, () => { ['A1', 'A2', 'D1', 'D2', 'C2'].forEach(n => this.pulse('K', n, .45)); this.off('old'); }],
        [2.8, () => { this.busy(['A2', 'D1', 'D2', 'C2']); this.on('new', .6); }],
        [3.25, () => { this.clearBusy(); this.flow = 'new'; }],
        [7.0, () => this.next()]
      ];
    }
    reset() {
      this.elapsed = 0;
      this.events = this.timeline();
      this.ev = 0;
      this.el.classList.remove('is-broken');
      this.clearBusy();
      this.pulses.forEach(p => p.c.remove()); this.pulses = [];
      Object.keys(this.paths).forEach(k => { const p = this.paths[k]; p.style.transitionDuration = ''; p.classList.remove('is-on', 'is-off'); });
      this.paths.old.classList.add('is-on');
      this.flow = 'old'; this.flowAlpha = 1;
      if (this.fill) { this.fill.style.transition = 'none'; this.fill.style.transform = 'scaleX(0)'; }
    }
    staticEnd() {
      this.el.classList.add('is-broken');
      this.paths.old.classList.remove('is-on');
      this.paths.new.classList.add('is-on');
      if (this.fill) { this.fill.style.transition = 'none'; this.fill.style.transform = 'scaleX(' + (this.mode === 'bgp' ? .86 : .3) + ')'; }
    }
    next() {
      if (!this.picked && this.btns.length !== 1) this.setMode(this.mode === 'bgp' ? 'sdn' : 'bgp');
      else this.reset();
    }
    breakLink() {
      this.el.classList.add('is-broken');
      this.flowAlpha = 0;
      this.busy(['B2']);
      if (this.fill) {
        const dur = this.mode === 'bgp' ? 4.8 : 1.6;
        this.fill.style.transition = 'none';
        this.fill.style.transform = 'scaleX(0)';
        void this.fill.getBoundingClientRect();
        this.fill.style.transition = 'transform ' + dur + 's linear';
        this.fill.style.transform = 'scaleX(' + (this.mode === 'bgp' ? .86 : .3) + ')';
      }
    }
    on(k, dur) { const p = this.paths[k]; if (dur) p.style.transitionDuration = dur + 's, .45s'; p.classList.remove('is-off'); p.classList.add('is-on'); }
    off(k) { this.paths[k].classList.add('is-off'); }
    busy(list) { list.forEach(n => this.nodes[n] && this.nodes[n].el.classList.add('is-busy')); }
    clearBusy() { Object.values(this.nodes).forEach(n => n.el.classList.remove('is-busy')); }
    pulse(a, b, dur) {
      const c = d.createElementNS(NS, 'circle');
      c.setAttribute('r', '5.5'); c.setAttribute('class', 'dg-pulse');
      this.pulsesG.appendChild(c);
      this.pulses.push({ c, a: this.nodes[a], b: this.nodes[b], t0: this.elapsed, dur });
    }
    tick(now) {
      if (!this.visible || reduce.matches || d.hidden) { this.running = false; return; }
      const dt = Math.min(0.1, (now - this.last) / 1000);
      this.last = now;
      this.elapsed += dt;
      while (this.ev < this.events.length && this.elapsed >= this.events[this.ev][0]) { const fn = this.events[this.ev][1]; this.ev++; fn(); }
      // pulses
      this.pulses = this.pulses.filter(p => {
        const k = (this.elapsed - p.t0) / p.dur;
        if (k >= 1) { p.c.remove(); return false; }
        const e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
        p.c.setAttribute('cx', (p.a.x + (p.b.x - p.a.x) * e).toFixed(1));
        p.c.setAttribute('cy', (p.a.y + (p.b.y - p.a.y) * e).toFixed(1));
        p.c.setAttribute('opacity', Math.min(1, (1 - k) * 4).toFixed(2));
        return true;
      });
      // packets along the active route
      const target = this.flow === 'old' && this.el.classList.contains('is-broken') ? 0 : 1;
      this.flowAlpha += (target - this.flowAlpha) * Math.min(1, dt * 6);
      const pts = this.route[this.flow].map(n => this.nodes[n]);
      const seg = [], lens = [];
      let total = 0;
      for (let i = 0; i < pts.length - 1; i++) { const l = Math.hypot(pts[i + 1].x - pts[i].x, pts[i + 1].y - pts[i].y); seg.push(l); total += l; }
      this.pkts.forEach((c, i) => {
        let u = ((this.elapsed * 0.24) + i / this.pkts.length) % 1;
        let dist = u * total, j = 0;
        while (j < seg.length - 1 && dist > seg[j]) { dist -= seg[j]; j++; }
        const f = seg[j] ? dist / seg[j] : 0;
        c.setAttribute('cx', (pts[j].x + (pts[j + 1].x - pts[j].x) * f).toFixed(1));
        c.setAttribute('cy', (pts[j].y + (pts[j + 1].y - pts[j].y) * f).toFixed(1));
        const edge = Math.min(1, u * 10, (1 - u) * 10);
        c.setAttribute('opacity', (edge * this.flowAlpha).toFixed(2));
      });
      requestAnimationFrame(t => this.tick(t));
    }
  }
  d.querySelectorAll('[data-diagram]').forEach(el => new Diagram(el));
})();
