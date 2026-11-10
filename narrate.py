"""Amharic narration for the video, via Azure neural text-to-speech.

Needs a .env file in the project folder (never share it):
    AZURE_SPEECH_KEY=...
    AZURE_SPEECH_REGION=uksouth
Optional: AZURE_SPEECH_VOICE=ameha   (or mekdes)

What is read: cover = brand, date, cover title; each story = headline + body;
last card = a short "follow us" line. The texts are saved to
editions/<date>/audio/narration.txt for review, and each clip is cached as an MP3
(only re-made when its text or voice changes).
"""
import hashlib, json, os, re, urllib.error, urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VOICES = {"mekdes": "am-ET-MekdesNeural", "ameha": "am-ET-AmehaNeural"}
DEFAULT_VOICE = "ameha"
SENTENCE_PAUSE_MS = 450    # pause after each sentence
HEADLINE_PAUSE_MS = 900    # gap between headline/title and what follows
FOLLOW_TEXT ="ለዕለታዊ የዓለም ዜና {brand}ን ይከተሉ። ዜናውን ያጋሩ፣ አስተያየትዎንም ይስጡን።"


def load_env():
    f = ROOT / ".env"
    env = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return {**env, **{k: v for k, v in os.environ.items() if k.startswith("AZURE_SPEECH")}}


# How acronyms / Latin-letter names are read. Add new ones here (the owner reviews them in
# audio/narration.txt). Anything ALL-CAPS not listed is spelled letter by letter and a warning is printed.
PRONOUNCE = {
    "UNHCR": "የተባበሩት መንግሥታት የስደተኞች ኮሚሽን",
    "COP31": "ሠላሳ አንደኛው የተመድ የአየር ንብረት ጉባኤ",
    "WHO": "የዓለም ጤና ድርጅት",
    "CDC": "የአሜሪካ የበሽታ መቆጣጠሪያ ማዕከል",
    "UN": "የተባበሩት መንግሥታት",
    "AU": "የአፍሪካ ኅብረት",
    "EU": "የአውሮፓ ኅብረት",
    "FIFA": "ፊፋ",
    "NATO": "ናቶ",
    "IMF": "የዓለም አቀፉ የገንዘብ ድርጅት",
    "USA": "አሜሪካ",
}
LETTERS = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "ኤ ቢ ሲ ዲ ኢ ኤፍ ጂ ኤች አይ ጀ ኬ ኤል ኤም ኤን ኦ ፒ ኪው አር ኤስ ቲ ዩ ቪ ደብሊው ኤክስ ዋይ ዜድ".split()))


def _say_acronym(m):
    tok = m.group(0)
    if tok in PRONOUNCE:
        return PRONOUNCE[tok]
    print(f"  WARNING: '{tok}' has no entry in PRONOUNCE (narrate.py) — spelled letter by letter")
    return " ".join(LETTERS[c] if c in LETTERS else c for c in tok)


def speakable(text):
    """Small fixes so the voice reads acronyms, dates, ranges and dashes naturally."""
    text = re.sub(r"\b[A-Z][A-Z0-9]{1,}\b", _say_acronym, text)
    t = text.replace("ዓ.ም.", "ዓመተ ምሕረት").replace("ዓ.ም", "ዓመተ ምሕረት")
    t = re.sub(r"(\d)\s*[–-]\s*(\d)", r"\1 እስከ \2", t)      # 1–2  → 1 እስከ 2
    t = re.sub(r"\s*[–—]\s*", " ", t)                          # word–word → word word
    t = t.replace("«", "").replace("»", "").replace("“", "").replace("”", "")
    return re.sub(r"\s+", " ", t).strip()


def scripts(d, card_names):
    """Narration text per card, in card order."""
    stories = iter(d["stories"])
    out = []
    for name in card_names:
        kind = name.split("_", 1)[-1]
        if kind == "cover":
            parts = d.get("cover_speech") or [f"{d['brand']}። {d['date_et']}።", f"{d.get('cover_title', '')}።"]
        elif kind == "follow":
            parts = [FOLLOW_TEXT.format(brand=d["brand"])]
        else:
            s = next(stories)
            # "speech" = [headline, body] written for the ear (numbers/acronyms in words);
            # falls back to the card text. The "ለምን ያገባናል?" note is never read.
            parts = s.get("speech") or [f"{s['headline']}።", s["body"]]
        # one part per line: the line break becomes the long pause (title/headline → rest)
        out.append("\n".join(speakable(p.replace("።።", "።")) for p in parts if p.strip()))
    return out


def pick_voice(d, override=None, env=None):
    env = env or load_env()
    name = (override or d.get("voice") or env.get("AZURE_SPEECH_VOICE") or DEFAULT_VOICE).lower()
    if name not in VOICES:
        raise SystemExit(f"Unknown voice '{name}' — choose one of: {', '.join(VOICES)}")
    return name


def tts(text, voice, out_mp3, env):
    key, region = env.get("AZURE_SPEECH_KEY"), env.get("AZURE_SPEECH_REGION")
    def with_pauses(line):
        sents = [s.strip() for s in re.split(r"(?<=።)", line) if s.strip()]
        return f"<break time='{SENTENCE_PAUSE_MS}ms'/>".join(escape(s) for s in sents)
    body = f"<break time='{HEADLINE_PAUSE_MS}ms'/>".join(
        with_pauses(l) for l in text.split("\n") if l.strip())
    ssml = (f"<speak version='1.0' xml:lang='am-ET'><voice name='{VOICES[voice]}'>"
            f"<prosody rate='-5%'>{body}</prosody></voice></speak>")
    req = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"),
        headers={"Ocp-Apim-Subscription-Key": key,
                 "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "audio-24khz-160kbitrate-mono-mp3",
                 "User-Agent": "alem-zare-cards"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out_mp3.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Azure text-to-speech failed ({e.code} {e.reason}) — check .env key/region")


def narrate(edition, d, card_names, voice):
    """Returns a list of MP3 paths (one per card), or None if no Azure key."""
    env = load_env()
    if not env.get("AZURE_SPEECH_KEY") or env["AZURE_SPEECH_KEY"].startswith("paste"):
        print("  NOTE: no Azure key in .env — video without narration")
        return None
    texts = scripts(d, card_names)
    adir = edition / "audio"
    adir.mkdir(exist_ok=True)
    clips = []
    for name, text in zip(card_names, texts):
        h = hashlib.sha1(f"{voice}|{text}".encode()).hexdigest()[:10]
        mp3 = adir / f"{name}_{voice}_{h}.mp3"
        if not mp3.exists():
            for old in adir.glob(f"{name}_{voice}_*.mp3"):
                old.unlink()
            tts(text, voice, mp3, env)
        clips.append(mp3)
    (adir / "narration.txt").write_text(
        f"Voice: {VOICES[voice]}\n\n" + "\n\n".join(f"[{n}]\n{t}" for n, t in zip(card_names, texts)) + "\n",
        encoding="utf-8")
    return clips
