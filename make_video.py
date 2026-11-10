"""Turn an edition's rendered cards into a vertical video (1080×1920 MP4) for
YouTube Shorts / Instagram Reels / TikTok, with Amharic narration and royalty-free
background music.

Each card is centred on a blurred copy of itself, with a slow zoom and a soft
crossfade to the next card. With narration, each card stays on screen as long as
its narration (+ short pauses) and the music plays quietly underneath.

    editions/2026-11-10/video/short.mp4     (written by this script)

Approval gate: only an edition approved by the owner (python3 approve.py) gets video/short.mp4.
A draft — or an approved edition edited afterwards — gets video/short_DRAFT.mp4 with a red
"DRAFT" banner, for reviewing the narration before approval. It must never be posted.
    editions/2026-11-10/audio/              narration clips + narration.txt (the read text)
    editions/2026-11-10/credits.md          gets a "Music / voice" section

Narration: Azure neural voice (see narrate.py; key in .env). Voice: --voice mekdes|ameha,
or "voice": "ameha" in stories.json, or AZURE_SPEECH_VOICE in .env. Default: ameha.
Music: tracks in music/, listed in music/tracks.json. Pick one per day with
"music": "<file>" in stories.json; otherwise tracks rotate by date.

Usage:
    python3 make_video.py                         latest edition
    python3 make_video.py 2026-11-10              that date's edition
    options:  --voice ameha   --no-voice   --silent (no music)   --out name.mp4

Needs ffmpeg: comes with the imageio-ffmpeg package (pip install -r requirements.txt).
Set FFMPEG=/path/to/ffmpeg to use a different one.
Render the cards first (python3 render_cards.py).
"""
import math, json, os, re, shutil, subprocess, sys, tempfile, time
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from render_cards import ROOT, EDITIONS, latest_edition
import narrate
from approve import approval_state
from runlog import log

MUSIC = ROOT / "music"
VW, VH = 1080, 1920          # video frame
FPS = 30
FADE = 0.6                   # crossfade between cards (s)
ZOOM = 0.03                  # slow zoom-in over a whole card without a photo (3%)
PHOTO_ZOOM = 0.06            # slow zoom-in of the photo only, text and panel stay still (6%)
VOLUME = 0.8                 # music level without narration (1.0 = original)
LOOP_XFADE = 4               # seconds of crossfade when a track has to loop
VOLUME_UNDER_VOICE = 0.11    # music level under narration
SECONDS = {"cover": 4.0, "story": 9.0, "follow": 4.0}   # card length without narration
VOICE_LEAD, VOICE_TAIL = 0.4, 0.9                      # pause before / after narration


def ffmpeg_bin():
    exe = os.environ.get("FFMPEG")
    if not exe:
        try:
            import imageio_ffmpeg          # bundles its own ffmpeg (pip install imageio-ffmpeg)
            exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            exe = shutil.which("ffmpeg")
    if not exe:
        sys.exit("ffmpeg not found — run:  pip install -r requirements.txt")
    return exe


def audio_seconds(exe, f):
    err = subprocess.run([exe, "-hide_banner", "-i", str(f)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def frame(card_png, out_png):
    """Card centred on a blurred, darkened, enlarged copy of itself (built at 2× so the zoom stays sharp)."""
    FW, FH = VW * 2, VH * 2
    card = Image.open(card_png).convert("RGB")
    scale = max(FW / card.width, FH / card.height)
    bg = card.resize((round(card.width * scale), round(card.height * scale)), Image.LANCZOS)
    left, top = (bg.width - FW) // 2, (bg.height - FH) // 2
    bg = bg.crop((left, top, left + FW, top + FH)).filter(ImageFilter.GaussianBlur(80))
    bg = ImageEnhance.Brightness(bg).enhance(0.6)
    card = card.resize((FW, round(card.height * FW / card.width)), Image.LANCZOS)
    bg.paste(card, (0, (FH - card.height) // 2))
    bg.save(out_png)


def pick_track(d, edition):
    """Returns (path, info) or (None, None)."""
    listing = MUSIC / "tracks.json"
    tracks = json.loads(listing.read_text(encoding="utf-8")) if listing.exists() else []
    tracks = [t for t in tracks if (MUSIC / t["file"]).exists()]
    if not tracks:
        return None, None
    want = d.get("music")
    if want:
        for t in tracks:
            if t["file"] == want:
                return MUSIC / t["file"], t
        print(f"  WARNING: music '{want}' not in music/tracks.json (or file missing) — rotating instead")
    for t in tracks:                       # "default": true in tracks.json = used every day
        if t.get("default"):
            return MUSIC / t["file"], t
    try:
        n = date.fromisoformat(edition.name).toordinal()
    except ValueError:
        n = 0
    t = tracks[n % len(tracks)]
    return MUSIC / t["file"], t


def write_credits(edition, info, voice):
    f = edition / "credits.md"
    text = f.read_text(encoding="utf-8") if f.exists() else ""
    text = re.split(r"\n## Music \(video\)|\n## Video audio", text)[0].rstrip() + "\n"
    lines = []
    if info:
        lines += [f"- Music: {info.get('title', '?')} — {info.get('artist', '?')} · {info.get('licence', 'NO LICENCE')}",
                  f"- Music source: {info.get('source', 'NO SOURCE LINK')}"]
        if info.get("attribution"):
            lines.append(f"- Attribution (put in the caption): {info['attribution']}")
    if voice:
        lines.append(f"- Narration: AI voice (Microsoft Azure, {narrate.VOICES[voice]}) — "
                     "turn on the platform's AI-generated label when posting")
    if lines:
        text += "\n## Video audio\n" + "\n".join(lines) + "\n"
    f.write_text(text, encoding="utf-8")


def draft_banner(out_png):
    """Red 'DRAFT' banner burned into unapproved videos so they can't be posted by mistake."""
    font = ImageFont.load_default(size=46)
    text = "DRAFT \u00b7 NOT APPROVED"
    w = round(font.getlength(text)) + 80
    im = Image.new("RGBA", (w, 96), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, 95), radius=22, fill=(200, 30, 30, 235))
    ImageDraw.Draw(im).text((w // 2, 48), text, font=font, fill="white", anchor="mm")
    im.save(out_png)


def make_video(edition, silent=False, voice=None, no_voice=False, out_name="short.mp4"):
    started = time.time()
    d = json.loads((edition / "stories.json").read_text(encoding="utf-8"))
    state = approval_state(edition, d)
    draft = state != "approved"
    if draft:
        why = ("stories.json or a photo changed after approval" if state == "changed"
               else "this edition is not approved yet")
        print(f"  DRAFT: {why} — making a draft video with a DRAFT banner (not for posting).")
        print(f"         After review, approve with: python3 approve.py {edition.name}")
        if out_name == "short.mp4":
            out_name = "short_DRAFT.mp4"
            stale = edition / "video" / "short.mp4"
            if stale.exists():
                stale.unlink()   # an older final video no longer matches the stories
                print("         (removed the old video/short.mp4 — it no longer matches the stories)")
    cards = sorted([*(edition / "cards").glob("*.jpg"), *(edition / "cards").glob("*.png")])
    if not cards:
        sys.exit(f"No cards in {edition / 'cards'} — run render_cards.py first")
    exe = ffmpeg_bin()
    names = [c.stem for c in cards]

    clips = None
    if not no_voice:
        voice = narrate.pick_voice(d, voice)
        clips = narrate.narrate(edition, d, names, voice)
    if not clips:
        voice = None

    # card lengths: fixed, or as long as the narration needs
    durs = [SECONDS.get(n.split("_", 1)[-1], SECONDS["story"]) for n in names]
    voice_at = []
    if clips:
        start = 0.0
        for i, c in enumerate(clips):
            fade_in = FADE if i else 0.0
            need = fade_in + VOICE_LEAD + audio_seconds(exe, c) + VOICE_TAIL + FADE
            durs[i] = max(need, 3.0)
            voice_at.append(start + fade_in + VOICE_LEAD)
            start += durs[i] - FADE
    total = sum(durs) - FADE * (len(cards) - 1)

    track, info = (None, None) if silent else pick_track(d, edition)
    if not silent and not track:
        print("  WARNING: no music found in music/ (see music/tracks.json)")

    out_dir = edition / "video"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / out_name

    with tempfile.TemporaryDirectory() as tmp:
        args, chains = [exe, "-y", "-loglevel", "error"], []
        layers = edition / "layers"
        boxes = json.loads((layers / "layers.json").read_text()) if (layers / "layers.json").exists() else {}
        k = 0                                     # index of the next ffmpeg input
        for i, (c, dur) in enumerate(zip(cards, durs)):
            fp = Path(tmp) / f"{i:02d}.png"
            frame(c, fp)
            n = round(dur * FPS)
            name = c.stem
            box = boxes.get(name)
            photo, fg = layers / f"{name}_photo.jpg", layers / f"{name}_fg.png"
            if box and photo.exists() and fg.exists():
                # photo-only zoom: still backdrop + still card, the photo moves, header/panel/text stay put
                im = Image.open(c)
                cy = (VH - round(im.height * VW / im.width)) // 2          # card's top edge in the video frame
                args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(fp),
                         "-i", str(photo),
                         "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(fg)]
                b, ph, f = k, k + 1, k + 2
                k += 3
                chains.append(
                    f"[{b}:v]scale={VW}:{VH},setsar=1,format=rgba[b{i}];"
                    f"[{ph}:v]zoompan=z='1+{PHOTO_ZOOM}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                    f":d={n}:s={box['w']}x{box['h']}:fps={FPS},setsar=1,format=rgba[p{i}];"
                    f"[{f}:v]scale={VW}:{round(im.height * VW / im.width)},setsar=1,format=rgba[f{i}];"
                    f"[b{i}][p{i}]overlay=x={box['x']}:y={cy + box['y']}:shortest=1[o{i}];"
                    f"[o{i}][f{i}]overlay=x=0:y={cy}:shortest=1,trim=end_frame={n},setpts=PTS-STARTPTS,"
                    f"format=yuv420p[v{i}]")
                continue
            args += ["-i", str(fp)]
            # whole card zooms (cards without a photo); upscale first so the slow zoom doesn't jitter
            chains.append(
                f"[{k}:v]scale={VW * 2}:{VH * 2},"
                f"zoompan=z='1+{ZOOM}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={n}:s={VW}x{VH}:fps={FPS},setsar=1,format=yuv420p[v{i}]")
            k += 1
        prev, offset = "v0", 0.0
        for i in range(1, len(cards)):
            offset += durs[i - 1] - FADE
            chains.append(f"[{prev}][v{i}]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[x{i}]")
            prev = f"x{i}"
        if draft:
            banner = Path(tmp) / "draft.png"
            draft_banner(banner)
            args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total:.3f}", "-i", str(banner)]
            chains.append(f"[{prev}][{k}:v]overlay=x=(W-w)/2:y=70:shortest=1[wm]")
            prev = "wm"
            k += 1

        nxt = k
        audio_parts = []
        if track:
            args += ["-i", str(track)]
            vol = VOLUME_UNDER_VOICE if clips else VOLUME
            t0 = float(info.get("start", 0))   # tracks.json "start" = seconds to skip at the beginning
            dur = audio_seconds(exe, track)
            tail = (f"volume={vol},aformat=sample_rates=44100:channel_layouts=stereo,"
                    f"afade=t=in:d=1,afade=t=out:st={total - 2:.3f}:d=2[music]")
            if dur >= t0 + total:
                chains.append(f"[{nxt}:a]atrim={t0:.3f}:{t0 + total:.3f},asetpts=PTS-STARTPTS,{tail}")
            else:
                # track too short: loop it with a smooth crossfade (LOOP_XFADE s) instead of a hard cut
                X = LOOP_XFADE
                n = 1 + math.ceil((total - (dur - t0)) / (dur - X))
                print(f"  NOTE: track ends before the video — looping with a {X:g}s crossfade ({n} passes)")
                outs = "".join(f"[m{j}]" for j in range(n))
                chains.append(f"[{nxt}:a]asplit={n}{outs}")
                for j in range(n):
                    a = t0 if j == 0 else 0
                    chains.append(f"[m{j}]atrim={a:.3f}:{dur:.3f},asetpts=PTS-STARTPTS,"
                                  f"aformat=sample_rates=44100:channel_layouts=stereo[p{j}]")
                prev_a = "p0"
                for j in range(1, n):
                    chains.append(f"[{prev_a}][p{j}]acrossfade=d={X}:c1=tri:c2=tri[c{j}]")
                    prev_a = f"c{j}"
                chains.append(f"[{prev_a}]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,{tail}")
            audio_parts.append("[music]")
            nxt += 1
        if clips:
            for k, (c, at) in enumerate(zip(clips, voice_at)):
                args += ["-i", str(c)]
                ms = round(at * 1000)
                chains.append(f"[{nxt}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                              f"adelay={ms}|{ms}[n{k}]")
                nxt += 1
            chains.append("".join(f"[n{k}]" for k in range(len(clips))) +
                          f"amix=inputs={len(clips)}:normalize=0,apad,atrim=0:{total:.3f}[voice]")
            audio_parts.append("[voice]")
        # final level: standard social-media loudness (-14 LUFS)
        norm = "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100"
        if len(audio_parts) == 2:
            chains.append(f"[music][voice]amix=inputs=2:normalize=0,{norm}[aout]")
        elif audio_parts:
            chains.append(f"{audio_parts[0]}{norm}[aout]")

        args += ["-filter_complex", ";".join(chains), "-map", f"[{prev}]"]
        if audio_parts:
            args += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
        args += ["-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                 "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart", str(out)]
        print(f"Making video from {len(cards)} cards ({total:.0f} s)"
              + (f", narration: {narrate.VOICES[voice]}" if voice else "") + "…")
        subprocess.run(args, check=True)

    write_credits(edition, info, voice)
    import share
    share.write_captions(edition)     # refresh captions.txt (music credit, approval state)
    log(edition, "video", seconds=round(time.time() - started, 1), file=out.name, draft=draft,
        length_s=round(total, 1), voice=voice or "none", music=(info or {}).get("title", "none"),
        tts_new_clips=narrate.STATS["new_clips"], tts_cached_clips=narrate.STATS["cached_clips"],
        tts_chars_sent=narrate.STATS["chars_sent"])
    print(f"video → {out}" + ("   (DRAFT — do not post)" if draft else ""))
    if info:
        print(f"music: {info.get('title')} — {info.get('artist')} ({info.get('licence')})")
        if info.get("attribution"):
            print(f"  put in the caption: {info['attribution']}")
    if voice:
        print(f"narration text → {edition / 'audio' / 'narration.txt'}")
    if total > 60:
        print(f"  NOTE: video is {total:.0f} s (over 60 s) — on YouTube, a claimed track would block it")


def main(args):
    opts = {"silent": False, "voice": None, "no_voice": False, "out_name": "short.mp4"}
    rest, it = [], iter(args)
    for a in it:
        if a == "--silent": opts["silent"] = True
        elif a == "--no-voice": opts["no_voice"] = True
        elif a == "--voice": opts["voice"] = next(it, None)
        elif a == "--out": opts["out_name"] = next(it, "short.mp4")
        else: rest.append(a)
    if not rest:
        return make_video(latest_edition(), **opts)
    ed = EDITIONS / rest[0]
    if not (ed / "stories.json").exists():
        sys.exit(f"No edition at {ed}")
    make_video(ed, **opts)


if __name__ == "__main__":
    main(sys.argv[1:])
