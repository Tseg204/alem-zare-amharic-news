"""Check one day's stories.json against the project's rules before anything is rendered.

The rules come from CLAUDE.md; here they are checked by code so nothing slips through.
  ERROR   = must be fixed (render_cards.py stops)
  WARNING = worth a look, but rendering continues

Usage:
    python3 validate.py               check the latest edition
    python3 validate.py 2026-11-10    check that date's edition
Exit code 0 = no errors, 1 = errors found (handy for scripts and automation later).
"""
import json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EDITIONS = ROOT / "editions"

N_STORIES = 5
MAX_STATS = 2
HEADLINE_WORDS = 8                      # "≤ ~8 words" → more than this is a warning
WHY_TAG = "ለምን ያገባናል?"

# Quotation marks of any kind: cards and narration use reported speech only.
QUOTES = re.compile(r'["«»“”„‟‹›‘’‚]')
# Flag emoji are pairs of "regional indicator" letters (U+1F1E6–U+1F1FF).
FLAG = re.compile("[\U0001F1E6-\U0001F1FF]")
# What the voice must never see: Latin letters, digits (Western or Ethiopic) and symbols it reads badly.
NOT_SPEAKABLE = re.compile(r"[A-Za-z0-9፩-፼%$€£&@#/+=<>~^*_|\\]")
HEX_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Photo licences we accept (checked in the "credit" text). NC = non-commercial, ND = no changes
# (we crop and tone-adjust every photo, so ND is out too).
LICENCE_OK = re.compile(r"\b(CC0|CC BY(-SA)?( \d\.\d)?|Public domain|Unsplash|Pexels)\b", re.I)
LICENCE_BAD = re.compile(r"\b(NC|ND)\b|non-?commercial|no derivatives", re.I)

TOP_FIELDS = ["brand", "tagline", "date_et", "date_gc", "cover_title", "cta_lines", "stories"]
STORY_TEXT = ["category", "color", "icon", "headline", "body", "note", "sources"]


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"{where}: {msg}")

    def print(self, name):
        for e in self.errors:
            print(f"  ERROR    {e}")
        for w in self.warnings:
            print(f"  WARNING  {w}")
        verdict = "OK" if not self.errors else "FAILED"
        print(f"validate {name}: {verdict} — {len(self.errors)} error(s), {len(self.warnings)} warning(s)")


def is_text(v):
    return isinstance(v, str) and v.strip() != ""


def snippet(text, m):
    """A few characters around a match, so the owner can find it quickly."""
    a, b = max(0, m.start() - 12), min(len(text), m.end() + 12)
    return f"…{text[a:b]}…"


# ---------- 2.1 structure ----------
def check_structure(d, edition, r):
    for f in TOP_FIELDS:
        if f not in d:
            r.error("top", f"missing field '{f}'")
    for f in ["brand", "tagline", "date_et", "date_gc", "cover_title"]:
        if f in d and not is_text(d[f]):
            r.error("top", f"'{f}' must be non-empty text")
    if "cta_lines" in d and not (isinstance(d["cta_lines"], list) and all(is_text(c) for c in d["cta_lines"])):
        r.error("top", "'cta_lines' must be a list of text lines")

    # date_gc must match the folder name — catches a forgotten date after `--new`.
    try:
        folder_date = datetime.strptime(edition.name, "%Y-%m-%d").date()
        if is_text(d.get("date_gc")):
            if datetime.strptime(d["date_gc"].strip(), "%d %b %Y").date() != folder_date:
                r.error("top", f"date_gc '{d['date_gc']}' does not match the folder date {edition.name}")
    except ValueError:
        r.error("top", f"date_gc '{d.get('date_gc')}' should look like '10 Nov 2026'")

    stories = d.get("stories")
    if not isinstance(stories, list):
        r.error("top", "'stories' must be a list")
        return []
    if len(stories) != N_STORIES:
        r.error("top", f"{len(stories)} stories — expected {N_STORIES}")

    lead = d.get("lead")
    if lead is not None and not (isinstance(lead, int) and 1 <= lead <= len(stories)):
        r.error("top", f"'lead' must be a story number 1–{len(stories)}, got {lead!r}")

    for i, s in enumerate(stories, 1):
        w = f"story {i}"
        if not isinstance(s, dict):
            r.error(w, "must be an object { … }")
            continue
        for f in STORY_TEXT:
            if not is_text(s.get(f)):
                r.error(w, f"missing or empty '{f}'")
        if is_text(s.get("color")) and not HEX_COLOUR.match(s["color"]):
            r.error(w, f"color '{s['color']}' should look like #4FA3FF")
        stats = s.get("stats")
        if not isinstance(stats, list):
            r.error(w, "'stats' must be a list (use [] for none)")
        else:
            if len(stats) > MAX_STATS:
                r.error(w, f"{len(stats)} stats — at most {MAX_STATS}")
            for j, st in enumerate(stats, 1):
                if not (isinstance(st, list) and len(st) == 2 and all(is_text(x) for x in st)):
                    r.error(w, f"stat {j} must be [number, label]")
    return [s for s in stories if isinstance(s, dict)]


def check_not_copied(d, edition, r):
    """`--new` copies yesterday's stories.json: make sure the stories were actually replaced."""
    earlier = sorted(p for p in EDITIONS.iterdir()
                     if p.name < edition.name and (p / "stories.json").exists())
    if not earlier:
        return
    try:
        prev = json.loads((earlier[-1] / "stories.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    old = {s.get("headline") for s in prev.get("stories", []) if isinstance(s, dict)}
    for i, s in enumerate(d.get("stories", []), 1):
        if isinstance(s, dict) and s.get("headline") in old:
            r.error(f"story {i}", f"same headline as {earlier[-1].name} — still the copied story?")


# ---------- 2.2 editorial ----------
def card_texts(d, stories):
    """Every piece of text that appears on a card or is read aloud, with a label."""
    yield "top.cover_title", d.get("cover_title")
    for k, line in enumerate(d.get("cta_lines") or [], 1):
        yield f"top.cta_lines[{k}]", line
    for k, line in enumerate(d.get("cover_speech") or [], 1):
        yield f"top.cover_speech[{k}]", line
    for i, s in enumerate(stories, 1):
        for f in ["category", "headline", "body", "note"]:
            yield f"story {i}.{f}", s.get(f)
        for j, st in enumerate(s.get("stats") or [], 1):
            if isinstance(st, list):
                for x in st:
                    yield f"story {i}.stat {j}", x
        for k, line in enumerate(s.get("speech") or [], 1):
            yield f"story {i}.speech[{k}]", line


def check_editorial(d, stories, r):
    for where, text in card_texts(d, stories):
        if not isinstance(text, str):
            continue
        m = QUOTES.search(text)
        if m:
            r.error(where, f"quotation mark {m.group()!r} {snippet(text, m)} — use reported speech")
        m = FLAG.search(text)
        if m:
            r.error(where, "flag emoji — they render badly, use a generic emoji")
    for i, s in enumerate(stories, 1):
        if FLAG.search(s.get("icon") or ""):
            r.error(f"story {i}.icon", "flag emoji — they render badly, use a generic emoji")
        h = s.get("headline")
        if is_text(h) and len(h.split()) > HEADLINE_WORDS:
            r.warn(f"story {i}.headline", f"{len(h.split())} words — aim for ≤ {HEADLINE_WORDS}")
        b = s.get("body")
        if is_text(b):
            n = len([x for x in b.split("።") if x.strip()])
            if n != 2:
                r.warn(f"story {i}.body", f"{n} sentence(s) — the format is 2")


# ---------- 2.3 photos ----------
def check_photos(edition, stories, r):
    for i, s in enumerate(stories, 1):
        w = f"story {i}.image"
        img = s.get("image")
        if not img:
            r.warn(w, "no photo — the card falls back to a colour block + emoji")
            continue
        if not isinstance(img, dict):
            r.error(w, "must be {file, credit, source, position}")
            continue
        f = img.get("file")
        if not is_text(f):
            r.error(w, "missing 'file'")
        elif not (edition / f).is_file():
            r.error(w, f"file not found: {f}")
        elif not f.startswith("images/"):
            r.warn(w, f"'{f}' is not in this day's images/ folder")
        src = img.get("source")
        if not is_text(src):
            r.error(w, "missing 'source' (the Commons / licence page URL)")
        elif not src.startswith("https://"):
            r.error(w, f"'source' should be a https:// link, got {src!r}")
        credit = img.get("credit")
        if not is_text(credit):
            r.error(w, "missing 'credit' (author · source · licence)")
        elif LICENCE_BAD.search(credit):
            r.error(w, f"licence not allowed (NC / ND): {credit}")
        elif not LICENCE_OK.search(credit):
            r.error(w, f"no allowed licence named in credit (CC0, CC BY, CC BY-SA, Public domain, "
                       f"Unsplash, Pexels): {credit}")


# ---------- 2.4 narration ----------
def check_narration(d, stories, r):
    if not d.get("cover_speech"):
        r.warn("top.cover_speech", "missing — the voice will read brand/date/cover_title as written")
    for i, s in enumerate(stories, 1):
        sp = s.get("speech")
        if sp is None:
            r.warn(f"story {i}.speech", "missing — the voice will read the card text (digits, Latin letters)")
        elif not (isinstance(sp, list) and len(sp) == 2 and all(is_text(x) for x in sp)):
            r.error(f"story {i}.speech", "must be [headline, body] for the ear")
    lines = [(f"top.cover_speech[{k}]", t) for k, t in enumerate(d.get("cover_speech") or [], 1)]
    for i, s in enumerate(stories, 1):
        lines += [(f"story {i}.speech[{k}]", t) for k, t in enumerate(s.get("speech") or [], 1)]
    for where, text in lines:
        if not isinstance(text, str):
            continue
        bad = sorted(set(NOT_SPEAKABLE.findall(text)))
        if bad:
            m = NOT_SPEAKABLE.search(text)
            r.error(where, f"the voice can't read {''.join(bad)!r} {snippet(text, m)} — write it in Amharic words")
        if WHY_TAG.rstrip("?") in text:
            r.warn(where, f"contains '{WHY_TAG}' — that note is never narrated")


# ---------- run ----------
def validate(edition):
    """Check an edition folder. Returns a Report (r.errors / r.warnings)."""
    r = Report()
    try:
        d = json.loads((edition / "stories.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        r.error("stories.json", f"not valid JSON — line {e.lineno}, column {e.colno}: {e.msg}")
        return r
    if not isinstance(d, dict):
        r.error("stories.json", "must be an object { … }")
        return r
    stories = check_structure(d, edition, r)
    check_not_copied(d, edition, r)
    check_editorial(d, stories, r)
    check_photos(edition, stories, r)
    check_narration(d, stories, r)
    return r


def main(args):
    if args:
        ed = EDITIONS / args[0]
    else:
        eds = sorted(p for p in EDITIONS.iterdir() if (p / "stories.json").exists())
        if not eds:
            sys.exit("No editions yet.")
        ed = eds[-1]
    if not (ed / "stories.json").exists():
        sys.exit(f"No edition at {ed}")
    r = validate(ed)
    r.print(ed.name)
    sys.exit(1 if r.errors else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
