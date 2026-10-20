#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dr. Hamad Al-Thiapi — personal site generator.

    python3 build.py            → writes the finished static site into ./docs
    (GitHub Pages serves ./docs from the main branch)

All texts live in content.py (Arabic + English together).
Everything you may want to change quickly is in CONFIG below.
"""
import html, json, math, os, random, re, shutil
from datetime import date
import content as C
from icons import ICONS as LUCIDE

# ============================================================== CONFIG
CONFIG = {
    # Live address of the site (used for canonical links, sitemap, Open Graph).
    "BASE_URL": "https://nouraldeentofi.github.io/hamad-al-thiapi/",
    # Portrait (inside src/assets/img). Leave "" to show a monogram instead.
    "PHOTO": "portrait.webp",
    "PHOTO_SMALL": "portrait-360.webp",
    # Contact — anything left empty stays hidden on the site.
    "EMAIL": "",        # e.g. "name@example.com"  (add after Dr. Hamad approves)
    "PHONE": "",        # e.g. "+966500000000"
    "WHATSAPP": "",     # digits only, e.g. "966500000000"
    "LINKEDIN": "https://www.linkedin.com/in/dr-hamad-al-thiapi/",
    # Maker credit in the footer.
    "MAKER": "https://nouraldeentofi.com",
    # PREVIEW = True → noindex + robots.txt blocks crawlers. Set False once he approves.
    "PREVIEW": True,
    # Custom domain later, e.g. "hamad-althiapi.com" (writes docs/CNAME). Also change BASE_URL.
    "DOMAIN": "",
}

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "docs")
YEAR = date.today().year
LANGS = ("ar", "en")
PAGES = ["index", "journey", "impact", "research", "contact"]

# ============================================================== helpers
def esc(s):
    return html.escape(str(s), quote=True)

def L(d, lang):
    if isinstance(d, dict):
        return d.get(lang, "")
    return d

_TOK = r"[A-Za-z0-9](?:[A-Za-z0-9@.,:%+&/'’\-–]*[A-Za-z0-9%])?"
_RUN = re.compile(_TOK + r"(?:\s+" + _TOK + r")*")

def bidi(s, lang):
    """Escape text; in Arabic wrap Latin words and numbers in dir=ltr spans."""
    s = str(s)
    if lang != "ar":
        return esc(s)
    out, last = [], 0
    for m in _RUN.finditer(s):
        out.append(esc(s[last:m.start()]))
        run = m.group(0)
        nw = ' class="nw"' if (" " not in run and re.search(r"[-–]", run)) else ""
        out.append('<span dir="ltr"%s>%s</span>' % (nw, esc(run)))
        last = m.end()
    out.append(esc(s[last:]))
    return "".join(out)

def T(d, lang):
    return bidi(L(d, lang), lang)

def ltr(s):
    return '<span dir="ltr">%s</span>' % esc(s)

def attrs(**kw):
    return "".join(' %s="%s"' % (k.rstrip("_").replace("_", "-"), esc(v)) for k, v in kw.items() if v is not None)

# ---------------------------------------------------------------- icons
_icon_cache = {}
CUSTOM_ICONS = {
    "linkedin": '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="M8 10.5V17"/><path d="M8 7.2v.01"/><path d="M12 17v-6.5"/><path d="M12 13.4a2.6 2.6 0 0 1 5 0V17"/>',
    "whatsapp": '<path d="M3.5 20.5l1.3-4.2A8.5 8.5 0 1 1 8 19.6z"/><path d="M9 8.6c.2 2.9 2.6 5.6 5.9 6.3l1.2-1.3-1.9-1-0.9.8c-1-.4-2.1-1.5-2.6-2.6l.8-.9-1-1.9z"/>',
}

def icon(name, cls="ic"):
    if name not in _icon_cache:
        inner = CUSTOM_ICONS.get(name) or LUCIDE[name]
        _icon_cache[name] = inner
    return ('<svg class="%s" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">%s</svg>') % (cls, _icon_cache[name])

# ---------------------------------------------------------------- urls
def page_file(slug):
    return "index.html" if slug == "index" else slug + ".html"

def rel(slug, lang, from_lang, anchor=""):
    """Relative link from a page in from_lang to slug in lang."""
    f = "./" if slug == "index" else page_file(slug)
    if lang == from_lang:
        p = f
    elif from_lang == "ar":            # ar (root) → en/
        p = "en/" + ("" if slug == "index" else f)
    else:                              # en/ → root
        p = "../" + ("" if slug == "index" else f)
    return p + (("#" + anchor) if anchor else "")

def abs_url(slug, lang):
    base = CONFIG["BASE_URL"]
    f = "" if slug == "index" else page_file(slug)
    return base + ("en/" if lang == "en" else "") + f

def asset(lang, path):
    return ("../" if lang == "en" else "") + "assets/" + path

def link_href(href, lang):
    """content hrefs like 'impact#ai' → relative link inside the same language."""
    slug, _, anchor = href.partition("#")
    return rel(slug, lang, lang, anchor)

# ============================================================== SVG scenes
def rng(seed):
    r = random.Random(seed)
    return r

def f1(x):
    return ("%.1f" % x).rstrip("0").rstrip(".")

def curve(x1, y1, x2, y2, bend=0.18):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    cx, cy = mx - dy * bend, my + dx * bend
    return "M%s %sQ%s %s %s %s" % (f1(x1), f1(y1), f1(cx), f1(cy), f1(x2), f1(y2))

def sky_converge(seed=7, inner=207, count=13):
    """Routes from points across a field, all turning the same way as they converge on the centre (the medallion)."""
    r = rng(seed)
    routes, nodes = [], []
    for i in range(count):
        a = (i / count) * math.tau + r.uniform(-0.1, 0.1)
        rad = (300, 455, 380, 470, 330)[i % 5] + r.uniform(-18, 18)
        x, y = 500 + rad * math.cos(a), 500 + rad * math.sin(a)
        ea = a + 0.5
        ex, ey = 500 + inner * math.cos(ea), 500 + inner * math.sin(ea)
        routes.append('<path class="route" pathLength="1" style="--i:%d" d="%s" data-packets="1" data-speed="%s"/>'
                      % (i, curve(x, y, ex, ey, 0.2), f1(r.uniform(7, 10.5))))
        nodes.append('<circle class="node" cx="%s" cy="%s" r="%s" style="--tw:%sms"/>'
                     % (f1(x), f1(y), f1(r.uniform(3, 4.4)), int(r.uniform(0, 4200))))
    stars = []
    for i in range(40):
        a = r.uniform(0, math.tau); rad = r.uniform(230, 520)
        stars.append('<circle class="star" cx="%s" cy="%s" r="%s" style="--tw:%sms"/>'
                     % (f1(500 + rad * math.cos(a)), f1(500 + rad * math.sin(a)), f1(r.uniform(0.8, 1.6)), int(r.uniform(0, 6000))))
    rings = "".join('<circle class="orbit-line" cx="500" cy="500" r="%d"/>' % rr for rr in (262, 338, 420))
    return ('<svg class="sky-svg" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">'
            '<g class="rings">%s</g><g class="stars">%s</g><g class="routes">%s</g><g class="nodes">%s</g><g class="packets"></g></svg>'
            % (rings, "".join(stars), "".join(routes), "".join(nodes)))

# Saudi regional capitals (approximate lat/lon) — the network that linked every region to Riyadh.
KSA = [
    ("Makkah", 21.39, 39.86), ("Madinah", 24.47, 39.61), ("Dammam", 26.43, 50.10), ("Buraidah", 26.33, 43.97),
    ("Hail", 27.52, 41.69), ("Tabuk", 28.38, 36.57), ("Sakaka", 29.97, 40.21), ("Arar", 30.98, 41.04),
    ("Abha", 18.22, 42.50), ("Jazan", 16.89, 42.55), ("Najran", 17.49, 44.13), ("Al-Baha", 20.01, 41.47),
    ("Jeddah", 21.49, 39.19), ("Al-Ahsa", 25.38, 49.59),
]
RIYADH = (24.71, 46.68)

def sky_kingdom(rtl=False, cy=480, k=30, seed=3):
    cx = 330 if rtl else 670
    r = rng(seed)
    def xy(lat, lon):
        return cx + (lon - RIYADH[1]) * k, cy - (lat - RIYADH[0]) * k
    hx, hy = xy(*RIYADH)
    grat = []
    for lon in range(34, 56, 2):
        x = cx + (lon - RIYADH[1]) * k
        grat.append('<line x1="%s" y1="0" x2="%s" y2="1000"/>' % (f1(x), f1(x)))
    for lat in range(14, 34, 2):
        y = cy - (lat - RIYADH[0]) * k
        grat.append('<line x1="0" y1="%s" x2="1000" y2="%s"/>' % (f1(y), f1(y)))
    routes, nodes = [], []
    for i, (name, lat, lon) in enumerate(KSA):
        x, y = xy(lat, lon)
        routes.append('<path class="route" pathLength="1" style="--i:%d" d="%s" data-packets="1" data-speed="%s"/>'
                      % (i, curve(x, y, hx, hy, 0.14 if i % 2 else -0.14), f1(r.uniform(6, 10))))
        nodes.append('<circle class="node" cx="%s" cy="%s" r="3.4" style="--tw:%sms"/>' % (f1(x), f1(y), int(r.uniform(0, 4000))))
    hub = ('<circle class="hub-halo" cx="%s" cy="%s" r="26"/><circle class="hub" cx="%s" cy="%s" r="6.5"/>'
           % (f1(hx), f1(hy), f1(hx), f1(hy)))
    return ('<svg class="sky-svg" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">'
            '<g class="grat">%s</g><g class="routes">%s</g><g class="nodes">%s</g>%s<g class="packets"></g></svg>'
            % ("".join(grat), "".join(routes), "".join(nodes), hub))

def sky_world(rtl=False):
    W, H = 1600, 800
    def xy(lat, lon):
        return (lon + 180) / 360 * W, (90 - lat) / 180 * H
    ry = xy(24.71, 46.68)
    places = {"bridgeport": xy(41.18, -73.19), "melbourne": xy(-37.81, 144.96), "singapore": xy(1.35, 103.82)}
    grat = []
    for lon in range(-180, 181, 30):
        x = (lon + 180) / 360 * W
        grat.append('<line x1="%s" y1="0" x2="%s" y2="%d"/>' % (f1(x), f1(x), H))
    for lat in range(-60, 91, 30):
        y = (90 - lat) / 180 * H
        grat.append('<line x1="0" y1="%s" x2="%d" y2="%s"/>' % (f1(y), W, f1(y)))
    def arc(a, b, lift):
        (x1, y1), (x2, y2) = a, b
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - lift
        return "M%s %sQ%s %s %s %s" % (f1(x1), f1(y1), f1(mx), f1(my), f1(x2), f1(y2))
    routes = []
    i = 0
    for key, lift_out, lift_back in (("bridgeport", 230, 170), ("melbourne", 150, 100)):
        p = places[key]
        routes.append('<path class="route" pathLength="1" style="--i:%d" d="%s" data-packets="1" data-speed="5"/>' % (i, arc(ry, p, lift_out))); i += 1
        routes.append('<path class="route route--back" pathLength="1" style="--i:%d" d="%s" data-packets="1" data-speed="5"/>' % (i, arc(p, ry, lift_back))); i += 1
    routes.append('<path class="route route--soft" pathLength="1" style="--i:%d" d="%s" data-packets="1" data-speed="6"/>' % (i, arc(ry, places["singapore"], 80)))
    nodes = "".join('<circle class="node node--big" cx="%s" cy="%s" r="5"/>' % (f1(x), f1(y)) for (x, y) in places.values())
    hub = ('<circle class="hub-halo" cx="%s" cy="%s" r="30"/><circle class="hub" cx="%s" cy="%s" r="7"/>'
           % (f1(ry[0]), f1(ry[1]), f1(ry[0]), f1(ry[1])))
    return ('<svg class="sky-svg" viewBox="380 -10 1180 660" preserveAspectRatio="PAR" aria-hidden="true" focusable="false">'
            '<g class="grat">%s</g><g class="routes">%s</g><g class="nodes">%s</g>%s<g class="packets"></g></svg>'
            % ("".join(grat), "".join(routes), nodes, hub)).replace("PAR", "xMinYMid meet" if rtl else "xMaxYMid meet")

def sky_domains(rtl=False, seed=11):
    r = rng(seed)
    clusters = [(620, 300, 92), (820, 190, 70), (860, 470, 84), (700, 640, 70), (480, 560, 64), (930, 720, 60)]
    if rtl:
        clusters = [(1000 - x, y, rad) for (x, y, rad) in clusters]
    nodes, links, routes = [], [], []
    pts = []
    for (cx, cy, rad) in clusters:
        nodes.append('<circle class="domain" cx="%d" cy="%d" r="%d"/>' % (cx, cy, rad))
        cp = []
        for j in range(4):
            a = r.uniform(0, math.tau); d = r.uniform(rad * 0.25, rad * 0.75)
            if rtl: a = math.pi - a
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            cp.append((x, y))
            nodes.append('<circle class="node" cx="%s" cy="%s" r="3" style="--tw:%sms"/>' % (f1(x), f1(y), int(r.uniform(0, 4000))))
        for j in range(len(cp) - 1):
            links.append('<line class="intra" x1="%s" y1="%s" x2="%s" y2="%s"/>' % (f1(cp[j][0]), f1(cp[j][1]), f1(cp[j + 1][0]), f1(cp[j + 1][1])))
        pts.append(cp)
    pairs = [(0, 1), (0, 2), (1, 2), (2, 3), (0, 4), (4, 3), (2, 5), (3, 5)]
    for i, (a, b) in enumerate(pairs):
        p, q = pts[a][0], pts[b][1]
        routes.append('<path class="route" pathLength="1" style="--i:%d" d="%s" data-packets="1" data-speed="%s"/>'
                      % (i, curve(p[0], p[1], q[0], q[1], 0.1), f1(r.uniform(7, 11))))
    return ('<svg class="sky-svg" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">'
            '<g class="domains">%s</g><g class="intra-links">%s</g><g class="routes">%s</g><g class="packets"></g></svg>'
            % ("".join(nodes), "".join(links), "".join(routes)))

def sky_calm(rtl=False, seed=5):
    r = rng(seed)
    hx, hy = 500, 500
    routes, nodes = [], []
    for i in range(10):
        a = math.tau * i / 10 + r.uniform(-0.12, 0.12)
        rad = r.uniform(260, 470)
        x, y = hx + rad * math.cos(a), hy + rad * math.sin(a)
        routes.append('<path class="route" pathLength="1" style="--i:%d" d="%s" data-packets="1" data-speed="%s"/>'
                      % (i, curve(x, y, hx, hy, 0.12 if i % 2 else -0.12), f1(r.uniform(6, 9))))
        nodes.append('<circle class="node" cx="%s" cy="%s" r="3.2" style="--tw:%sms"/>' % (f1(x), f1(y), int(r.uniform(0, 4000))))
    hub = '<circle class="hub-halo" cx="%d" cy="%d" r="22"/><circle class="hub" cx="%d" cy="%d" r="6.5"/>' % (hx, hy, hx, hy)
    return ('<svg class="sky-svg" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">'
            '<g class="routes">%s</g><g class="nodes">%s</g>%s<g class="packets"></g></svg>'
            % ("".join(routes), "".join(nodes), hub))

def sky_trace(rtl=False, seed=21):
    """Faint flowing routes for light sections."""
    r = rng(seed)
    routes, nodes = [], []
    for i in range(4):
        y0 = 180 + i * 190 + r.uniform(-40, 40)
        y1 = y0 + r.uniform(-120, 120)
        c1 = (330, y0 + r.uniform(-160, 160)); c2 = (670, y1 + r.uniform(-160, 160))
        x0, x1 = (-20, 1020) if (i % 2 == 0) != rtl else (1020, -20)
        if x0 > x1:
            c1, c2 = (1000 - c1[0], c1[1]), (1000 - c2[0], c2[1])
        d = "M%s %sC%s %s %s %s %s %s" % (f1(x0), f1(y0), f1(c1[0]), f1(c1[1]), f1(c2[0]), f1(c2[1]), f1(x1), f1(y1))
        routes.append('<path class="route" pathLength="1" style="--i:%d" d="%s" data-packets="1" data-speed="%s"/>' % (i, d, f1(r.uniform(3.2, 4.6))))
    return ('<svg class="sky-svg" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true" focusable="false">'
            '<g class="routes">%s</g><g class="packets"></g></svg>' % "".join(routes))

SKIES = {"kingdom": sky_kingdom, "world": sky_world, "domains": sky_domains, "calm": sky_calm, "trace": sky_trace}

def sky(scene, extra="", lang="ar", seed=None):
    pulses = ""
    if scene == "calm":
        pulses = '<span class="pulse" style="--p:0"></span><span class="pulse" style="--p:1"></span><span class="pulse" style="--p:2"></span>'
    kw = {"rtl": lang == "ar"}
    if seed is not None:
        kw["seed"] = seed
    return '<div class="sky sky--%s %s" aria-hidden="true">%s%s</div>' % (scene, extra, SKIES[scene](**kw), pulses)

# ---------------------------------------------------------------- research diagram
DIAG = {
    "S": (54, 200), "T": (586, 200),
    "A1": (150, 166), "A2": (150, 236), "B1": (268, 120), "B2": (372, 120), "B3": (320, 156),
    "C1": (490, 166), "C2": (490, 236), "D1": (268, 280), "D2": (372, 280), "D3": (320, 244),
    "K": (320, 34),
}
DOMAINS = [("A", 112, 200, 70), ("B", 320, 118, 62), ("C", 528, 200, 70), ("D", 320, 282, 62)]
LINKS = [("A1", "B1", "ab"), ("B2", "C1", "bc"), ("A2", "D1", "ad"), ("D2", "C2", "dc"), ("B3", "D3", "bd")]
INTRA = [("S", "A1"), ("S", "A2"), ("A1", "A2"), ("B1", "B2"), ("B1", "B3"), ("B2", "B3"), ("D1", "D2"), ("D1", "D3"), ("D2", "D3"),
         ("C1", "C2"), ("C1", "T"), ("C2", "T")]
PATHS = {
    "old":   ["S", "A1", "B1", "B2", "C1", "T"],
    "trial": ["S", "A1", "B1", "B3", "D3", "D2", "C2", "T"],
    "new":   ["S", "A2", "D1", "D2", "C2", "T"],
}
CTRL = ["A1", "A2", "B2", "D1", "D2", "C2"]

def poly_d(names):
    pts = [DIAG[n] for n in names]
    return "M" + " L".join("%d %d" % p for p in pts)

def diagram(lang, compact=False):
    d = C.RESEARCH["diagram"]
    parts = []
    for (name, x, y, rad) in DOMAINS:
        parts.append('<circle class="dg-domain" cx="%d" cy="%d" r="%d"/>' % (x, y, rad))
    for (a, b) in INTRA:
        (x1, y1), (x2, y2) = DIAG[a], DIAG[b]
        parts.append('<line class="dg-intra" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (x1, y1, x2, y2))
    for n in CTRL:
        (x1, y1), (x2, y2) = DIAG["K"], DIAG[n]
        parts.append('<line class="dg-ctrl" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (x1, y1, x2, y2))
    for (a, b, key) in LINKS:
        (x1, y1), (x2, y2) = DIAG[a], DIAG[b]
        parts.append('<line class="dg-link dg-link--%s" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (key, x1, y1, x2, y2))
    bx, by = (DIAG["B2"][0] + DIAG["C1"][0]) / 2, (DIAG["B2"][1] + DIAG["C1"][1]) / 2
    parts.append('<g class="dg-break" transform="translate(%s %s)"><circle r="11"/><path d="M-4.5 -4.5L4.5 4.5M4.5 -4.5L-4.5 4.5"/></g>' % (f1(bx), f1(by)))
    for key in ("old", "trial", "new"):
        parts.append('<path class="dg-path dg-path--%s" pathLength="1" d="%s"/>' % (key, poly_d(PATHS[key])))
    for n, (x, y) in DIAG.items():
        if n in ("S", "T"):
            parts.append('<g class="dg-host" data-n="%s" transform="translate(%d %d)"><rect x="-13" y="-10" width="26" height="20" rx="5"/><path d="M-6 -2h12M-6 3h8"/></g>' % (n, x, y))
        elif n == "K":
            parts.append('<g class="dg-ctrlnode" data-n="K" transform="translate(%d %d)"><path d="M0 -19L16.5 -9.5V9.5L0 19L-16.5 9.5V-9.5Z"/><text y="4.5" text-anchor="middle">SDN</text></g>' % (x, y))
        else:
            parts.append('<circle class="dg-router" data-n="%s" cx="%d" cy="%d" r="7.5"/>' % (n, x, y))
    lab = []
    sx, sy = DIAG["S"]; tx, ty = DIAG["T"]
    lab.append('<text class="dg-label" x="%d" y="%d" text-anchor="middle">%s</text>' % (sx + 4, sy + 34, esc(L(d["src"], lang))))
    lab.append('<text class="dg-label" x="%d" y="%d" text-anchor="middle">%s</text>' % (tx - 4, ty + 34, esc(L(d["dst"], lang))))
    svg = ('<svg class="dg-svg" viewBox="0 0 640 340" role="img" aria-label="%s" focusable="false">%s%s<g class="dg-pulses"></g><g class="dg-packets"></g></svg>'
           % (esc(L(d["aria"], lang)), "".join(parts), "".join(lab)))
    modes = C.RESEARCH["modes"]
    timebar = ('<div class="dg-time"><span class="dg-time-label">%s</span><span class="dg-time-track"><span class="dg-time-fill"></span></span></div>'
               % T(d["time"], lang))
    if compact:
        caps = "".join('<p class="dg-cap" data-mode="%s">%s</p>' % (m["key"], '<b>%s</b> · %s' % (T(m["label"], lang), T(m["cap"], lang))) for m in modes)
        return ('<div class="diagram diagram--compact" data-diagram data-auto="1">%s%s<div class="dg-caps">%s</div></div>'
                % (svg, timebar, caps))
    seg = "".join('<button type="button" class="seg-btn" data-mode="%s" aria-pressed="%s">%s</button>'
                  % (m["key"], "true" if i == 0 else "false", T(m["label"], lang)) for i, m in enumerate(modes))
    caps = "".join('<p class="dg-cap" data-mode="%s">%s</p>' % (m["key"], T(m["cap"], lang)) for m in modes)
    return ('<div class="diagram" data-diagram data-auto="1">'
            '<div class="seg" role="group" aria-label="%s"><span class="seg-ind" aria-hidden="true"></span>%s</div>'
            '<div class="dg-stage">%s</div>%s<div class="dg-caps">%s</div><p class="dg-note">%s</p></div>'
            % (esc(L(C.RESEARCH["explain_h"], lang)), seg, svg, timebar, caps, T(C.UI["simplified"], lang)))

# ============================================================== components
def brand_mark(lang, size=40):
    if CONFIG["PHOTO_SMALL"] or CONFIG["PHOTO"]:
        src = asset(lang, "img/" + (CONFIG["PHOTO_SMALL"] or CONFIG["PHOTO"]))
        return '<span class="mark"><img src="%s" width="%d" height="%d" alt="" decoding="async"></span>' % (src, size, size)
    return '<span class="mark mark--mono" aria-hidden="true">%s</span>' % esc(L(C.PERSON["monogram"], lang))

def header(lang, slug):
    other = "en" if lang == "ar" else "ar"
    nav = "".join('<a class="nav-link" href="%s"%s>%s</a>'
                  % (rel(s, lang, lang), ' aria-current="page"' if s == slug else "", T(label, lang))
                  for (s, label, _ic) in C.NAV)
    return f'''<header class="site-header" data-header>
  <div class="bar">
    <a class="brand" href="{rel('index', lang, lang)}">
      {brand_mark(lang)}
      <span class="brand-text"><span class="brand-name">{T(C.PERSON['name'], lang)}</span><span class="brand-role">{T(C.PERSON['role'], lang)}</span></span>
    </a>
    <nav class="nav" aria-label="{esc(L(C.UI['menu_label'], lang))}">{nav}</nav>
    <div class="tools">
      <a class="tool tool--lang" href="{rel(slug, other, lang)}" hreflang="{other}" lang="{other}" data-lang-switch="{other}">{icon('languages')}<span class="lang-l">{esc(L(C.UI['lang_switch'], lang))}</span><span class="lang-s">{'EN' if lang == 'ar' else 'عربي'}</span></a>
      <button class="tool tool--theme" type="button" data-theme-toggle aria-label="{esc(L(C.UI['theme_label'], lang))}" aria-pressed="false">{icon('moon', 'ic ic-moon')}{icon('sun', 'ic ic-sun')}</button>
    </div>
  </div>
</header>'''

def dock(lang, slug):
    items = []
    for (s, label, ic) in C.NAV:
        cur = s == slug
        items.append('<a class="dock-item" href="%s"%s>%s%s<span class="dock-label">%s</span></a>'
                     % (rel(s, lang, lang), ' aria-current="page"' if cur else "",
                        '<span class="dock-pill" aria-hidden="true"></span>' if cur else "", icon(ic), T(label, lang)))
    return '<nav class="dock" aria-label="%s">%s</nav>' % (esc(L(C.UI["dock_label"], lang)), "".join(items))

def contact_items(lang):
    """[(kind, icon, label, value_html, href)] — only filled values."""
    items = []
    if CONFIG["LINKEDIN"]:
        items.append(("linkedin", "linkedin", L(C.UI["linkedin"], lang), T(C.UI["linkedin_cta"], lang), CONFIG["LINKEDIN"]))
    if CONFIG["EMAIL"]:
        items.append(("email", "mail", L(C.UI["email"], lang), ltr(CONFIG["EMAIL"]), "mailto:" + CONFIG["EMAIL"]))
    if CONFIG["PHONE"]:
        items.append(("phone", "phone", L(C.UI["phone"], lang), ltr(CONFIG["PHONE"]), "tel:" + CONFIG["PHONE"].replace(" ", "")))
    if CONFIG["WHATSAPP"]:
        items.append(("whatsapp", "whatsapp", "WhatsApp", ltr("+" + CONFIG["WHATSAPP"]), "https://wa.me/" + CONFIG["WHATSAPP"]))
    return items

def contact_card(kind, ic, label, value, href, cls="ccard"):
    ext = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
    return ('<a class="%s %s--%s" href="%s"%s><span class="ccard-ic">%s</span><span class="ccard-text"><span class="ccard-label">%s</span>'
            '<span class="ccard-value">%s</span></span>%s</a>'
            % (cls, cls, kind, esc(href), ext, icon(ic), esc(label), value, icon("arrow-up-right", "ic ccard-go")))

def footer(lang, slug):
    links = "".join('<a class="f-link" href="%s">%s</a>' % (rel(s, lang, lang), T(label, lang)) for (s, label, _i) in C.NAV)
    contact = ""
    if slug != "contact":
        cards = "".join(contact_card(*c, cls="fcard") for c in contact_items(lang))
        contact = '<div class="f-col f-contact"><h2 class="f-h">%s</h2>%s</div>' % (T(C.UI["contact"], lang), cards)
    maker = CONFIG["MAKER"]
    return f'''<div class="parapet parapet--night" aria-hidden="true"></div>
<footer class="site-footer">
  {sky('kingdom', 'sky--footer', lang)}
  <div class="wrap f-grid">
    <div class="f-col f-id">
      <a class="f-brand" href="{rel('index', lang, lang)}">{brand_mark(lang, 52)}<span><span class="f-name">{T(C.PERSON['name'], lang)}</span><span class="f-role">{T(C.PERSON['role'], lang)}</span></span></a>
      <p class="f-city">{icon('map-pin')}<span>{T(C.UI['footer_note'], lang)}</span></p>
    </div>
    <nav class="f-col f-nav" aria-label="{esc(L(C.UI['pages'], lang))}"><h2 class="f-h">{T(C.UI['pages'], lang)}</h2><div class="f-links">{links}</div></nav>
    {contact}
  </div>
  <div class="wrap f-bottom">
    <p class="maker"><span lang="ar" dir="rtl"><a href="{maker}" target="_blank" rel="noopener">{esc(C.UI['maker_ar'])}</a></span> <span class="dot" aria-hidden="true">·</span> <span lang="en" dir="ltr"><a href="{maker}" target="_blank" rel="noopener">{esc(C.UI['maker_en'])}</a></span></p>
    <p class="copy"><span dir="ltr">© {YEAR}</span> {T(C.PERSON['name'], lang)}</p>
  </div>
</footer>'''

def name_html(lang):
    if lang == "en":
        return 'Dr. Hamad <span class="nw">Al-Thiapi</span>'
    return T(C.PERSON["name"], lang)

def page_hero(lang, scene, h1, lead, extra=""):
    return f'''<section class="phero" data-section>
  {sky(scene, '', lang)}
  <div class="wrap phero-inner" data-hero-out>
    <h1 class="phero-title page-title" data-enter style="--d:80ms">{T(h1, lang)}</h1>
    <p class="phero-lead" data-enter style="--d:200ms">{T(lead, lang)}</p>
    {extra}
  </div>
  <div class="parapet" aria-hidden="true"></div>
</section>'''

def sec_head(lang, h, lead=None, tag="h2", cls=""):
    lead_html = '<p class="sec-lead" data-reveal>%s</p>' % T(lead, lang) if lead else ""
    return '<div class="sec-head %s"><%s class="sec-title" data-reveal data-slide>%s</%s>%s</div>' % (cls, tag, T(h, lang), tag, lead_html)

def dots(n):
    return '<div class="dots" aria-hidden="true">%s</div>' % "".join('<i></i>' for _ in range(n))

def next_link(lang, slug, label):
    return ('<div class="wrap next"><a class="next-link" href="%s" data-reveal><span>%s</span>%s</a></div>'
            % (rel(slug, lang, lang), T(label, lang), icon("arrow-left" if lang == "ar" else "arrow-right", "ic next-ic")))

def fwd(lang):
    return icon("arrow-left" if lang == "ar" else "arrow-right", "ic fwd")

# ============================================================== pages
def home(lang):
    H = C.HOME
    photo = CONFIG["PHOTO"]
    portrait = ('<img src="%s" width="720" height="720" alt="%s" fetchpriority="high" decoding="async">' % (asset(lang, "img/" + photo), esc(L(C.PERSON["portrait_alt"], lang)))
                if photo else '<span class="mono" aria-hidden="true">%s</span>' % esc(L(C.PERSON["monogram"], lang)))
    meta = "".join('<li>%s<span>%s</span></li>' % (icon(ic), T(m, lang)) for m, ic in zip(H["hero_meta"], ("landmark", "graduation-cap")))
    stats = "".join(
        '<div class="stat glass-dark" data-reveal style="--i:%d"><span class="stat-n" dir="ltr"><span class="count" data-count="%d">%s</span>%s</span><span class="stat-l">%s</span></div>'
        % (i, s["n"], "{:,}".format(s["n"]), esc(s.get("suffix", "")), T(s["label"], lang)) for i, s in enumerate(H["stats"]))
    pillars = "".join(
        '<a class="card card--link pillar" href="%s" data-reveal style="--i:%d"><span class="tile">%s</span><h3 class="card-h">%s</h3><p class="card-p">%s</p><span class="card-foot">%s%s</span></a>'
        % (link_href(p["href"], lang), i, icon(p["icon"]), T(p["h"], lang), T(p["p"], lang), T(C.UI["read_more"], lang), fwd(lang)) for i, p in enumerate(H["pillars"]))
    think = "".join(
        '<article class="card thought" data-reveal style="--i:%d"><span class="thought-n" dir="ltr">0%d</span><h3 class="card-h">%s</h3><p class="card-p">%s</p></article>'
        % (i, i + 1, T(x["h"], lang), T(x["p"], lang)) for i, x in enumerate(H["think"]))
    honors = "".join(
        '<article class="card honor" data-reveal style="--i:%d"><div class="honor-top"><span class="tile tile--gold">%s</span><span class="honor-y" dir="ltr">%s</span></div><h3 class="card-h">%s</h3><p class="card-p">%s</p></article>'
        % (i, icon(h["icon"]), esc(h["y"]), T(h["h"], lang), T(h["p"], lang)) for i, h in enumerate(H["honors"]))
    return f'''
<section class="hero" data-section>
  <div class="hero-glow" aria-hidden="true"></div>
  <div class="wrap hero-grid">
    <div class="hero-copy" data-hero-out>
      <h1 class="hero-name page-title" data-enter style="--d:120ms">{name_html(lang)}</h1>
      <p class="hero-role" data-enter style="--d:220ms">{T(C.PERSON['role'], lang)}</p>
      <p class="hero-lead" data-enter style="--d:320ms">{T(H['hero_lead'], lang)}</p>
      <div class="hero-cta" data-enter style="--d:440ms">
        <a class="btn btn-gold shine" href="{rel('journey', lang, lang)}">{T(H['cta_primary'], lang)}{fwd(lang)}</a>
        <a class="btn btn-glass" href="{rel('contact', lang, lang)}">{T(H['cta_secondary'], lang)}</a>
      </div>
      <ul class="hero-meta" data-enter style="--d:560ms">{meta}</ul>
    </div>
    <div class="hero-visual" data-hero-visual>
      <figure class="medallion" data-enter style="--d:60ms">
        <div class="sky sky--converge" aria-hidden="true">{sky_converge()}</div>
        <div class="med-orbit" aria-hidden="true"><span class="sat"></span></div>
        <div class="med-ring" aria-hidden="true"></div>
        <div class="med-shine" aria-hidden="true"></div>
        <div class="portrait">{portrait}</div>
        <figcaption class="sr-only">{T(C.PERSON['portrait_alt'], lang)}</figcaption>
        <div class="badge badge--a glass-dark">{icon('award')}<span><b>{T(H['badge_award'], lang)}</b><small>{T(H['badge_award_sub'], lang)}</small></span></div>
        <div class="badge badge--b glass-dark">{icon('graduation-cap')}<span><b>{T(H['badge_phd'], lang)}</b><small>{T(H['badge_phd_sub'], lang)}</small></span></div>
      </figure>
    </div>
  </div>
  <div class="parapet" aria-hidden="true"></div>
</section>

<section class="sec story" data-section>
  <div class="wrap story-grid">
    {sec_head(lang, H['story_h'])}
    <div class="story-body">
      <p class="story-text" data-reveal>{T(H['story'], lang)}</p>
      <a class="tlink" href="{rel('journey', lang, lang)}" data-reveal><span>{T(H['story_link'], lang)}</span>{fwd(lang)}</a>
    </div>
  </div>
</section>

<div class="parapet parapet--night" aria-hidden="true"></div>
<section class="band" data-section>
  {sky('domains', 'sky--band', lang)}
  <div class="wrap stats">{stats}</div>
  <div class="parapet" aria-hidden="true"></div>
</section>

<section class="sec" data-section>
  <div class="wrap">
    {sec_head(lang, H['pillars_h'], H['pillars_lead'])}
    <div class="grid grid-3 swipe" data-swipe>{pillars}</div>
    {dots(len(H['pillars']))}
  </div>
</section>

<section class="sec sec--tint sec--sky" data-section>
  {sky('trace', 'sky--light', lang, 21)}
  <div class="wrap">
    {sec_head(lang, H['think_h'], H['think_lead'])}
    <div class="grid grid-2 swipe" data-swipe>{think}</div>
    {dots(len(H['think']))}
  </div>
</section>

<section class="sec" data-section>
  <div class="wrap phd">
    <div class="phd-copy">
      {sec_head(lang, H['phd_h'])}
      <p class="phd-q" data-reveal>{T(H['phd_q'], lang)}</p>
      <p class="phd-p" data-reveal>{T(H['phd_p'], lang)}</p>
      <a class="btn btn-ink" href="{rel('research', lang, lang)}" data-reveal>{T(H['phd_link'], lang)}{fwd(lang)}</a>
    </div>
    <div class="phd-visual card" data-reveal>{diagram(lang, compact=True)}</div>
  </div>
</section>

<section class="sec sec--tint sec--sky" data-section>
  {sky('trace', 'sky--light', lang, 33)}
  <div class="wrap">
    {sec_head(lang, H['honors_h'])}
    <div class="grid grid-3 swipe" data-swipe>{honors}</div>
    {dots(len(H['honors']))}
  </div>
</section>

<section class="sec cta" data-section>
  <div class="wrap">
    <div class="cta-card" data-reveal>
      {sky('calm', 'sky--cta', lang)}
      <div class="cta-copy">
        <h2 class="sec-title">{T(H['cta_h'], lang)}</h2>
        <p class="cta-p">{T(H['cta_p'], lang)}</p>
      </div>
      <a class="btn btn-gold shine" href="{rel('contact', lang, lang)}">{T(H['cta_secondary'], lang)}{fwd(lang)}</a>
    </div>
  </div>
</section>'''

def journey(lang):
    J = C.JOURNEY
    items = []
    for i, ch in enumerate(J["chapters"]):
        kind = ch["kind"]
        chip = ""
        if kind == "abroad":
            chip = '<span class="chip chip--gold">%s%s</span>' % (icon("plane-takeoff"), T(J["depart"], lang))
        elif kind == "return":
            chip = '<span class="chip">%s%s</span>' % (icon("plane-landing"), T(J["return"], lang))
        years = ch["years"]
        years_html = T(years, lang) if isinstance(years, dict) else ltr(years)
        tags = "".join('<li>%s</li>' % T(tg, lang) for tg in ch.get("tags", []))
        full = L(ch["p"], lang)
        cut = full.find(". ")
        if cut > 0:
            first, rest = full[:cut + 1], full[cut + 2:]
            mid = "chm-%s-%d" % (lang, i)
            more = ('<button class="ch-toggle" type="button" aria-expanded="false" aria-controls="%s"><span class="t-open">%s</span><span class="t-close">%s</span>%s</button>'
                    '<div class="ch-more" id="%s"><div class="ch-more-in"><p class="ch-p">%s</p></div></div>'
                    % (mid, T(C.UI["more"], lang), T(C.UI["less"], lang), icon("chevron-down", "ic ch-toggle-ic"), mid, bidi(rest, lang)))
            body = '<p class="ch-p">%s</p>%s' % (bidi(first, lang), more)
        else:
            body = '<p class="ch-p">%s</p>' % bidi(full, lang)
        path = ("M30 0 V100" if kind != "abroad" else "M30 0 V12 C30 24 52 22 52 36 V64 C52 78 30 76 30 88 V100")
        items.append(f'''<li class="ch ch--{kind}" data-section>
  <div class="rail" aria-hidden="true"><svg viewBox="0 0 60 100" preserveAspectRatio="none" focusable="false"><path class="rail-base" d="{path}" vector-effect="non-scaling-stroke"/><path class="rail-draw" pathLength="1" d="{path}" vector-effect="non-scaling-stroke"/></svg><span class="rail-node"></span></div>
  <article class="card ch-card" data-reveal>
    <div class="ch-side"><span class="ch-years">{years_html}</span><span class="ch-place">{icon('map-pin')}{T(ch['place'], lang)}</span>{chip}</div>
    <div class="ch-main">
      <h2 class="ch-h">{T(ch['h'], lang)}</h2>
      {body}
      <ul class="ch-tags">{tags}</ul>
    </div>
  </article>
</li>''')
    closing_sub = ('<p class="closing-sub">%s</p>' % T(J["closing_en"], lang)) if L(J["closing_en"], lang) else ""
    return page_hero(lang, "world", J["h1"], J["lead"]) + f'''
<section class="sec journey" data-section>
  <div class="wrap">
    <ol class="chapters">{''.join(items)}</ol>
    <div class="closing" data-reveal><p class="closing-ar" lang="ar" dir="rtl">{esc(J['closing'])}</p>{closing_sub}</div>
  </div>
</section>
{next_link(lang, 'impact', J['next'])}'''

def impact(lang):
    I = C.IMPACT
    blocks = []
    for a in I["areas"]:
        items = "".join(
            '<article class="card item" data-reveal style="--i:%d"><span class="tile">%s</span><h3 class="card-h">%s</h3><p class="card-p">%s</p></article>'
            % (i, icon(it["icon"]), T(it["h"], lang), T(it["p"], lang)) for i, it in enumerate(a["items"]))
        cols = "grid-3" if len(a["items"]) % 3 == 0 else "grid-4"
        blocks.append(f'''<section class="sec area" id="{a['id']}" data-section>
  <div class="wrap">
    <div class="area-head">
      <span class="tile tile--lg" data-reveal>{icon(a['icon'])}</span>
      <div>
        <h2 class="sec-title" data-reveal data-slide>{T(a['h'], lang)}</h2>
        <p class="area-role" data-reveal>{T(a['role'], lang)}</p>
        <p class="sec-lead" data-reveal>{T(a['p'], lang)}</p>
      </div>
    </div>
    <p class="note" data-reveal>{icon('award')}<span>{T(a['note'], lang)}</span></p>
    <div class="grid {cols} swipe" data-swipe>{items}</div>
    {dots(len(a['items']))}
  </div>
</section>''')
    focus = "".join('<li data-reveal style="--i:%d">%s</li>' % (i, T(f, lang)) for i, f in enumerate(I["focus"]))
    jump = "".join('<a class="jump" href="#%s">%s<span>%s</span></a>' % (a["id"], icon(a["icon"]), T(a["h"], lang)) for a in I["areas"])
    return page_hero(lang, "kingdom", I["h1"], I["lead"], '<nav class="jumps" data-enter style="--d:320ms" aria-label="%s">%s</nav>' % (esc(L(I["h1"], lang)), jump)) + "".join(blocks) + f'''
<section class="sec sec--tint" data-section>
  <div class="wrap">
    {sec_head(lang, I['focus_h'])}
    <ul class="focus">{focus}</ul>
  </div>
</section>
{next_link(lang, 'research', I['next'])}'''

def research(lang):
    R = C.RESEARCH
    explain = "".join('<p class="ex-p" data-reveal>%s</p>' % T(p, lang) for p in R["explain"])
    pubs = "".join(
        '<li class="pub" data-reveal style="--i:%d"><span class="pub-y" dir="ltr">%s</span><div class="pub-body"><p class="pub-t" lang="en" dir="ltr">%s</p><p class="pub-v">%s</p></div></li>'
        % (i, esc(p["y"]), esc(p["title"]), T(p["venue"], lang)) for i, p in enumerate(R["pubs"]))
    degrees = "".join(
        '<article class="card degree" data-reveal style="--i:%d"><span class="tile">%s</span><h3 class="card-h">%s</h3><p class="card-p">%s</p><p class="degree-foot"><span class="degree-years" dir="ltr">%s</span><span class="degree-note">%s</span></p></article>'
        % (i, icon(d["icon"]), T(d["deg"], lang), T(d["school"], lang), esc(d["years"]), T(d["note"], lang)) for i, d in enumerate(R["degrees"]))
    return page_hero(lang, "domains", R["h1"], R["lead"]) + f'''
<section class="sec" data-section>
  <div class="wrap explain">
    <div class="explain-copy">{sec_head(lang, R['explain_h'])}{explain}</div>
    <div class="explain-visual card" data-reveal>{diagram(lang)}</div>
  </div>
</section>

<section class="sec sec--tint sec--sky" data-section>
  {sky('trace', 'sky--light', lang, 44)}
  <div class="wrap pubs-wrap">
    {sec_head(lang, R['pubs_h'])}
    <ol class="pubs">{pubs}</ol>
  </div>
</section>

<section class="sec" data-section>
  <div class="wrap duo">
    <article class="card feature feature--night" data-reveal style="--i:0">
      {sky('calm', 'sky--card', lang, 5)}
      <span class="feature-n" dir="ltr"><span class="count" data-count="30000">30,000</span></span>
      <h2 class="feature-h">{T(R['reads_h'], lang)}</h2>
      <p class="feature-p">{T(R['reads_p'], lang)}</p>
    </article>
    <article class="card feature feature--night" data-reveal style="--i:1">
      {sky('calm', 'sky--card', lang, 9)}
      <span class="feature-n" dir="ltr"><span class="count" data-count="93.18" data-dec="2">93.18</span>%</span>
      <h2 class="feature-h">{T(R['teach_h'], lang)}</h2>
      <p class="feature-p">{T(R['teach_p'], lang)}</p>
    </article>
  </div>
</section>

<section class="sec sec--tint" data-section>
  <div class="wrap">
    {sec_head(lang, R['degrees_h'])}
    <div class="grid grid-4 swipe" data-swipe>{degrees}</div>
    {dots(len(R['degrees']))}
  </div>
</section>
{next_link(lang, 'contact', R['next'])}'''

def faq_items(lang):
    items = []
    for q, a in C.CONTACT["faq"]:
        ans = L(a, lang)
        if q is C.CONTACT["faq"][-1][0] and CONFIG["EMAIL"]:
            ans = ("عبر رسالة على لينكدإن أو البريد الإلكتروني %s." if lang == "ar" else "Through a LinkedIn message or by email at %s.") % CONFIG["EMAIL"]
        items.append((L(q, lang), ans))
    return items

def contact(lang):
    K = C.CONTACT
    acts = []
    for i, (kind, ic, label, value, href) in enumerate(contact_items(lang)):
        ext = ' target="_blank" rel="noopener"' if href.startswith("http") else ""
        if kind == "linkedin":
            acts.append('<a class="btn btn-gold shine" href="%s"%s>%s<span>%s</span></a>' % (esc(href), ext, icon("linkedin"), T(C.UI["linkedin_cta"], lang)))
        else:
            acts.append('<a class="btn btn-glass" href="%s"%s>%s<span>%s</span></a>' % (esc(href), ext, icon(ic), value))
    panel = f'''<article class="cpanel" data-reveal>
      {sky('calm', 'sky--panel', lang, 13)}
      <div class="cpanel-id">{brand_mark(lang, 84)}<div><h2 class="cpanel-name">{T(C.PERSON['name'], lang)}</h2><p class="cpanel-role">{T(C.PERSON['role'], lang)}</p></div></div>
      <p class="cpanel-p">{T(K['panel_p'], lang)}</p>
      <div class="cpanel-actions">{''.join(acts)}</div>
      <p class="cpanel-loc">{icon('map-pin')}<span>{T(C.PERSON['city'], lang)}</span></p>
    </article>'''
    faq = "".join('<details class="faq" style="--i:%d"><summary><span>%s</span>%s</summary><div class="faq-a"><p>%s</p></div></details>'
                  % (i, bidi(q, lang), icon("chevron-down", "ic faq-ic"), bidi(a, lang)) for i, (q, a) in enumerate(faq_items(lang)))
    return page_hero(lang, "calm", K["h1"], K["lead"]) + f'''
<section class="sec" data-section>
  <div class="wrap">{panel}</div>
</section>
<section class="sec sec--tint sec--sky" data-section>
  {sky('trace', 'sky--light', lang, 55)}
  <div class="wrap faq-wrap">
    {sec_head(lang, K['faq_h'])}
    <div class="faqs">{faq}</div>
  </div>
</section>'''

BUILDERS = {"index": home, "journey": journey, "impact": impact, "research": research, "contact": contact}
META = {"index": C.HOME, "journey": C.JOURNEY, "impact": C.IMPACT, "research": C.RESEARCH, "contact": C.CONTACT}

# ============================================================== structured data
def person_ld():
    alt = ["Hamad Al-Thiapi", "Hamad Al-thiapi", "Dr. Hamad Al-thiapi", "Hamad Althiapi", "Hamad Al Thiapi", "Dr Hamad Al Thiapi",
           "Eng. Dr. Hamad Al-Thiapi", "Hamad Al-Thiyabi", "Hamad Althiyabi", "Hamad Al-Dhiyabi", "Hamad Aldhiyabi", "Hamad Al-Thiabi",
           "Hamad Al-Theyabi", "Hamad Al-Diyabi", "Hamed Al-Thiapi",
           "حمد الذيابي", "د. حمد الذيابي", "د / حمد الذيابي", "الدكتور حمد الذيابي", "المهندس الدكتور حمد الذيابي", "حمد الذيابى", "حمد الديابي", "حمد الزيابي"]
    p = {
        "@type": "Person", "@id": CONFIG["BASE_URL"] + "#person",
        "name": "Dr. Hamad Al-Thiapi", "alternateName": alt,
        "honorificPrefix": "Dr.", "givenName": "Hamad", "familyName": "Al-Thiapi",
        "jobTitle": ["Director of Artificial Intelligence Management", "مدير إدارة الذكاء الاصطناعي"],
        "description": L(C.HOME["desc"], "en"),
        "url": CONFIG["BASE_URL"],
        "address": {"@type": "PostalAddress", "addressLocality": "Riyadh", "addressCountry": "SA"},
        "workLocation": {"@type": "Place", "name": "Riyadh, Saudi Arabia"},
        "worksFor": {"@type": "GovernmentOrganization", "name": "Saudi government sector (entity not disclosed)", "address": {"@type": "PostalAddress", "addressLocality": "Riyadh", "addressCountry": "SA"}},
        "hasOccupation": [
            {"@type": "Occupation", "name": "Director of Artificial Intelligence",
             "alternateName": ["Head of Artificial Intelligence", "AI Director", "AI Leader", "مدير إدارة الذكاء الاصطناعي", "مدير الذكاء الاصطناعي", "قائد الذكاء الاصطناعي"],
             "occupationLocation": {"@type": "City", "name": "Riyadh"},
             "skills": "AI strategy, AI governance, KPIs, data warehouse, AI use cases, DGA/SDAIA/NCA compliance"},
            {"@type": "Occupation", "name": "Digital Transformation Leader",
             "alternateName": ["Digital Government Leader", "E-Services Director", "قائد التحول الرقمي", "مدير الخدمات والتعاملات الإلكترونية"]},
            {"@type": "Occupation", "name": "Network and Telecommunications Engineer",
             "alternateName": ["Network Engineer", "Network Operations Director", "مهندس شبكات واتصالات", "مدير عمليات الشبكات"]},
            {"@type": "Occupation", "name": "Researcher in computer networks",
             "alternateName": ["SDN researcher", "BGP researcher", "باحث في هندسة الشبكات"]},
        ],
        "knowsAbout": ["Artificial Intelligence", "AI strategy", "AI governance", "Digital transformation", "Digital government", "Data governance",
                       "Data analytics", "Cloud migration", "Government cloud", "Network infrastructure", "Software-Defined Networking (SDN)",
                       "Border Gateway Protocol (BGP)", "BGP convergence", "Wireless sensor networks", "IT strategy", "IT program management",
                       "Government procurement", "DGA, SDAIA and NCA compliance",
                       "الذكاء الاصطناعي", "استراتيجية الذكاء الاصطناعي", "حوكمة الذكاء الاصطناعي", "التحول الرقمي", "الحكومة الرقمية",
                       "حوكمة البيانات", "الحوسبة السحابية", "البنية التحتية للشبكات", "الشبكات المعرّفة بالبرمجيات"],
        "alumniOf": [
            {"@type": "CollegeOrUniversity", "name": "RMIT University", "address": "Melbourne, Australia"},
            {"@type": "CollegeOrUniversity", "name": "University of Bridgeport", "address": "Bridgeport, Connecticut, USA"},
            {"@type": "CollegeOrUniversity", "name": "Umm Al-Qura University", "alternateName": "جامعة أم القرى", "address": "Makkah, Saudi Arabia"},
            {"@type": "CollegeOrUniversity", "name": "King Fahad Security College", "alternateName": "كلية الملك فهد الأمنية", "address": "Riyadh, Saudi Arabia"},
        ],
        "hasCredential": [
            {"@type": "EducationalOccupationalCredential", "credentialCategory": "degree", "educationalLevel": "Doctoral",
             "name": "Ph.D., Networks and Telecommunication Engineering", "recognizedBy": {"@type": "CollegeOrUniversity", "name": "RMIT University"}},
            {"@type": "EducationalOccupationalCredential", "credentialCategory": "degree", "educationalLevel": "Master's",
             "name": "Master of Engineering, Computer Engineering (Honors, GPA 3.67/4)", "recognizedBy": {"@type": "CollegeOrUniversity", "name": "University of Bridgeport"}},
            {"@type": "EducationalOccupationalCredential", "credentialCategory": "degree", "educationalLevel": "Bachelor's",
             "name": "Bachelor's degree, Computer Engineering", "recognizedBy": {"@type": "CollegeOrUniversity", "name": "Umm Al-Qura University"}},
            {"@type": "EducationalOccupationalCredential", "credentialCategory": "diploma",
             "name": "Diploma, Security Science (grade 94)", "recognizedBy": {"@type": "CollegeOrUniversity", "name": "King Fahad Security College"}},
            {"@type": "EducationalOccupationalCredential", "credentialCategory": "Professional accreditation",
             "name": "Consultant Professional Accreditation", "recognizedBy": {"@type": "Organization", "name": "Saudi Council of Engineers", "alternateName": "الهيئة السعودية للمهندسين"}},
        ],
        "award": ["Best Technology Leader Award 2025 (2nd place across all sectors and regions)",
                  "Ideal Teacher (Rose) Award 2019, RMIT University (93.18% teaching score)",
                  "Excellence Award 2017 (Network Operations Division)"],
        "memberOf": {"@type": "Organization", "name": "Upsilon Pi Epsilon"},
        "knowsLanguage": [{"@type": "Language", "name": "Arabic", "alternateName": "ar"}, {"@type": "Language", "name": "English", "alternateName": "en"}],
        "sameAs": [CONFIG["LINKEDIN"]] if CONFIG["LINKEDIN"] else [],
    }
    if CONFIG["PHOTO"]:
        p["image"] = CONFIG["BASE_URL"] + "assets/img/portrait.jpg"
    if CONFIG["EMAIL"]:
        p["email"] = "mailto:" + CONFIG["EMAIL"]
    if CONFIG["PHONE"]:
        p["telephone"] = CONFIG["PHONE"]
    return p

def page_ld(slug, lang):
    meta = META[slug]
    url = abs_url(slug, lang)
    graph = [
        person_ld(),
        {"@type": "WebSite", "@id": CONFIG["BASE_URL"] + "#website", "url": CONFIG["BASE_URL"], "name": "Dr. Hamad Al-Thiapi",
         "alternateName": "د. حمد الذيابي", "inLanguage": ["ar", "en"], "about": {"@id": CONFIG["BASE_URL"] + "#person"}},
        {"@type": "ProfilePage" if slug == "index" else "WebPage", "@id": url + "#page", "url": url, "name": L(meta["title"], lang),
         "description": L(meta["desc"], lang), "inLanguage": lang, "isPartOf": {"@id": CONFIG["BASE_URL"] + "#website"},
         "mainEntity" if slug == "index" else "about": {"@id": CONFIG["BASE_URL"] + "#person"},
         "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
             {"@type": "ListItem", "position": 1, "name": L(C.NAV[0][1], lang), "item": abs_url("index", lang)}] +
             ([{"@type": "ListItem", "position": 2, "name": L(dict((s, l) for s, l, _ in C.NAV)[slug], lang), "item": url}] if slug != "index" else [])}},
    ]
    if slug == "research":
        for p in C.RESEARCH["pubs"]:
            graph.append({"@type": "ScholarlyArticle", "headline": p["title"], "name": p["title"], "datePublished": p["y"],
                          "publisher": L(p["venue"], "en"), "author": {"@id": CONFIG["BASE_URL"] + "#person"}})
    if slug == "contact":
        graph.append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq_items(lang)]})
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))

# ============================================================== document
FONT_PRELOAD = {
    "ar": ["ibm-plex-sans-arabic-arabic-400-normal.woff2", "ibm-plex-sans-arabic-arabic-600-normal.woff2", "amiri-arabic-700-normal.woff2",
           "ibm-plex-sans-arabic-latin-400-normal.woff2", "ibm-plex-sans-arabic-latin-600-normal.woff2", "amiri-latin-700-normal.woff2",
           "cormorant-garamond-latin-600-normal.woff2"],
    "en": ["ibm-plex-sans-arabic-latin-400-normal.woff2", "ibm-plex-sans-arabic-latin-600-normal.woff2", "cormorant-garamond-latin-600-normal.woff2",
           "ibm-plex-sans-arabic-arabic-600-normal.woff2"],
}

HEAD_JS = ("(function(){var d=document.documentElement;d.className=d.className.replace('no-js','js');"
           "try{var t=localStorage.getItem('theme');if(t==='dark'||t==='light'){d.setAttribute('data-theme',t)}}catch(e){}"
           "try{var w=localStorage.getItem('lang'),a=d.getAttribute('data-alt');"
           "if(w&&w!==d.lang&&a&&!/[?&]stay/.test(location.search)){location.replace(a+location.hash)}}catch(e){}})();")

RESTORE_JS = ("(function(){try{var p=sessionStorage.getItem('langpos');if(!p)return;sessionStorage.removeItem('langpos');p=JSON.parse(p);"
              "if(p.page!==document.body.getAttribute('data-page')||!(p.y>0))return;var s=document.querySelectorAll('[data-section]')[p.idx];if(!s)return;"
              "var h=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h'))||70;var r=s.getBoundingClientRect();"
              "window.scrollTo({top:Math.max(0,window.scrollY+r.top+p.frac*r.height-h-20),behavior:'instant'})}catch(e){}})();")

def document(slug, lang):
    meta = META[slug]
    other = "en" if lang == "ar" else "ar"
    title, desc = L(meta["title"], lang), L(meta["desc"], lang)
    url = abs_url(slug, lang)
    og_img = CONFIG["BASE_URL"] + "assets/img/og.jpg"
    robots = '<meta name="robots" content="noindex, nofollow">' if CONFIG["PREVIEW"] else '<meta name="robots" content="index, follow, max-image-preview:large">'
    fonts = FONT_PRELOAD[lang] + (["amiri-arabic-700-normal.woff2"] if (lang == "en" and slug == "journey") else [])
    preload = "".join('<link rel="preload" href="%s" as="font" type="font/woff2" crossorigin>' % asset(lang, "fonts/" + f) for f in fonts)
    body = BUILDERS[slug](lang)
    return f'''<!doctype html>
<html lang="{lang}" dir="{'rtl' if lang == 'ar' else 'ltr'}" class="no-js" data-theme="light" data-alt="{esc(rel(slug, other, lang))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="ar" href="{abs_url(slug, 'ar')}">
<link rel="alternate" hreflang="en" href="{abs_url(slug, 'en')}">
<link rel="alternate" hreflang="x-default" href="{abs_url(slug, 'ar')}">
<meta property="og:type" content="profile">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og_img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="{'ar_SA' if lang == 'ar' else 'en_US'}">
<meta property="og:locale:alternate" content="{'en_US' if lang == 'ar' else 'ar_SA'}">
<meta property="profile:first_name" content="Hamad">
<meta property="profile:last_name" content="Al-Thiapi">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og_img}">
<meta name="author" content="{esc(L(C.PERSON['name'], lang))}">
<meta name="theme-color" content="#1b1a2e">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="{asset(lang, 'img/icon.svg')}" type="image/svg+xml">
<link rel="apple-touch-icon" href="{asset(lang, 'img/apple-touch-icon.png')}">
{preload}
<script>{HEAD_JS}</script>
<link rel="stylesheet" href="{asset(lang, 'style.css')}">
<script type="application/ld+json">{page_ld(slug, lang)}</script>
</head>
<body data-page="{slug}">
<a class="skip" href="#main">{T(C.UI['skip'], lang)}</a>
<div class="progress" aria-hidden="true"></div>
{header(lang, slug)}
<main id="main" tabindex="-1">
{body}
</main>
{footer(lang, slug)}
{dock(lang, slug)}
<script>{RESTORE_JS}</script>
<script src="{asset(lang, 'site.js')}" defer></script>
</body>
</html>
'''

# ============================================================== text files for AI & search
def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)

def llms_txt():
    b = CONFIG["BASE_URL"]
    lines = [
        "# Dr. Hamad Al-Thiapi (د. حمد الذيابي)", "",
        "> " + L(C.HOME["desc"], "en"), "",
        "Eng. Dr. Hamad Al-Thiapi leads technology in the Saudi government sector (18+ years). Director of Artificial Intelligence Management at a government entity in Riyadh since 2023; also led E-Services & Transactions (2023–2025). Ph.D. in Networks & Telecommunication Engineering (RMIT University, Australia), M.Eng. in Computer Engineering with honors (University of Bridgeport, USA), B.Sc. in Computer Engineering (Umm Al-Qura University). Best Technology Leader Award 2025 (2nd place across all sectors and regions).", "",
        "## Pages (English)",
    ]
    for s, label, _ in C.NAV:
        lines.append("- [%s](%s): %s" % (L(label, "en"), abs_url(s, "en"), L(META[s]["desc"], "en")))
    lines += ["", "## الصفحات (العربية)"]
    for s, label, _ in C.NAV:
        lines.append("- [%s](%s): %s" % (L(label, "ar"), abs_url(s, "ar"), L(META[s]["desc"], "ar")))
    lines += ["", "## More", "- [Full text of the site](%sllms-full.txt)" % b]
    if CONFIG["LINKEDIN"]:
        lines.append("- [LinkedIn](%s)" % CONFIG["LINKEDIN"])
    return "\n".join(lines) + "\n"

def llms_full():
    out = ["# Dr. Hamad Al-Thiapi — full site text (English, then Arabic)", ""]
    for lang in ("en", "ar"):
        out.append("=" * 60)
        out.append("LANGUAGE: " + lang)
        out.append("=" * 60)
        H = C.HOME
        out += ["", "## " + L(C.PERSON["name"], lang) + " — " + L(C.PERSON["role"], lang), L(H["hero_lead"], lang), ""]
        out += ["### " + L(H["story_h"], lang), L(H["story"], lang), ""]
        out += ["### " + L(H["pillars_h"], lang)] + ["- %s: %s" % (L(p["h"], lang), L(p["p"], lang)) for p in H["pillars"]] + [""]
        out += ["### " + L(H["think_h"], lang)] + ["- %s: %s" % (L(p["h"], lang), L(p["p"], lang)) for p in H["think"]] + [""]
        out += ["### " + L(H["honors_h"], lang)] + ["- %s — %s: %s" % (h["y"], L(h["h"], lang), L(h["p"], lang)) for h in H["honors"]] + [""]
        J = C.JOURNEY
        out += ["## " + L(J["h1"], lang), L(J["lead"], lang), ""]
        for ch in J["chapters"]:
            yrs = L(ch["years"], lang) if isinstance(ch["years"], dict) else ch["years"]
            out += ["### %s (%s, %s)" % (L(ch["h"], lang), L(ch["place"], lang), yrs), L(ch["p"], lang), ""]
        I = C.IMPACT
        out += ["## " + L(I["h1"], lang), L(I["lead"], lang), ""]
        for a in I["areas"]:
            out += ["### %s — %s" % (L(a["h"], lang), L(a["role"], lang)), L(a["p"], lang), L(a["note"], lang)]
            out += ["- %s: %s" % (L(it["h"], lang), L(it["p"], lang)) for it in a["items"]] + [""]
        out += ["### " + L(I["focus_h"], lang), " • ".join(L(f, lang) for f in I["focus"]), ""]
        R = C.RESEARCH
        out += ["## " + L(R["h1"], lang), L(R["lead"], lang), ""] + [L(p, lang) for p in R["explain"]] + [""]
        out += ["### " + L(R["pubs_h"], lang)] + ["- %s. %s. %s" % (p["y"], p["title"], L(p["venue"], lang)) for p in R["pubs"]] + [""]
        out += ["### " + L(R["reads_h"], lang), L(R["reads_p"], lang), "", "### " + L(R["teach_h"], lang), L(R["teach_p"], lang), ""]
        out += ["### " + L(R["degrees_h"], lang)] + ["- %s — %s (%s). %s" % (L(d["deg"], lang), L(d["school"], lang), d["years"], L(d["note"], lang)) for d in R["degrees"]] + [""]
        out += ["## " + L(C.CONTACT["h1"], lang), L(C.CONTACT["lead"], lang), ""]
        out += ["### " + L(C.CONTACT["faq_h"], lang)] + ["**%s**\n%s\n" % (q, a) for q, a in faq_items(lang)]
        if CONFIG["LINKEDIN"]:
            out += ["LinkedIn: " + CONFIG["LINKEDIN"], ""]
    return "\n".join(out) + "\n"

def robots_txt():
    if CONFIG["PREVIEW"]:
        prev = ["LinkedInBot", "facebookexternalhit", "WhatsApp", "Twitterbot", "TelegramBot", "Slackbot", "Discordbot"]
        return ("# Preview: hidden from search and AI crawlers until approved (PREVIEW = True in build.py).\n"
                "# Link-preview bots may read it so shared links show a card.\n\n"
                + "".join("User-agent: %s\nAllow: /\n\n" % b for b in prev) + "User-agent: *\nDisallow: /\n")
    bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User", "Claude-SearchBot", "anthropic-ai",
            "PerplexityBot", "Perplexity-User", "Google-Extended", "Googlebot", "Bingbot", "Applebot", "Applebot-Extended",
            "DuckDuckBot", "YandexBot", "CCBot", "Amazonbot", "Meta-ExternalAgent"]
    s = "".join("User-agent: %s\nAllow: /\n\n" % b for b in bots)
    return s + "User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n" % CONFIG["BASE_URL"]

def sitemap():
    today = date.today().isoformat()
    rows = []
    for s in PAGES:
        for lang in LANGS:
            alts = "".join('<xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (l2, abs_url(s, l2)) for l2 in LANGS)
            alts += '<xhtml:link rel="alternate" hreflang="x-default" href="%s"/>' % abs_url(s, "ar")
            rows.append("<url><loc>%s</loc><lastmod>%s</lastmod>%s</url>" % (abs_url(s, lang), today, alts))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n%s\n</urlset>\n' % "\n".join(rows))

def not_found():
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>الصفحة غير موجودة | د. حمد الذيابي</title><meta name="robots" content="noindex">
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#1b1a2e;color:#f3eee4;font:17px/1.8 system-ui,sans-serif;text-align:center;padding:24px}}a{{color:#d9b76f;font-weight:600;text-decoration:none}}</style></head>
<body><main><p>الصفحة غير موجودة · Page not found</p><p><a href="{CONFIG['BASE_URL']}">العودة إلى الرئيسية</a> · <a href="{CONFIG['BASE_URL']}en/">Back home</a></p></main></body></html>'''

# ============================================================== build
def build():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "en"))
    shutil.copytree(os.path.join(SRC, "assets"), os.path.join(OUT, "assets"))
    for lang in LANGS:
        for slug in PAGES:
            path = os.path.join(OUT, ("en" if lang == "en" else ""), page_file(slug))
            with open(path, "w", encoding="utf-8") as f:
                f.write(document(slug, lang))
    for name, text in (("llms.txt", llms_txt()), ("llms-full.txt", llms_full()), ("robots.txt", robots_txt()),
                       ("sitemap.xml", sitemap()), ("404.html", not_found())):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(text)
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    if CONFIG["DOMAIN"]:
        with open(os.path.join(OUT, "CNAME"), "w") as f:
            f.write(CONFIG["DOMAIN"].strip() + "\n")
    n = sum(len(fs) for _, _, fs in os.walk(OUT))
    print("built %d files into %s (PREVIEW=%s)" % (n, OUT, CONFIG["PREVIEW"]))

if __name__ == "__main__":
    build()
