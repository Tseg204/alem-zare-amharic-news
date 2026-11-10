"""Check one day's stories.json against the project's rules before anything is rendered.

The rules come from CLAUDE.md; here they are checked by code so nothing slips through.
  ERROR   = must be fixed (render_cards.py stops)
  WARNING = worth a look, but rendering continues

Usage:
    python3 validate.py               check the latest edition
    python3 validate.py 2026-11-10    check that date's edition
It also checks the pipeline hand-off files when they exist (docs/pipeline.md):
research.json (stage 1) and factcheck.json (stage 3).
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
    else:
        # date_et is computed by etdate.py — the Ethiopian date is easy to get wrong by hand.
        from etdate import date_et
        want = date_et(folder_date)
        if is_text(d.get("date_et")) and d["date_et"].strip() != want:
            r.error("top", f"date_et '{d['date_et']}' should be '{want}' (python3 etdate.py {edition.name})")

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


# ---------- 3.1 / 3.2 hand-off files (format: docs/pipeline.md) ----------
NUMBER = re.compile(r"\d(?:[\d,.]*\d)?")
FACT_STATUS = {"verified", "corrected", "rejected", "unclear"}
FACT_FIELDS = {"headline", "body", "stats", "note"}


def site(url):
    """'https://www.bbc.com/news/x' → 'bbc.com' (to tell sources from different websites apart)."""
    m = re.match(r"https://(?:www\.)?([^/]+)", url or "")
    return m.group(1).lower() if m else None


def numbers(text):
    """All numbers in a text, commas removed: '~36,000 and 1–2' → {'36000', '1', '2'}."""
    return {n.replace(",", "").rstrip(".") for n in NUMBER.findall(text or "")}


def check_sources(where, sources, r, need=2):
    if not isinstance(sources, list):
        r.error(where, "'sources' must be a list")
        return
    for k, src in enumerate(sources, 1):
        url = src.get("url") if isinstance(src, dict) else None
        if not site(url):
            r.error(where, f"source {k} needs a https:// 'url'")
    sites = {site(s.get("url")) for s in sources if isinstance(s, dict)} - {None}
    if len(sites) < need:
        r.error(where, f"{len(sites)} different website(s) among the sources — need {need}+")


def load_json(path, r):
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        r.error(path.name, f"not valid JSON — line {e.lineno}, column {e.colno}: {e.msg}")
        return None
    if not isinstance(d, dict):
        r.error(path.name, "must be an object { … }")
        return None
    return d


def check_research(edition, r):
    path = edition / "research.json"
    if not path.exists():
        r.warn("research.json", "missing — no record of the candidate stories and their sources")
        return
    d = load_json(path, r)
    if d is None:
        return
    cands = d.get("candidates")
    if not isinstance(cands, list) or not cands:
        r.error("research.json", "'candidates' must be a non-empty list")
        return
    picked = []
    for c in cands:
        if not isinstance(c, dict):
            r.error("research.json", "each candidate must be an object { … }")
            continue
        w = f"research {c.get('id', '?')}"
        for f in ["id", "title_en", "summary_en", "category"]:
            if not is_text(c.get(f)):
                r.error(w, f"missing or empty '{f}'")
        if c.get("selected"):
            picked.append(c)
            check_sources(w, c.get("sources"), r)
            if c.get("story") not in range(1, N_STORIES + 1):
                r.error(w, f"selected, so 'story' must be the card number 1–{N_STORIES}")
    if len(picked) != N_STORIES:
        r.error("research.json", f"{len(picked)} candidates selected — expected {N_STORIES}")
    nums = [c.get("story") for c in picked]
    if len(set(nums)) != len(nums):
        r.error("research.json", f"two selected candidates share a story number: {nums}")
    horn = [c for c in cands if isinstance(c, dict) and c.get("horn_of_africa")]
    if not horn:
        r.warn("research.json", "no Horn of Africa candidate found — was there really none?")
    elif not any(c.get("selected") for c in horn):
        r.warn("research.json", "a Horn of Africa candidate exists but none was selected")


def check_factcheck(edition, stories, r):
    path = edition / "factcheck.json"
    if not path.exists():
        r.warn("factcheck.json", "missing — the numbers, names and dates on the cards are not fact-checked")
        return
    d = load_json(path, r)
    if d is None:
        return
    claims = d.get("claims")
    if not isinstance(claims, list) or not claims:
        r.error("factcheck.json", "'claims' must be a non-empty list")
        return
    checked = {i: set() for i in range(1, len(stories) + 1)}   # numbers covered, per story
    for k, c in enumerate(claims, 1):
        w = f"factcheck claim {k}"
        if not isinstance(c, dict):
            r.error(w, "must be an object { … }")
            continue
        n = c.get("story")
        if n not in checked:
            r.error(w, f"'story' must be a card number 1–{len(stories)}, got {n!r}")
            continue
        w = f"factcheck story {n} claim {k}"
        if c.get("field") not in FACT_FIELDS:
            r.error(w, f"'field' must be one of {sorted(FACT_FIELDS)}")
        for f in ["text", "claim_en"]:
            if not is_text(c.get(f)):
                r.error(w, f"missing or empty '{f}'")
        status = c.get("status")
        if status not in FACT_STATUS:
            r.error(w, f"'status' must be one of {sorted(FACT_STATUS)}")
        elif status == "verified":
            check_sources(w, c.get("sources"), r)
            checked[n] |= numbers(c.get("text")) | numbers(c.get("claim_en"))
        else:
            r.error(w, f"{status}: {c.get('claim_en')} — fix: {c.get('fix') or '(no fix given)'}")
        # Was the card edited after the check? (compare without spaces/punctuation differences)
        s = stories[n - 1]
        card = " ".join([s.get("headline") or "", s.get("body") or "", s.get("note") or ""]
                        + [x for st in s.get("stats") or [] if isinstance(st, list) for x in st])
        if is_text(c.get("text")) and c["text"].strip() not in card:
            r.warn(w, f"text {c['text']!r} is no longer on the card — re-check after editing")
    for i, s in enumerate(stories, 1):
        on_card = set()
        for f in ["headline", "body", "note"]:
            on_card |= numbers(s.get(f))
        for st in s.get("stats") or []:
            if isinstance(st, list):
                on_card |= numbers(" ".join(x for x in st if isinstance(x, str)))
        missing = sorted(on_card - checked[i], key=lambda x: (len(x), x))
        if missing:
            r.error(f"story {i}", f"number(s) not fact-checked: {', '.join(missing)}")


# ---------- 4.1 approval (approve.py) ----------
def check_approval(d, edition, r):
    from approve import approval_state
    status = d.get("status", "draft")
    if status not in ("draft", "approved"):
        r.error("top", f"'status' must be draft or approved, got {status!r}")
    elif approval_state(edition, d) == "changed":
        r.warn("top", "approved, but stories.json or a photo changed since — run approve.py again")


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
    check_approval(d, edition, r)
    check_research(edition, r)
    check_factcheck(edition, stories, r)
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
