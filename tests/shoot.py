"""Quick screenshots: python3 tests/shoot.py <page> <lang> <width> <height> [theme] [scrolls...]"""
import sys, asyncio
from playwright.async_api import async_playwright
OUT = "/tmp/claude-0/-home-claude/de5effe6-e0c8-50f2-bcd8-0ff6f15724b0/scratchpad/shots"
async def main():
    page_name, lang, w, h = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    theme = sys.argv[5] if len(sys.argv) > 5 else "light"
    full = "full" in sys.argv
    url = "http://127.0.0.1:8765/" + ("en/" if lang == "en" else "") + ("" if page_name == "index" else page_name + ".html")
    async with async_playwright() as p:
        b = await p.chromium.launch()
        mobile = w < 600
        ctx = await b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1, is_mobile=mobile, has_touch=mobile)
        await ctx.add_init_script("try{localStorage.setItem('theme','%s')}catch(e){}" % theme)
        pg = await ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        await pg.goto(url + "?stay=1", wait_until="networkidle")
        await pg.wait_for_timeout(3600)
        name = f"{OUT}/{page_name}-{lang}-{w}-{theme}"
        if full:
            # scroll through to trigger reveals, then full page
            hgt = await pg.evaluate("document.documentElement.scrollHeight")
            y = 0
            while y < hgt:
                await pg.evaluate(f"window.scrollTo(0,{y})"); await pg.wait_for_timeout(250); y += h // 2
            await pg.evaluate("window.scrollTo(0,0)"); await pg.wait_for_timeout(600)
            await pg.add_style_tag(content="[data-reveal],.swipe>*{animation:none!important;opacity:1!important;transform:none!important}.rail-draw{animation:none!important;stroke-dashoffset:0!important}[data-hero-out],[data-hero-visual],.phero>.sky{animation:none!important}")
            await pg.evaluate("document.querySelectorAll('.count[data-count]').forEach(e=>e.textContent=(+e.dataset.count).toLocaleString('en-US'))")
            await pg.wait_for_timeout(600)
            await pg.screenshot(path=name + "-full.png", full_page=True)
        else:
            await pg.screenshot(path=name + ".png")
        print("errors:", errs)
        await b.close()
asyncio.run(main())
