"""
Full QA run for the site (Playwright + axe-core).
    python3 tests/test_site.py [--base http://127.0.0.1:8765/] [--quick]
Prints a report and exits 1 if anything fails.
"""
import asyncio, json, os, sys, time, math
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8765/"
for i, a in enumerate(sys.argv):
    if a == "--base":
        BASE = sys.argv[i + 1]
QUICK = "--quick" in sys.argv
AXE = os.environ.get("AXE", "/tmp/claude-0/-home-claude/de5effe6-e0c8-50f2-bcd8-0ff6f15724b0/scratchpad/npm/node_modules/axe-core/axe.min.js")
SHOTS = os.environ.get("SHOTS", "/tmp/claude-0/-home-claude/de5effe6-e0c8-50f2-bcd8-0ff6f15724b0/scratchpad/qa")
os.makedirs(SHOTS, exist_ok=True)

PAGES = ["index", "journey", "impact", "research", "contact"]
LANGS = ["ar", "en"]
THEMES = ["light", "dark"]
VIEWPORTS = [  # name, w, h, touch
    ("p320", 320, 640, True), ("p360", 360, 740, True), ("p390", 390, 844, True), ("p412", 412, 915, True),
    ("p430", 430, 932, True), ("land", 844, 390, True), ("t768", 768, 1024, True),
    ("d1024", 1024, 768, False), ("d1366", 1366, 768, False), ("d1440", 1440, 900, False),
]
if QUICK:
    VIEWPORTS = [v for v in VIEWPORTS if v[0] in ("p360", "t768", "d1440")]

FAIL = []
NOTES = []
def fail(msg):
    FAIL.append(msg)
def note(msg):
    NOTES.append(msg)

def url(page, lang):
    return BASE + ("en/" if lang == "en" else "") + ("" if page == "index" else page + ".html") + "?stay=1"

INIT = """
window.__cls = 0; window.__shifts = [];
try { new PerformanceObserver(l => { for (const e of l.getEntries()) { if (!e.hadRecentInput) { window.__cls += e.value; window.__shifts.push({v:e.value, t:e.startTime, src:(e.sources||[]).map(s=>s.node && (s.node.className||s.node.nodeName)).join('|')}); } } }).observe({type:'layout-shift', buffered:true}); } catch(e) {}
"""

async def new_ctx(browser, w, h, touch, theme, reduced=False):
    ctx = await browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1, is_mobile=touch and w < 900,
                                    has_touch=touch, reduced_motion="reduce" if reduced else "no-preference")
    await ctx.add_init_script("try{if(!sessionStorage.getItem('__qa')){sessionStorage.setItem('__qa','1');localStorage.setItem('theme','%s');localStorage.removeItem('lang')}}catch(e){}" % theme)
    await ctx.add_init_script(INIT)
    return ctx

async def basic_checks(browser, page_name, lang, vp, theme, sem):
    name, w, h, touch = vp
    async with sem:
        ctx = await new_ctx(browser, w, h, touch, theme)
        pg = await ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" else None)
        tag = f"{page_name}/{lang}/{name}/{theme}"
        try:
            await pg.goto(url(page_name, lang), wait_until="networkidle")
            await pg.wait_for_timeout(900)
            # scroll through the page (reveals, counters), then back to top
            H = await pg.evaluate("document.documentElement.scrollHeight")
            y = 0
            while y < H:
                await pg.evaluate(f"window.scrollTo(0,{y})"); await pg.wait_for_timeout(70); y += int(h * 0.8)
            await pg.evaluate("window.scrollTo(0,0)"); await pg.wait_for_timeout(300)
            r = await pg.evaluate("""() => {
              const de = document.documentElement;
              const over = Math.max(de.scrollWidth, document.body.scrollWidth) - de.clientWidth;
              const wide = [];
              if (over > 0) {
                for (const el of document.querySelectorAll('body *')) {
                  const b = el.getBoundingClientRect();
                  if (b.width && (b.right > de.clientWidth + 1 || b.left < -1)) {
                    let p = el, clipped = false;
                    while ((p = p.parentElement)) { const cs = getComputedStyle(p); if (/(hidden|clip)/.test(cs.overflowX) || /(hidden|clip)/.test(cs.overflow)) { clipped = true; break; } }
                    if (!clipped) wide.push((el.className && el.className.baseVal === undefined ? el.className : el.tagName) + ' ' + Math.round(b.left) + '..' + Math.round(b.right));
                  }
                  if (wide.length > 6) break;
                }
              }
              return {over, wide};
            }""")
            if r["over"] > 0:
                fail(f"[hscroll] {tag}: page is {r['over']}px wider than the viewport: {r['wide']}")
            if errs:
                fail(f"[js] {tag}: {errs[:3]}")
            if touch:
                small = await pg.evaluate("""() => {
                  const out = [];
                  for (const el of document.querySelectorAll('a[href], button, summary, [role=button]')) {
                    const cs = getComputedStyle(el);
                    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
                    let p = el, hidden = false;
                    while ((p = p.parentElement)) { const c = getComputedStyle(p); if (c.display === 'none' || c.visibility === 'hidden') { hidden = true; break; } }
                    if (hidden) continue;
                    const b = el.getBoundingClientRect();
                    if (!b.width && !b.height) continue;
                    if (el.classList.contains('skip')) continue;
                    if (b.width < 43.5 || b.height < 43.5) out.push((el.className || el.tagName) + ' "' + (el.textContent||'').trim().slice(0,30) + '" ' + Math.round(b.width) + 'x' + Math.round(b.height));
                  }
                  return out;
                }""")
                if small:
                    fail(f"[touch<44] {tag}: {small[:5]}")
            # no underlines at rest
            und = await pg.evaluate("""() => [...document.querySelectorAll('a,button')].filter(e => getComputedStyle(e).textDecorationLine !== 'none').map(e => e.className || e.tagName).slice(0,5)""")
            if und:
                fail(f"[underline] {tag}: {und}")
            cls = await pg.evaluate("window.__cls")
            if cls > 0.0001:
                shifts = await pg.evaluate("window.__shifts.slice(0,5)")
                fail(f"[cls-load] {tag}: CLS {cls:.4f} {shifts}")
        except Exception as e:
            fail(f"[error] {tag}: {e}")
        await ctx.close()

async def axe_check(browser, page_name, lang, theme, w, h, sem):
    async with sem:
        ctx = await new_ctx(browser, w, h, w < 900, theme)
        pg = await ctx.new_page()
        tag = f"{page_name}/{lang}/{w}/{theme}"
        try:
            await pg.goto(url(page_name, lang), wait_until="networkidle")
            await pg.add_style_tag(content="*{animation:none!important;transition:none!important}[data-reveal]{opacity:1!important;transform:none!important}.swipe>*{opacity:1!important}")
            await pg.evaluate("document.querySelectorAll('.count[data-count]').forEach(e=>e.textContent=(+e.dataset.count).toLocaleString('en-US'))")
            await pg.add_script_tag(path=AXE)
            res = await pg.evaluate("""async () => { const r = await axe.run(document, {resultTypes:['violations']}); return r.violations.filter(v => v.impact === 'serious' || v.impact === 'critical').map(v => ({id:v.id, impact:v.impact, n:v.nodes.length, sample:v.nodes.slice(0,3).map(n=>n.target.join(' ') + ' :: ' + (n.failureSummary||'').slice(0,160))})); }""")
            if res:
                fail(f"[axe] {tag}: {json.dumps(res, ensure_ascii=False)[:900]}")
        except Exception as e:
            fail(f"[axe-error] {tag}: {e}")
        await ctx.close()

async def interaction_checks(browser, lang):
    """Touch context: nav, language + theme toggles, carousels, hover not sticking, diagram, FAQ, nothing jumps."""
    ctx = await new_ctx(browser, 390, 844, True, "light")
    pg = await ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    tag = f"touch/{lang}"
    await pg.goto(url("index", lang), wait_until="networkidle")
    await pg.wait_for_timeout(800)
    # dock navigation
    for slug in ["journey", "impact", "research", "contact", "index"]:
        href = ("./" if slug == "index" else slug + ".html")
        loc = pg.locator(f'.dock a[href="{href}"]')
        if await loc.count() == 0:
            fail(f"[nav] {tag}: dock link {href} missing"); continue
        await loc.first.tap()
        await pg.wait_for_load_state("networkidle"); await pg.wait_for_timeout(400)
        cur = await pg.evaluate("document.body.dataset.page")
        if cur != slug:
            fail(f"[nav] {tag}: tapping {href} went to {cur}")
        cur_link = await pg.evaluate("(document.querySelector('.dock [aria-current=page]')||{}).getAttribute ? document.querySelector('.dock [aria-current=page]').getAttribute('href') : null")
        if cur_link != href:
            fail(f"[nav] {tag}: dock highlight on {cur_link}, expected {href}")
    # theme toggle: no layout shift, persists
    await pg.evaluate("window.scrollTo(0, 900)"); await pg.wait_for_timeout(500)
    before = await pg.evaluate("[window.scrollY, document.querySelector('.story, .sec').getBoundingClientRect().top, window.__cls]")
    await pg.locator("[data-theme-toggle]").tap(); await pg.wait_for_timeout(600)
    after = await pg.evaluate("[window.scrollY, document.querySelector('.story, .sec').getBoundingClientRect().top, window.__cls, document.documentElement.dataset.theme, localStorage.getItem('theme')]")
    if after[3] != "dark" or after[4] != "dark":
        fail(f"[theme] {tag}: toggle did not switch/persist: {after}")
    if abs(after[0] - before[0]) > 0.5 or abs(after[1] - before[1]) > 0.5:
        fail(f"[jump-theme] {tag}: page moved {before} -> {after}")
    await pg.locator("[data-theme-toggle]").tap(); await pg.wait_for_timeout(300)
    # carousels rotate on their own and swipe
    rows = await pg.evaluate("document.querySelectorAll('[data-swipe]').length")
    if rows:
        await pg.evaluate("document.querySelector('[data-swipe]').scrollIntoView({block:'center'})")
        await pg.wait_for_timeout(700)
        y0 = await pg.evaluate("window.scrollY")
        a0 = await pg.evaluate("[...document.querySelector('[data-swipe]').nextElementSibling.children].findIndex(i=>i.classList.contains('on'))")
        nxt = await pg.evaluate("document.querySelector('[data-swipe]').parentElement.nextElementSibling ? 1 : 0")
        await pg.wait_for_timeout(9800)
        a1 = await pg.evaluate("[...document.querySelector('[data-swipe]').nextElementSibling.children].findIndex(i=>i.classList.contains('on'))")
        y1 = await pg.evaluate("window.scrollY")
        if a1 == a0:
            fail(f"[carousel] {tag}: did not rotate on its own ({a0} -> {a1})")
        if abs(y1 - y0) > 0.5:
            fail(f"[jump-carousel] {tag}: page scrolled while carousel rotated {y0}->{y1}")
        box = await pg.evaluate("(() => { const r = document.querySelector('[data-swipe]').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
        # swipe gesture (scroll the row by one card)
        await pg.evaluate("(() => { const row = document.querySelector('[data-swipe]'); row.scrollBy({left: (document.dir==='rtl'?-1:1) * row.clientWidth * 0.84, behavior:'instant'}); })()")
        await pg.wait_for_timeout(500)
        a2 = await pg.evaluate("[...document.querySelector('[data-swipe]').nextElementSibling.children].findIndex(i=>i.classList.contains('on'))")
        if a2 == a1:
            fail(f"[carousel] {tag}: swipe did not change the active dot ({a1} -> {a2})")
    # hover must not stick on touch: tap a card link? (navigates) — tap a non-link card instead
    card = pg.locator(".thought").first
    if await card.count():
        await card.scroll_into_view_if_needed(); await card.tap(); await pg.wait_for_timeout(700)
        tr = await card.evaluate("e => getComputedStyle(e).transform")
        sh = await card.evaluate("e => getComputedStyle(e).boxShadow")
        base_sh = await pg.evaluate("getComputedStyle(document.querySelectorAll('.thought')[1]).boxShadow")
        if sh != base_sh:
            fail(f"[hover-stick] {tag}: tapped card keeps a different shadow")
    # language toggle keeps position and works
    await pg.goto(url("journey", lang), wait_until="networkidle")
    await pg.wait_for_timeout(500)
    await pg.evaluate("document.querySelectorAll('.ch')[3].scrollIntoView({block:'start'})"); await pg.wait_for_timeout(400)
    sec_before = await pg.evaluate("(() => { const s=[...document.querySelectorAll('[data-section]')]; const h=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h'))+20; return s.findIndex(x=>x.getBoundingClientRect().bottom>h); })()")
    await pg.locator("[data-lang-switch]").first.tap()
    await pg.wait_for_load_state("networkidle"); await pg.wait_for_timeout(700)
    new_lang = await pg.evaluate("document.documentElement.lang")
    sec_after = await pg.evaluate("(() => { const s=[...document.querySelectorAll('[data-section]')]; const h=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h'))+20; return s.findIndex(x=>x.getBoundingClientRect().bottom>h); })()")
    if new_lang == lang:
        fail(f"[lang] {tag}: language toggle did not switch")
    if sec_after != sec_before:
        fail(f"[lang-pos] {tag}: reader moved from section {sec_before} to {sec_after}")
    stored = await pg.evaluate("localStorage.getItem('lang')")
    if stored != new_lang:
        fail(f"[lang] {tag}: choice not remembered ({stored})")
    # remembered choice redirects the other language's page
    await pg.goto(BASE + ("en/" if lang == "en" else "") + "impact.html", wait_until="networkidle")
    red = await pg.evaluate("document.documentElement.lang")
    if red != new_lang:
        fail(f"[lang-remember] {tag}: opening {lang} page with {new_lang} saved stayed on {red}")
    await pg.evaluate("localStorage.removeItem('lang')")
    # research diagram: segmented control, nothing jumps
    await pg.goto(url("research", lang), wait_until="networkidle"); await pg.wait_for_timeout(500)
    await pg.evaluate("document.querySelector('.diagram').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(600)
    nxt_top = await pg.evaluate("document.querySelector('.explain').parentElement.nextElementSibling.getBoundingClientRect().top")
    cls0 = await pg.evaluate("window.__cls")
    await pg.locator('.seg-btn[data-mode="sdn"]').tap(); await pg.wait_for_timeout(3600)
    m = await pg.evaluate("document.querySelector('.diagram').dataset.mode")
    if m != "sdn":
        fail(f"[diagram] {tag}: segmented control did not switch ({m})")
    await pg.locator('.seg-btn[data-mode="bgp"]').tap(); await pg.wait_for_timeout(2500)
    nxt_top2 = await pg.evaluate("document.querySelector('.explain').parentElement.nextElementSibling.getBoundingClientRect().top")
    cls1 = await pg.evaluate("window.__cls")
    if abs(nxt_top2 - nxt_top) > 0.5 or cls1 - cls0 > 0.0001:
        fail(f"[jump-diagram] {tag}: section below moved {nxt_top}->{nxt_top2}, cls +{cls1-cls0:.4f}")
    # journey: "show details" opens below the button and the button stays put
    await pg.goto(url("journey", lang), wait_until="networkidle"); await pg.wait_for_timeout(400)
    tg = pg.locator(".ch-toggle").first
    if await tg.count():
        await tg.evaluate("e => e.scrollIntoView({block:'center'})"); await pg.wait_for_timeout(900)
        b0 = await tg.evaluate("e => e.getBoundingClientRect().top")
        await tg.tap(); await pg.wait_for_timeout(800)
        b1 = await tg.evaluate("e => e.getBoundingClientRect().top")
        ex = await tg.get_attribute("aria-expanded")
        hh = await pg.evaluate("document.getElementById(document.querySelector('.ch-toggle').getAttribute('aria-controls')).getBoundingClientRect().height")
        if ex != "true" or hh < 20:
            fail(f"[fold] {tag}: details did not open ({ex}, {hh})")
        if abs(b1 - b0) > 0.5:
            fail(f"[fold-jump] {tag}: the tapped button moved {b0}->{b1}")
    # FAQ opens and closes (allowed to grow)
    await pg.goto(url("contact", lang), wait_until="networkidle"); await pg.wait_for_timeout(400)
    s1 = pg.locator(".faq summary").first
    await s1.scroll_into_view_if_needed(); await pg.wait_for_timeout(700)
    top0 = await s1.evaluate("e => e.getBoundingClientRect().top")
    await s1.tap(); await pg.wait_for_timeout(700)
    op = await pg.evaluate("document.querySelector('.faq').open")
    top1 = await s1.evaluate("e => e.getBoundingClientRect().top")
    await s1.tap(); await pg.wait_for_timeout(700)
    op2 = await pg.evaluate("document.querySelector('.faq').open")
    if not op or op2:
        fail(f"[faq] {tag}: open/close failed ({op},{op2})")
    if abs(top1 - top0) > 0.5:
        fail(f"[faq-jump] {tag}: tapped question moved {top0}->{top1}")
    if errs:
        fail(f"[js-touch] {tag}: {errs[:3]}")
    await ctx.close()

async def jump_checks(browser, page_name, lang, vp):
    """Let auto-rotating things run a full cycle; nothing below may move and CLS stays 0."""
    name, w, h, touch = vp
    ctx = await new_ctx(browser, w, h, touch, "light")
    pg = await ctx.new_page()
    tag = f"{page_name}/{lang}/{name}"
    await pg.goto(url(page_name, lang), wait_until="networkidle")
    await pg.wait_for_timeout(600)
    H = await pg.evaluate("document.documentElement.scrollHeight")
    positions = []
    for frac in (0.0, 0.3, 0.6):
        y = int(H * frac)
        await pg.evaluate(f"window.scrollTo(0,{y})"); await pg.wait_for_timeout(400)
        p0 = await pg.evaluate("[...document.querySelectorAll('[data-section]')].map(s => Math.round(s.getBoundingClientRect().top*10)/10)")
        await pg.wait_for_timeout(5800)
        p1 = await pg.evaluate("[...document.querySelectorAll('[data-section]')].map(s => Math.round(s.getBoundingClientRect().top*10)/10)")
        moved = [(i, a, b) for i, (a, b) in enumerate(zip(p0, p1)) if abs(a - b) > 0.5]
        if moved:
            fail(f"[jump] {tag} @{frac}: sections moved while idle {moved[:3]}")
    cls = await pg.evaluate("window.__cls")
    if cls > 0.0001:
        fail(f"[cls] {tag}: CLS {cls:.4f} {await pg.evaluate('window.__shifts.slice(0,4)')}")
    await ctx.close()

async def sibling_checks(browser, page_name, lang, vp):
    name, w, h, touch = vp
    ctx = await new_ctx(browser, w, h, touch, "light")
    pg = await ctx.new_page()
    tag = f"{page_name}/{lang}/{name}"
    await pg.goto(url(page_name, lang), wait_until="networkidle")
    await pg.add_style_tag(content="*{animation:none!important;transition:none!important}[data-reveal]{opacity:1!important;transform:none!important}.swipe>*{transform:none!important;opacity:1!important}")
    await pg.wait_for_timeout(300)
    res = await pg.evaluate("""() => {
      const out = [];
      const groups = document.querySelectorAll('.grid, .stats, .duo, .pubs, .faqs, .chapters');
      groups.forEach((g, gi) => {
        const kids = [...g.children].filter(k => getComputedStyle(k).display !== 'none');
        const horizontal = getComputedStyle(g).display === 'flex' && getComputedStyle(g).overflowX !== 'visible';
        // rows: group by top (grid) — in swipe rows all are one row
        const rows = {};
        kids.forEach(k => { const r = k.getBoundingClientRect(); const key = horizontal ? 0 : Math.round(r.top); (rows[key] = rows[key] || []).push(k); });
        Object.values(rows).forEach(row => {
          if (row.length < 2) return;
          const rs = row.map(k => k.getBoundingClientRect());
          const hs = rs.map(r => r.height), ts = rs.map(r => r.top);
          if (Math.max(...hs) - Math.min(...hs) > 1) out.push(g.className + ' heights ' + hs.map(Math.round).join(','));
          if (Math.max(...ts) - Math.min(...ts) > 1) out.push(g.className + ' tops ' + ts.map(Math.round).join(','));
          const foots = row.map(k => k.querySelector('.card-foot, .degree-foot')).filter(Boolean);
          if (foots.length === row.length) {
            const bs = foots.map(f => f.getBoundingClientRect().bottom);
            if (Math.max(...bs) - Math.min(...bs) > 1) out.push(g.className + ' footers ' + bs.map(Math.round).join(','));
            const tops = foots.map(f => f.getBoundingClientRect().top);
            if (Math.max(...tops) - Math.min(...tops) > 1) out.push(g.className + ' footer-tops ' + tops.map(Math.round).join(','));
          }
        });
        kids.forEach(k => {
          const kb = k.getBoundingClientRect();
          k.querySelectorAll('*').forEach(c => {
            const cs = getComputedStyle(c);
            if (cs.position === 'absolute' || cs.position === 'fixed') return;
            if (c.closest('.sky') || c.closest('details:not([open])')) return;
            let a = c.parentElement, clipped = false;
            while (a && a !== k) { const s = getComputedStyle(a); if (s.overflow !== 'visible' || s.overflowY !== 'visible') { clipped = true; break; } a = a.parentElement; }
            if (clipped) return;
            const b = c.getBoundingClientRect();
            if (!b.width || !b.height) return;
            if (b.left < kb.left - 1 || b.right > kb.right + 1 || b.top < kb.top - 1 || b.bottom > kb.bottom + 1) out.push('overflow in ' + (k.className||'') + ': ' + (c.className && c.className.baseVal === undefined ? c.className : c.tagName));
          });
        });
      });
      return out.slice(0, 8);
    }""")
    if res:
        fail(f"[siblings] {tag}: {res}")
    await ctx.close()

async def hover_focus_underline(browser, lang):
    ctx = await new_ctx(browser, 1440, 900, False, "light")
    pg = await ctx.new_page()
    await pg.goto(url("index", lang), wait_until="networkidle")
    els = await pg.query_selector_all("a, button")
    bad = []
    for el in els[:80]:
        try:
            if not await el.is_visible():
                continue
            await el.hover(timeout=800)
            td = await el.evaluate("e => getComputedStyle(e).textDecorationLine")
            await el.focus()
            td2 = await el.evaluate("e => getComputedStyle(e).textDecorationLine")
            if td != "none" or td2 != "none":
                bad.append(await el.evaluate("e => e.className || e.tagName"))
        except Exception:
            pass
    if bad:
        fail(f"[underline-hover] {lang}: {bad[:5]}")
    await ctx.close()

async def motion_checks(browser, lang, theme):
    from PIL import Image, ImageChops
    ctx = await new_ctx(browser, 1440, 900, False, theme)
    pg = await ctx.new_page()
    await pg.goto(url("index", lang))
    shots = []
    for i, t in enumerate((150, 1000, 3000)):
        await pg.wait_for_timeout(t - (0 if i == 0 else (150, 1000, 3000)[i - 1]))
        p = f"{SHOTS}/motion-{lang}-{theme}-{t}.png"
        await pg.screenshot(path=p); shots.append(p)
    def diff(a, b):
        A, B = Image.open(a).convert("L"), Image.open(b).convert("L")
        d = ImageChops.difference(A, B)
        return sum(d.histogram()[12:]) / (A.size[0] * A.size[1])
    d01, d12 = diff(shots[0], shots[1]), diff(shots[1], shots[2])
    if d01 < 0.002:
        fail(f"[motion] {lang}/{theme}: entrance animation not visible (diff {d01:.4f})")
    if d12 < 0.0003:
        fail(f"[motion] {lang}/{theme}: nothing moves at rest (diff {d12:.5f})")
    note(f"motion {lang}/{theme}: load→1s {d01:.4f}, 1s→3s {d12:.5f}")
    # at-rest motion continues a few seconds later
    await pg.wait_for_timeout(2000)
    p4 = f"{SHOTS}/motion-{lang}-{theme}-5000.png"; await pg.screenshot(path=p4)
    d23 = diff(shots[2], p4)
    if d23 < 0.0003:
        fail(f"[motion] {lang}/{theme}: background does not keep moving (diff {d23:.5f})")
    # scroll-linked motion at three positions
    H = await pg.evaluate("document.documentElement.scrollHeight")
    prev = None
    for k, frac in enumerate((0.12, 0.4, 0.7)):
        await pg.evaluate(f"window.scrollTo(0,{int(H*frac)})"); await pg.wait_for_timeout(500)
        p = f"{SHOTS}/scroll-{lang}-{theme}-{k}.png"; await pg.screenshot(path=p)
    st = await pg.evaluate("""() => { const h = document.querySelector('[data-hero-out]'); const pr = document.querySelector('.progress'); return [getComputedStyle(h).opacity, getComputedStyle(pr).transform]; }""")
    if st[1] in ("none", "matrix(0, 0, 0, 1, 0, 0)"):
        fail(f"[motion-scroll] {lang}/{theme}: reading progress not moving {st}")
    await ctx.close()

async def reduced_motion(browser, lang):
    ctx = await new_ctx(browser, 390, 844, True, "light", reduced=True)
    pg = await ctx.new_page()
    for page_name in PAGES:
        await pg.goto(url(page_name, lang), wait_until="networkidle")
        H = await pg.evaluate("document.documentElement.scrollHeight")
        y = 0
        hidden = []
        while y < H:
            await pg.evaluate(f"window.scrollTo(0,{y})"); await pg.wait_for_timeout(900)
            hidden += await pg.evaluate("""() => [...document.querySelectorAll('[data-reveal], h1, h2, p')].filter(e => { const r = e.getBoundingClientRect(); if (r.bottom < 80 || r.top > innerHeight - 120 || !r.height) return false; if (e.matches('.dg-cap') && e.closest('.diagram') && e.dataset.mode !== e.closest('.diagram').dataset.mode) return false; return +getComputedStyle(e).opacity < 0.95; }).map(e => (e.className||e.tagName) + ':' + getComputedStyle(e).opacity).slice(0,3)""")
            y += 700
        if hidden:
            fail(f"[reduced] {page_name}/{lang}: content not fully visible with reduced motion: {hidden[:4]}")
    await ctx.close()

def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])

def contrast(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

async def glass_contrast(browser, lang, theme, no_blur=False):
    """Text on glass: composite the glass fill over the darkest/lightest thing that can sit behind it."""
    ctx = await new_ctx(browser, 1440, 900, False, theme)
    pg = await ctx.new_page()
    await pg.goto(url("index", lang), wait_until="networkidle")
    if no_blur:
        await pg.add_style_tag(content="*{-webkit-backdrop-filter:none!important;backdrop-filter:none!important}")
    await pg.evaluate("window.scrollTo(0, 1400)"); await pg.wait_for_timeout(600)
    res = await pg.evaluate("""() => {
      const parse = s => { const m = s.match(/rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [p[0],p[1],p[2], p.length>3?p[3]:1]; };
      const items = [];
      const add = (sel, bgSel) => document.querySelectorAll(sel).forEach(el => {
        const fill = parse(getComputedStyle(el, bgSel || null).backgroundColor) || [0,0,0,0];
        el.querySelectorAll('b, small, span, a, .stat-l, .stat-n, .dock-label').forEach(t => {
          if (!t.textContent.trim()) return;
          const c = parse(getComputedStyle(t).color);
          items.push({sel, text: t.textContent.trim().slice(0,24), fill, color: c, size: parseFloat(getComputedStyle(t).fontSize), weight: +getComputedStyle(t).fontWeight});
        });
      });
      add('.badge'); add('.stat'); add('.dock'); add('.bar', '::before'); add('.btn-glass');
      return items;
    }""")
    worst = []
    behinds = [(27, 26, 46), (255, 255, 255), (246, 242, 234)]  # night, white portrait, ivory page
    for it in res:
        f = it["fill"]
        if not it["color"]:
            continue
        for bg in behinds:
            if it["sel"] in (".stat",) and bg != behinds[0]:
                continue
            a = f[3]
            comp = tuple(f[i] * a + bg[i] * (1 - a) for i in range(3))
            col = it["color"]
            ca = col[3] if len(col) > 3 else 1
            colc = tuple(col[i] * ca + comp[i] * (1 - ca) for i in range(3))
            cr = contrast(colc, comp)
            large = it["size"] >= 24 or (it["size"] >= 18.66 and it["weight"] >= 700)
            need = 3 if large else 4.5
            if cr < need:
                worst.append(f"{it['sel']} '{it['text']}' {cr:.2f} over {bg}")
    if worst:
        fail(f"[glass-contrast] {lang}/{theme}{'/no-blur' if no_blur else ''}: {worst[:5]}")
    await ctx.close()

async def smoothness(browser, lang):
    ctx = await new_ctx(browser, 390, 844, True, "light")
    pg = await ctx.new_page()
    cdp = await ctx.new_cdp_session(pg)
    await pg.goto(url("index", lang), wait_until="networkidle")
    await pg.wait_for_timeout(1200)
    await cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    res = await pg.evaluate("""async () => {
      const H = document.documentElement.scrollHeight - innerHeight;
      const times = []; let last = performance.now(); let y = 0;
      await new Promise(done => {
        const step = now => { times.push(now - last); last = now; y += 14; window.scrollTo(0, y); if (y < H) requestAnimationFrame(step); else done(); };
        requestAnimationFrame(step);
      });
      times.shift();
      const sorted = [...times].sort((a,b)=>a-b);
      const avg = times.reduce((a,b)=>a+b,0)/times.length;
      return {frames: times.length, avg, p95: sorted[Math.floor(sorted.length*0.95)], over50: times.filter(t=>t>50).length};
    }""")
    await cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
    fps = 1000 / res["avg"]
    note(f"smoothness {lang} (390px touch, 4x CPU): {fps:.0f} fps avg, p95 {res['p95']:.1f} ms, {res['over50']} frames >50ms of {res['frames']}")
    if fps < 45:
        fail(f"[smooth] {lang}: average {fps:.0f} fps under 4x CPU throttling")
    await ctx.close()

async def main():
    t0 = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        sem = asyncio.Semaphore(6)
        jobs = [basic_checks(browser, pg_, lg, vp, th, sem) for pg_ in PAGES for lg in LANGS for vp in VIEWPORTS for th in THEMES]
        await asyncio.gather(*jobs)
        print(f"basic checks done ({len(jobs)} loads) {time.time()-t0:.0f}s", flush=True)
        await asyncio.gather(*[axe_check(browser, pg_, lg, th, w, h, sem) for pg_ in PAGES for lg in LANGS for th in THEMES for (w, h) in ((390, 844), (1440, 900))])
        print(f"axe done {time.time()-t0:.0f}s", flush=True)
        await asyncio.gather(*[sibling_checks(browser, pg_, lg, vp) for pg_ in PAGES for lg in LANGS for vp in VIEWPORTS if vp[0] in ("p390", "t768", "d1024", "d1440")])
        print(f"siblings done {time.time()-t0:.0f}s", flush=True)
        await asyncio.gather(*[interaction_checks(browser, lg) for lg in LANGS])
        print(f"interactions done {time.time()-t0:.0f}s", flush=True)
        jsem = asyncio.Semaphore(2)
        async def jc(*a):
            async with jsem:
                await jump_checks(browser, *a)
        await asyncio.gather(*[jc(pg_, lg, vp) for pg_ in PAGES for lg in LANGS for vp in VIEWPORTS if vp[0] in ("p390", "d1440")])
        print(f"jump checks done {time.time()-t0:.0f}s", flush=True)
        await asyncio.gather(*[hover_focus_underline(browser, lg) for lg in LANGS])
        await asyncio.gather(*[motion_checks(browser, lg, th) for lg in LANGS for th in THEMES])
        await asyncio.gather(*[reduced_motion(browser, lg) for lg in LANGS])
        await asyncio.gather(*[glass_contrast(browser, lg, th, nb) for lg in LANGS for th in THEMES for nb in (False, True)])
        for lg in LANGS:
            await smoothness(browser, lg)
        await browser.close()
    print("\n".join("NOTE " + n for n in NOTES))
    print(f"\n{len(FAIL)} problem(s) in {time.time()-t0:.0f}s")
    for f in FAIL:
        print(" -", f)
    sys.exit(1 if FAIL else 0)

asyncio.run(main())
