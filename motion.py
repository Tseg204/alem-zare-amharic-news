"""Animated card video ("portal" style) with HyperFrames — used by make_video.py.

Builds one HyperFrames composition from an edition's cards (the same HTML and card.css as the still
cards, so every frame looks like the real card), animates it with motion/motion.js and renders a
silent 1080×1350 MP4. make_video.py adds the narration, music and DRAFT banner on top.

What moves (chosen by the owner, 10 Nov 2026):
- story cards: photo pushes in slowly; the frosted panel opens as a growing circle; a band of light
  runs through the headline and each body sentence (left to right) when the voice reaches it;
  stats burst out of a thin ring and count up; the note tag pops out of a ripple; sources fade in.
- cover: date, label and lead headline (light sweep), thumbnails pop in one by one.
- follow card: brand (light sweep), tagline, buttons pop in.

Needs Node.js + the pinned packages in motion/ (cd motion && npm ci) and ffmpeg on PATH
(brew install ffmpeg). available() says whether all of that is there; otherwise make_video.py
falls back to the still-card video.
"""
import json, os, re, shutil, subprocess, tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

import render_cards as rc

ROOT = Path(__file__).resolve().parent
MOTION = ROOT / "motion"
CLI = MOTION / "node_modules" / ".bin" / "hyperframes"
W, H = rc.W, rc.H                 # 1080×1350, the cards' own size
STORY_LEAD = 1.0                  # seconds before the voice on a story card (the panel opens first)


def available():
    return CLI.exists() and shutil.which("node") and shutil.which("ffmpeg") and shutil.which("ffprobe")


def pauses(exe, mp3):
    """Headline end and body-sentence starts (seconds into the clip), from the silences in the narration."""
    log = subprocess.run([exe, "-hide_banner", "-i", str(mp3), "-af", "silencedetect=noise=-35dB:d=0.3",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", log).groups()
    dur = int(h) * 3600 + int(m) * 60 + float(s)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    cuts = [(a, b) for a, b in zip(starts, ends) if b - a > 0.6 and b < dur - 0.2]   # not the end silence
    head_end = cuts[0][0] if cuts else dur * 0.2
    return head_end, [b for a, b in cuts] or [head_end + 0.5]


CHECK_LIMIT = 12.0                # mean grey-level difference (0–255) above which a card "doesn't match"


def check(edition, names, scenes, fade, mp4, exe):
    """Compare each card's last settled frame in the video with its still card (lower part only:
    headline, text, stats, note, sources; the photo moves, so it is left out). Returns the cards whose
    layout differs, e.g. a line wrapped differently and pushed the sources off the card."""
    from PIL import Image, ImageChops, ImageStat
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (name, sc) in enumerate(zip(names, scenes)):
            still = edition / "cards" / f"{name}.jpg"
            if not still.exists():
                continue
            last = i == len(names) - 1
            t = sc["start"] + sc["dur"] - (0.1 if last else fade + 0.1)
            f = Path(tmp) / f"{name}.png"
            subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", str(mp4),
                            "-frames:v", "1", str(f)], check=True)
            a = Image.open(f).convert("L").resize((270, 338))
            b = Image.open(still).convert("L").resize((270, 338))
            box = (0, int(338 * 0.55), 270, int(338 * 0.97))
            diff = ImageStat.Stat(ImageChops.difference(a.crop(box), b.crop(box))).mean[0]
            if diff > CHECK_LIMIT:
                bad.append((name, round(diff, 1)))
    return bad


def _words(txt, cls):
    return " ".join(f'<span class="{cls}">{w}</span>' for w in txt.split())


def _animatable(card):
    """Mark up the card HTML so words, sentences, numbers and the note tag can move on their own."""
    one = lambda pat, fn, s: re.sub(pat, fn, s, count=1, flags=re.S)
    card = one(r'(<div class="headline[^>]*>)(.*?)(</div>)', lambda m: m[1] + _words(m[2], "hw") + m[3], card)
    card = one(r'(<div class="lead-hl[^>]*>)(.*?)(</div>)', lambda m: m[1] + _words(m[2], "hw") + m[3], card)
    card = one(r'(<div class="big[^>]*>)(.*?)(</div>)', lambda m: m[1] + _words(m[2], "hw") + m[3], card)
    card = one(r'(<div class="body[^>]*>)(.*?)(</div>)',
               lambda m: m[1] + " ".join(f'<span class="sent">{_words(x.strip(), "bw")}</span>'
                                         for x in re.findall(r"[^።]+።?", m[2]) if x.strip()) + m[3], card)
    card = one(r'(<div class="note[^>]*>)(<span class="tag">.*?</span>)(.*?)(</div>)',
               lambda m: m[1] + f'<span class="tagwrap"><i class="ring"></i>{m[2]}</span>' + _words(m[3], "nw") + m[4],
               card)
    card = re.sub(r"(<div class='n'>)(.*?)(</div>)",
                  lambda m: m[1] + f'<span class="numwrap"><span class="num">{m[2]}</span><i class="ring"></i></span>' + m[3],
                  card)
    return card


CSS = """
@font-face { font-family:'Apple Color Emoji'; src: local('Apple Color Emoji'); }
@font-face { font-family:'Noto Color Emoji'; src: local('Apple Color Emoji'); }
@font-face { font-family:'Segoe UI Emoji'; src: local('Apple Color Emoji'); }
html, body { margin:0; width:%dpx; height:%dpx; overflow:hidden; background:#0B0B0E; }
#root { position:relative; width:%dpx; height:%dpx; overflow:hidden; }
.scene { position:absolute; inset:0; }
/* words stay inline (no boxes) so the text wraps exactly like the still card; the sweep only changes
   opacity and glow, which work on inline text */
/* splitting text into word spans can make a line a fraction of a pixel wider than on the still card; a line
   that exactly filled the card would then wrap and push the sources off. 1px of slack absorbs that without changing any other line break (more slack lets extra words onto a line). */
.headline, .lead-hl, .big, .body, .note { margin-right:-1px; }
.numwrap, .tagwrap { position:relative; display:inline-block; }
.num { display:inline-block; transform-origin:0%% 50%%; }
.tag { transform-origin:50%% 50%%; }
.ring { position:absolute; left:50%%; top:50%%; width:240px; height:240px; margin:-120px 0 0 -120px; border-radius:50%%;
        border:3px solid var(--accent, #fff); box-shadow:0 0 16px var(--accent, #fff); opacity:0; pointer-events:none; }
.tagwrap .ring { width:180px; height:180px; margin:-90px 0 0 -90px; }
""" % (W, H, W, H)


def render(edition, d, names, scenes, total, fade, out_mp4, exe):
    """scenes[i] = {start, dur, voice (s, or None), clip (narration mp3 or None)} for card names[i]."""
    total_cards = len(d["stories"]) + 2
    with tempfile.TemporaryDirectory() as tmp:
        build = Path(os.environ.get("MOTION_BUILD_DIR") or tmp)      # set MOTION_BUILD_DIR to keep the build for checking
        if build.exists() and build != Path(tmp):
            shutil.rmtree(build)
        (build / "assets").mkdir(parents=True)
        shutil.copy(MOTION / "node_modules/gsap/dist/gsap.min.js", build / "assets")
        css, parts, conf, images = None, [], [], {}
        for i, (name, sc) in enumerate(zip(names, scenes)):
            kind = name.split("_", 1)[-1]
            if kind == "cover":
                page = rc.cover(d, total_cards, edition)
            elif kind == "follow":
                page = rc.follow(d, total_cards, edition)
            else:
                n = int(name[:2]) - 1                 # 02_story → story 1
                page = rc.story(d, d["stories"][n - 1], n + 1, total_cards, edition)
            css = css or re.search(r"<style>(.*?)</style>", page, re.S).group(1)
            card = re.search(r"<body>(.*)</body>", page, re.S).group(1)

            def local(m):                              # photos → assets/ inside the build folder
                uri = m.group(1)
                if uri not in images:
                    src = Path(unquote(urlparse(uri).path))
                    images[uri] = f"assets/img{len(images)}{src.suffix}"
                    shutil.copy(src, build / images[uri])
                return f'src="{images[uri]}"'
            card = re.sub(r'src="(file://[^"]+)"', local, card)
            card = _animatable(card)
            sid = f"s{i}"
            parts.append(f'<div id="{sid}" class="scene clip" data-start="{sc["start"]:.3f}" '
                         f'data-duration="{sc["dur"]:.3f}">{card}</div>')
            c = {"id": sid, "type": "story" if kind == "story" else kind, "start": round(sc["start"], 3),
                 "dur": round(sc["dur"], 3), "voice": round(sc["voice"], 3) if sc.get("voice") is not None else None}
            if c["type"] == "story" and sc.get("clip"):
                head_end, sents = pauses(exe, sc["clip"])
                c["headEnd"], c["sents"] = round(head_end, 2), [round(x, 2) for x in sents]
            conf.append(c)
        doc = f"""<!doctype html>
<html lang="am">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<script src="assets/gsap.min.js"></script>
<style>{css}{CSS}</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-width="{W}" data-height="{H}">
{chr(10).join(parts)}
</div>
<script>window.MOTION = {json.dumps({"total": round(total, 3), "fade": fade, "scenes": conf})};
{(MOTION / "motion.js").read_text(encoding="utf-8")}</script>
</body>
</html>
"""
        (build / "index.html").write_text(doc, encoding="utf-8")
        lint = subprocess.run([str(CLI), "lint", str(build)], cwd=MOTION, capture_output=True, text=True)
        for line in (lint.stdout + lint.stderr).splitlines():
            if "✗" in line:
                print("  motion lint:", line.strip())
        print(f"Animating {len(names)} cards with HyperFrames ({total:.0f} s; a few minutes)…")
        r = subprocess.run([str(CLI), "render", str(build), "-o", str(out_mp4), "-q", "delivery", "--fps", "30"],
                           cwd=MOTION, capture_output=True, text=True)
        if r.returncode or not Path(out_mp4).exists():
            raise RuntimeError("HyperFrames render failed:\n" + (r.stdout + r.stderr)[-2000:])
