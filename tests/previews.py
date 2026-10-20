"""Builds the two combined preview images (phones, desktop)."""
import asyncio, os
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFilter
BASE = "http://127.0.0.1:8765/"
OUT = os.environ.get("PREV_OUT", "/mnt/user-data/outputs")
TMP = "/tmp/claude-0/-home-claude/de5effe6-e0c8-50f2-bcd8-0ff6f15724b0/scratchpad/prev"
os.makedirs(TMP, exist_ok=True)
PHONES = [  # (path, scroll target selector or None, theme, name)
    ("", None, "light", "p1"), ("", ".band", "light", "p2"), ("journey.html", ".chapters", "light", "p3"),
    ("research.html", ".explain", "light", "p4"), ("contact.html", ".cpanel", "dark", "p5"), ("en/", None, "dark", "p6"),
]
DESK = [("", None, "light", "d1"), ("journey.html", None, "light", "d2"), ("research.html", ".explain", "light", "d3"), ("en/", None, "dark", "d4")]
async def shoot(b, path, sel, theme, name, w, h, mobile):
    ctx = await b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=mobile, has_touch=mobile)
    await ctx.add_init_script("try{localStorage.setItem('theme','%s');localStorage.removeItem('lang')}catch(e){}" % theme)
    pg = await ctx.new_page()
    await pg.goto(BASE + path + "?stay=1", wait_until="networkidle")
    await pg.wait_for_timeout(1200)
    if sel:
        await pg.evaluate(f"(() => {{ const e = document.querySelector('{sel}'); window.scrollTo(0, e.getBoundingClientRect().top + scrollY - (innerWidth < 900 ? 70 : 90)); }})()")
        await pg.wait_for_timeout(1600)
        await pg.evaluate("document.querySelectorAll('.count[data-count]').forEach(e=>e.textContent=(+e.dataset.count).toLocaleString('en-US',{minimumFractionDigits:+(e.dataset.dec||0)}))")
    else:
        await pg.wait_for_timeout(2600)
    p = f"{TMP}/{name}.png"
    await pg.screenshot(path=p)
    await ctx.close()
    return p
def rounded(im, r):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.size[0] - 1, im.size[1] - 1), r, fill=255)
    out = Image.new("RGBA", im.size); out.paste(im, (0, 0), m); return out
def compose(paths, cols, cell_w, radius, gap, pad, bg, out):
    ims = [Image.open(p).convert("RGB") for p in paths]
    scale = cell_w / ims[0].size[0]
    ims = [i.resize((cell_w, int(i.size[1] * scale)), Image.LANCZOS) for i in ims]
    rows = (len(ims) + cols - 1) // cols
    ch = ims[0].size[1]
    W = pad * 2 + cols * cell_w + (cols - 1) * gap
    H = pad * 2 + rows * ch + (rows - 1) * gap
    canvas = Image.new("RGB", (W, H), bg)
    for k, im in enumerate(ims):
        x = pad + (k % cols) * (cell_w + gap); y = pad + (k // cols) * (ch + gap)
        sh = Image.new("RGBA", (cell_w + 60, ch + 60), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((30, 40, cell_w + 30, ch + 30), radius, fill=(10, 10, 25, 120))
        sh = sh.filter(ImageFilter.GaussianBlur(18))
        canvas.paste(sh, (x - 30, y - 30), sh)
        r = rounded(im, radius); canvas.paste(r, (x, y), r)
    canvas.save(out, quality=90)
    return out
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ph = [await shoot(b, *x, 390, 844, True) for x in PHONES]
        dk = [await shoot(b, *x, 1440, 900, False) for x in DESK]
        await b.close()
    compose(ph, 6, 390, 44, 36, 60, (226, 220, 208), f"{OUT}/preview-phone.jpg")
    compose(dk, 2, 1100, 18, 40, 60, (226, 220, 208), f"{OUT}/preview-desktop.jpg")
    print("ok")
asyncio.run(main())
