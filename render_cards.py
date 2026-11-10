"""Render ዓለም ዛሬ Amharic news cards (1080×1350 PNG) for one day's edition.

Each day lives in its own folder:
    editions/2026-11-10/
        stories.json   all text for that day (+ optional "image" per story, optional "lead")
        images/        that day's photos
        cards/         rendered PNGs, ready to post   (written by this script)
        credits.md     photo + source credits          (written by this script)

Usage:
    python3 render_cards.py                 render the latest edition
    python3 render_cards.py 2026-11-10      render that date's edition
    python3 render_cards.py --new 2026-11-11
                                            start a new edition (copies the latest
                                            stories.json as a starting point)
Every render first runs validate.py (the project's rules) and stops if it finds errors.
"""
import json, re, sys, html, os, shutil, tempfile, colorsys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
from validate import validate   # rule checks (validate.py) run before every render

try:
    from PIL import Image          # used to pick each photo's main colour for the card frame
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parent
EDITIONS = ROOT / "editions"
CSS_FILE = ROOT / "card.css"
W, H = 1080, 1350
SCALE = 2          # render at 2× (2160×2700) so text stays sharp after Instagram/TikTok downscale
JPEG_QUALITY = 95  # clean JPEG, no chroma subsampling (4:4:4) → crisp coloured text edges
AI_DISCLOSURE = "ይህ ይዘት በAI ታግዞ ተዘጋጅቶ በሰው ተገምግሟል"
WHY_TAG = "ለምን ያገባናል?"


# ---------- fonts ----------
# Best results: install Noto Sans Ethiopic + Poppins (fonts.google.com).
# macOS ships "Kefa" for Amharic as a fallback.
def _font_face(family, weight, candidates):
    srcs = [f"local('{c}')" for c in candidates if not c.startswith('/')]
    srcs += [f"url('file://{c}')" for c in candidates if c.startswith('/') and os.path.exists(c)]
    return f"@font-face {{ font-family:'{family}'; src:{', '.join(srcs)}; font-weight:{weight}; }}" if srcs else ""


FONT_FACES = "\n".join([
    _font_face('Amh', 400, ['Noto Sans Ethiopic', 'NotoSansEthiopic-Regular', 'Kefa', 'Kefa-Regular', 'Abyssinica SIL',
                            '/usr/share/fonts/truetype/freefont/FreeSerif.ttf']),
    _font_face('Pop', 700, ['Poppins Bold', 'Poppins-Bold', '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf']),
    _font_face('Pop', 500, ['Poppins Medium', 'Poppins-Medium', '/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf']),
])


# ---------- helpers ----------
def esc(s):
    return html.escape(str(s))


def darken(h, t):
    """Mix a hex colour toward black by share t."""
    h = h.lstrip('#')
    return '#' + ''.join('%02x' % round(int(h[i:i + 2], 16) * (1 - t)) for i in (0, 2, 4))


def page(inner, cls, vars_=None):
    css = FONT_FACES + "\n" + CSS_FILE.read_text(encoding='utf-8')
    style = "".join(f"--{k}:{v};" for k, v in (vars_ or {}).items())
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head>"
            f"<body><div class='card {cls}' style='{style}'>{inner}</div></body></html>")


def top(d, right=None):
    right = right or f"""<div class="meta amh">{esc(d['date_et'])}<br><span class="gc">{esc(d['date_gc'])}</span></div>"""
    return f"""<div class="top">
  <div class="brand"><div class="logo">🌍</div><div class="brand-name amh bold">{esc(d['brand'])}</div></div>
  {right}
</div>"""


# Light, uniform tone adjustment so photos catch the eye (originals in images/ are never touched).
# Colour/contrast only: no sharpening, no retouching, no generative edits.
ENHANCE_PHOTOS = True
ENHANCE = {"contrast": 1.11, "color": 1.20}      # 1.0 = unchanged
_enhanced_dir = None


def enhanced(f):
    """Copy of photo f with the light tone adjustment (cached in a temp folder), or f itself."""
    global _enhanced_dir
    if not ENHANCE_PHOTOS or Image is None or f is None:
        return f
    from PIL import ImageEnhance
    if _enhanced_dir is None:
        _enhanced_dir = Path(tempfile.mkdtemp(prefix="alem_photos_"))
    out = _enhanced_dir / (f.stem + ".jpg")
    if not out.exists():
        im = Image.open(f).convert("RGB")
        im = ImageEnhance.Contrast(im).enhance(ENHANCE["contrast"])
        im = ImageEnhance.Color(im).enhance(ENHANCE["color"])
        im.save(out, "JPEG", quality=95, subsampling=0)
    return out


def image_path(s, edition):
    """Path of a story's photo, or None (with a warning if it is listed but missing)."""
    img = s.get('image')
    if not img:
        return None
    f = (edition / img['file']).resolve()
    if not f.exists():
        print(f"  WARNING: image not found, rendering without it: {f}")
        return None
    return enhanced(f)


def img_tag(s, f, cls=""):
    pos = esc(s['image'].get('position', 'center'))
    return f'<img class="{cls}" src="{f.as_uri()}" style="object-position:{pos}">'


def photo_colour(f, fallback):
    """The photo's most characteristic colour (frequent and fairly saturated)."""
    if not f or Image is None:
        return fallback
    im = Image.open(f).convert("RGB").resize((80, 80))
    q = im.quantize(8)
    pal = q.getpalette()[:24]
    best, score = None, -1
    for n, i in q.getcolors():
        r, g, b = pal[i * 3:i * 3 + 3]
        _, l, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        sc = n * (sat ** 1.3 + 0.03) * max(0.05, 1 - abs(l - 0.42) * 1.6)
        if sc > score:
            best, score = '#%02x%02x%02x' % (r, g, b), sc
    return best or fallback


def lead_index(d):
    """Which story is on the cover: "lead" in stories.json (1 = first story), else the first with a photo."""
    if isinstance(d.get('lead'), int) and 1 <= d['lead'] <= len(d['stories']):
        return d['lead'] - 1
    return next((i for i, s in enumerate(d['stories']) if s.get('image')), 0)


def et_date_parts(d):
    """'ኅዳር 1, 2019 ዓ.ም' -> ('ኅዳር', '1', '2019 ዓ.ም')"""
    month, rest = d['date_et'].split(' ', 1)
    day, _, year = rest.partition(',')
    return month, day.strip(), year.strip()


# ---------- cards ----------
def cover(d, total, edition):
    li = lead_index(d)
    L = d['stories'][li]
    lf = image_path(L, edition)
    bg = img_tag(L, lf, "bg") if lf else '<div class="bg noimg"></div>'
    thumbs = ""
    for i, s in enumerate(d['stories']):
        if i == li:
            continue
        f = image_path(s, edition)
        inside = img_tag(s, f) if f else s['icon']
        thumbs += f"<div class='th'>{inside}<b>{i + 2:02d}</b></div>"
    month, day, year = et_date_parts(d)
    inner = f"""{bg}<div class="shade"></div>
{top(d, '<div class="chip">DAILY · AMHARIC</div>')}
<div class="bottom">
  <div class="date"><span class="d">{esc(day)}</span><span class="m amh bold">{esc(month)}</span>
    <span class="y amh">{esc(year)}<br>{esc(d['date_gc'])}</span></div>
  <div class="lab amh"><i></i>የዕለቱ ዋና ዜና</div>
  <div class="lead-hl amh xbold">{esc(L['headline'])}</div>
  <div class="thumbs">{thumbs}<div class="more amh"><b>+{len(d['stories']) - 1}</b>ዜናዎች<br>ያንሸራትቱ →</div></div>
</div>"""
    return page(inner, "cover")


def keep_ranges(t):
    """Stop number ranges like 1–2 from breaking across two lines."""
    return re.sub(r'(\d)([–-])(\d)', '\\1\u2060\\2\u2060\\3', t)


def story(d, s, idx, total, edition):
    acc = s['color']
    f = image_path(s, edition)
    img = s.get('image') or {}
    if f:
        for key in ('credit', 'source'):
            if not img.get(key):
                print(f"  WARNING: image {img['file']} has no '{key}'")
        hero = f"""<div class="hero">{img_tag(s, f)}<div class="credit">{esc(img.get('credit', ''))}</div></div>"""
    else:
        hero = f"""<div class="hero noimg">{s['icon']}</div>"""
    frame = darken(photo_colour(f, acc), 0.30)
    vars_ = {"accent": acc, "accent-ink": darken(acc, 0.38),
             "accent-soft": f"color-mix(in srgb,{acc} 18%,white)", "frame": frame}

    note, tag = s['note'], "ማስታወሻ"
    if note.startswith(WHY_TAG):
        tag, note = WHY_TAG, note[len(WHY_TAG):].strip()
    stats = "".join(f"<div class='stat'><div class='n'>{esc(n)}</div><div class='l amh'>{esc(l)}</div></div>"
                    for n, l in (s.get('stats') or []))
    stats_html = f'<div class="stats">{stats}</div>' if stats else ""   # stats are optional: only for a strong number
    inner = f"""{hero}
{top(d)}
<div class="sheet">
  <div class="kicker amh"><i></i>{esc(s['category'])}<span class="num">{idx:02d}/{total:02d}</span></div>
  <div class="headline amh bold">{esc(s['headline'])}</div>
  <div class="body amh">{keep_ranges(esc(s['body']))}</div>
  {stats_html}
  <div class="note amh"><span class="tag">{tag}</span>{esc(note)}</div>
  <div class="spacer"></div>
  <div class="foot"><span class="src amh">ምንጭ፦ <b>{esc(s['sources'])}</b></span><span class="page">{idx}/{total}</span></div>
</div>"""
    return page(inner, "story" if stats else "story nostats", vars_)


def follow(d, total, edition):
    L = d['stories'][lead_index(d)]
    lf = image_path(L, edition)
    bg = img_tag(L, lf, "blur") if lf else ""
    chips = "".join(f"<span class='amh'>{esc(c)}</span>" for c in d['cta_lines'])
    inner = f"""{bg}
{top(d, '<div class="chip">DAILY · AMHARIC</div>')}
<div class="inner">
  <div class="kick">FOLLOW FOR DAILY NEWS</div>
  <div class="big amh xbold">{esc(d['brand'])}</div>
  <div class="tagline amh">{esc(d['tagline'])}</div>
  <div class="ctas">{chips}</div>
</div>
<div class="foot2"><span class="amh">{AI_DISCLOSURE}</span><span class="page">{total}/{total}</span></div>"""
    return page(inner, "follow")


# ---------- credits ----------
def write_credits(d, edition):
    lines = [f"# Credits — {d['date_gc']} ({d['date_et']})", ""]
    for i, s in enumerate(d['stories'], start=2):
        lines.append(f"## Card {i}: {s['headline']}")
        lines.append(f"- News sources: {s['sources']}")
        img = s.get('image')
        if img:
            adj = " · colour/contrast adjusted, cropped" if ENHANCE_PHOTOS else " · cropped"   # licences require stating changes
            lines.append(f"- Photo: `{img['file']}` — {img.get('credit', 'NO CREDIT')}{adj}")
            lines.append(f"- Photo source: {img.get('source', 'NO SOURCE LINK')}")
        else:
            lines.append("- Photo: none (emoji icon)")
        lines.append("")
    li = lead_index(d)
    lines.append(f"Cover and follow card use the photo of card {li + 2}.")
    (edition / "credits.md").write_text("\n".join(lines) + "\n", encoding='utf-8')


# ---------- editions ----------
def latest_edition():
    eds = sorted(p for p in EDITIONS.iterdir() if (p / "stories.json").exists()) if EDITIONS.exists() else []
    if not eds:
        sys.exit("No editions yet. Start one with: python3 render_cards.py --new YYYY-MM-DD")
    return eds[-1]


def new_edition(date):
    ed = EDITIONS / date
    if (ed / "stories.json").exists():
        sys.exit(f"{ed} already exists")
    prev = latest_edition() if EDITIONS.exists() and any(EDITIONS.iterdir()) else None
    (ed / "images").mkdir(parents=True, exist_ok=True)
    if prev:
        from approve import set_draft, save
        d = json.loads((prev / "stories.json").read_text(encoding="utf-8"))
        save(ed, set_draft(d))   # a new day always starts as a draft, never "approved"
        print(f"Created {ed} (stories.json copied from {prev.name} — replace the stories and dates)")
    else:
        print(f"Created {ed} — add a stories.json")


# ---------- layers for the video: photo (moves) + everything else (stays still) ----------
# Per card with a photo, render_cards also writes layers/NN_kind_photo.jpg (the photo only) and
# layers/NN_kind_fg.png (header, gradients, panel, text on a transparent background) so make_video.py
# can zoom just the photo. The frosted-glass panel keeps a still, blurred copy of the photo behind it.
LAYER_RECT = {"story": ".hero", "cover": ".card", "follow": ".card"}
LAYER_PHOTO_CSS = {   # hide everything but the photo
    "story": ".top,.sheet,.credit{visibility:hidden!important} .story .hero::after{display:none!important}",
    "cover": ".top,.bottom,.shade{visibility:hidden!important}",
    "follow": ".top,.inner,.foot2{visibility:hidden!important}",
}
LAYER_FG_CSS = {      # hide the photo, make the background transparent
    "story": ".story .hero img{clip-path:inset(478px 16px 0 16px round 40px 40px 0 0)}",
    "cover": ".cover .bg{visibility:hidden!important}",
    "follow": ".follow .blur{visibility:hidden!important}",
}
LAYER_PHOTO_SEL = {"story": ".hero img", "cover": "img.bg", "follow": "img.blur"}


def render_layers(pg, name, tmp, layers):
    """Write the photo and foreground layers of the page that is currently loaded. Returns the photo's box."""
    kind = name.split("_", 1)[-1]
    if pg.locator(LAYER_PHOTO_SEL[kind]).count() == 0 or Image is None:
        return None
    box = pg.locator(LAYER_RECT[kind]).first.bounding_box()
    st = pg.add_style_tag(content=LAYER_PHOTO_CSS[kind])
    shot = Path(tmp) / f"{name}_photo.png"
    pg.screenshot(path=str(shot), clip=box)
    st.evaluate("e => e.remove()")
    Image.open(shot).convert("RGB").save(layers / f"{name}_photo.jpg", "JPEG", quality=JPEG_QUALITY, subsampling=0)
    st = pg.add_style_tag(content="html,body,.card{background:transparent!important} " + LAYER_FG_CSS[kind])
    pg.screenshot(path=str(layers / f"{name}_fg.png"), omit_background=True)
    st.evaluate("e => e.remove()")
    return {"x": round(box["x"]), "y": round(box["y"]), "w": round(box["width"]), "h": round(box["height"])}


def render(edition):
    from runlog import log
    t0 = time.time()
    report = validate(edition)
    report.print(edition.name)
    log(edition, "validate", errors=report.errors, warnings=len(report.warnings))
    if report.errors:
        sys.exit("Fix the errors above, then render again.")
    d = json.loads((edition / "stories.json").read_text(encoding='utf-8'))
    if Image is None:
        print("  NOTE: Pillow not installed (pip install -r requirements.txt) — card frames use the story colour.")
    cards = edition / "cards"
    cards.mkdir(exist_ok=True)
    for old in [*cards.glob("*.png"), *cards.glob("*.jpg")]:
        old.unlink()
    layers = edition / "layers"
    shutil.rmtree(layers, ignore_errors=True)
    layers.mkdir()
    boxes = {}
    total = len(d['stories']) + 2
    pages = [("01_cover", cover(d, total, edition))]
    for i, s in enumerate(d['stories'], start=2):
        pages.append((f"{i:02d}_story", story(d, s, i, total, edition)))
    pages.append((f"{total:02d}_follow", follow(d, total, edition)))

    problems, overflow = 0, []
    with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
        chrome = os.environ.get("CHROME_PATH")
        if chrome:
            b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"])
        else:
            try:
                b = p.chromium.launch(channel="chrome")   # installed Google Chrome
            except Exception:
                b = p.chromium.launch()                   # Playwright's bundled Chromium
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=SCALE)
        for name, doc in pages:
            f = Path(tmp) / f"{name}.html"
            f.write_text(doc, encoding='utf-8')
            pg.goto(f.as_uri()); pg.wait_for_timeout(300)
            # text doesn't fit if any block spills past the card's bottom edge
            over = pg.evaluate(f"""[...document.querySelectorAll('.sheet > *, .bottom, .inner > *, .foot2')]
                .some(e => e.getBoundingClientRect().bottom > {H} - 20)
              || [...document.querySelectorAll('.sheet')].some(e => e.scrollHeight > e.clientHeight + 1)""")
            problems += over
            if over:
                overflow.append(name)
            if Image is not None:
                shot = Path(tmp) / f"{name}.png"
                pg.screenshot(path=str(shot))
                Image.open(shot).convert("RGB").save(cards / f"{name}.jpg", "JPEG", quality=JPEG_QUALITY,
                                                      subsampling=0, optimize=True, dpi=(144, 144))
            else:   # no Pillow: keep lossless PNG rather than Chrome's 4:2:0 JPEG
                pg.screenshot(path=str(cards / f"{name}.png"))
            box = render_layers(pg, name, tmp, layers)
            if box:
                boxes[name] = box
            print(name, "OVERFLOW! (shorten the text)" if over else "ok")
        b.close()
    (layers / "layers.json").write_text(json.dumps(boxes, indent=2), encoding="utf-8")
    write_credits(d, edition)
    print(f"\n{len(pages)} cards → {cards.relative_to(ROOT)}/   credits → {(edition / 'credits.md').relative_to(ROOT)}")
    if problems:
        print(f"{problems} card(s) overflow — fix before posting.")
    log(edition, "render", seconds=round(time.time() - t0, 1), cards=len(pages), overflow=overflow)


def main(args):
    if args[:1] == ["--new"] and len(args) == 2:
        return new_edition(args[1])
    if not args:
        return render(latest_edition())
    target = Path(args[0])
    if target.suffix == ".json":          # old style: path to a stories.json
        return render(target.resolve().parent)
    ed = EDITIONS / args[0]
    if not (ed / "stories.json").exists():
        sys.exit(f"No edition at {ed}")
    render(ed)


if __name__ == "__main__":
    main(sys.argv[1:])
