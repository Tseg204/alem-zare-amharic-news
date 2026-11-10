"""Reading and posting extras for one edition (Phase 8) — built only from files that already exist,
so nothing new and unchecked is written:

  digest.md     for reading yourself: each card's Amharic text + the English summary, key facts,
                the fact-checked claims and the source links; plus the stories that were left out.
  captions.txt  ready-to-paste captions for Instagram, TikTok and YouTube Shorts: headlines, sources,
                photo/music credits, AI-disclosure line, hashtags; character counts checked per platform.

Both are rewritten by render_cards.py (after every render) and make_video.py (adds the music credit).
Run alone:  python3 share.py [YYYY-MM-DD]
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EDITIONS = ROOT / "editions"

AI_DISCLOSURE = "ይህ ይዘት በAI ታግዞ ተዘጋጅቶ በሰው ተገምግሟል"     # same line as on the follow card
NUMBERS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
BASE_TAGS = ["#ዓለምዛሬ", "#AmharicNews", "#Ethiopia"]
TOPIC_TAGS = {          # research.json "category" → hashtag (first matches fill up to MAX_TAGS)
    "africa": "#Africa", "health": "#Health", "climate": "#Climate", "economy": "#Economy",
    "tech": "#Tech", "science": "#Science", "sport": "#Sport", "world": "#WorldNews",
}
MAX_TAGS = 5            # Instagram and TikTok both advise 3–5 relevant hashtags
LIMITS = {"Instagram": 2200, "TikTok": 4000, "YouTube description": 5000, "YouTube title": 100}


def _json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _selected(research):
    """story number → research candidate."""
    return {c["story"]: c for c in (research or {}).get("candidates", []) if c.get("selected")}


def _status(edition, d):
    from approve import approval_state
    return approval_state(edition, d)        # 'approved' | 'changed' | 'draft'


# ---------- digest.md ----------
def write_digest(edition):
    d = _json(edition / "stories.json")
    research = _json(edition / "research.json")
    claims = (_json(edition / "factcheck.json") or {}).get("claims", [])
    sel = _selected(research)
    out = [f"# {d['brand']} — {d['date_et']} ({d['date_gc']})", ""]
    if _status(edition, d) != "approved":
        out += ["> **Draft** — not approved by the owner (or changed after approval).", ""]
    for i, s in enumerate(d["stories"], 1):
        c = sel.get(i, {})
        out += [f"## {i}. {s['headline']}", f"*{s['category']}* · card {i + 1}", "", s["body"], ""]
        out += [f"> {s['note']}", ""] if s.get("note") else []
        if s.get("stats"):
            out += ["**Numbers:** " + " · ".join(f"{n} {label}" for n, label in s["stats"]), ""]
        if c.get("title_en"):
            out += [f"**In English — {c['title_en']}.** {c.get('summary_en', '')}", ""]
        if c.get("key_facts_en"):
            out += ["**Key facts**"] + [f"- {f}" for f in c["key_facts_en"]] + [""]
        mine = [x for x in claims if x.get("story") == i]
        if mine:
            ok = sum(x.get("status") == "verified" for x in mine)
            out.append(f"**Fact-check** — {ok} of {len(mine)} claims verified")
            for x in mine:
                links = ", ".join(f"[{src.get('outlet', '?')}]({src['url']})" for src in x.get("sources", []) if src.get("url"))
                out.append(f"- {'✔' if x.get('status') == 'verified' else '⚠ ' + x.get('status', '?')} "
                           f"{x.get('claim_en', x.get('text', ''))} — {links}")
            out.append("")
        if c.get("sources"):
            out += ["**Read more**"] + [f"- [{src.get('outlet', src['url'])}]({src['url']})"
                                        + (f" · {src['published']}" if src.get("published") else "")
                                        for src in c["sources"]] + [""]
        elif s.get("sources"):
            out += [f"**Sources:** {s['sources']}", ""]
    others = [c for c in (research or {}).get("candidates", []) if not c.get("selected")]
    if others:
        out += ["## Also in the news (not on the cards)", ""]
        for c in others:
            links = " · ".join(f"[{src.get('outlet', '?')}]({src['url']})" for src in c.get("sources", []))
            out.append(f"- **{c.get('title_en', c.get('id'))}** — {c.get('summary_en', '')} {links}"
                       + (f"  \n  *Left out:* {c['reason']}" if c.get("reason") else ""))
        out.append("")
    if research is None:
        out += ["*(No research.json for this day — English summaries and links start with editions made by /todays-cards.)*", ""]
    (edition / "digest.md").write_text("\n".join(out), encoding="utf-8")


# ---------- captions.txt ----------
def _outlets(d):
    seen = []
    for s in d["stories"]:
        for o in s.get("sources", "").split("·"):
            o = o.strip()
            if o and o not in seen:
                seen.append(o)
    return seen


def _hashtags(d, research):
    tags = list(BASE_TAGS)
    for c in sorted(_selected(research).values(), key=lambda c: c["story"]):
        t = TOPIC_TAGS.get(str(c.get("category", "")).lower())
        if t and t not in tags and len(tags) < MAX_TAGS:
            tags.append(t)
    if len(tags) < MAX_TAGS:
        tags.append("#ዜና")
    return tags[:MAX_TAGS]


def _music(d, edition):
    try:
        from make_video import pick_track
        return pick_track(d, edition)[1]
    except Exception:
        return None


def write_captions(edition):
    d = _json(edition / "stories.json")
    research = _json(edition / "research.json")
    tags = " ".join(_hashtags(d, research))
    heads = [f"{NUMBERS[i]} {s['headline']}" for i, s in enumerate(d["stories"])]
    photos = [s["image"] for s in d["stories"] if s.get("image")]
    music = _music(d, edition)
    cta = " | ".join(d.get("cta_lines", []))
    intro = [f"🌍 {d['brand']} | {d['date_et']}", f"{d.get('cover_title', '')}፦", ""] + heads
    sources = "📰 ምንጮች፦ " + " · ".join(_outlets(d))
    short_credits = ["📷 " + "; ".join(p["credit"].removeprefix("Photo: ") for p in photos)] if photos else []
    long_credits = ([f"📷 ፎቶዎች (photos, colour-adjusted and cropped):"]
                    + [f"• {p['credit'].removeprefix('Photo: ')} — {p['source']}" for p in photos]) if photos else []
    music_line = []
    if music:
        music_line = [f"🎵 {music.get('attribution') or music.get('title', '') + ' — ' + music.get('artist', '') + ' (Pixabay)'}"]
    ai = [f"🤖 {AI_DISCLOSURE} (AI narration)"]

    posts = {
        "Instagram": intro + ["", "👉 ያንሸራትቱ / ቪዲዮውን ይመልከቱ", "", sources] + short_credits + music_line + ai
                     + ["", f"🔔 {cta}", "", tags],
        "TikTok": intro + ["", sources] + short_credits + music_line + ai + ["", tags],
        "YouTube description": intro + ["", sources, ""] + long_credits + music_line + ai
                               + ["", f"🔔 {cta}", "", tags + " #Shorts"],
    }
    lead = d["stories"][(d.get("lead") or 1) - 1]["headline"]
    title = f"{d['brand']} | {d['date_et']} — {lead}"
    if len(title) > LIMITS["YouTube title"]:
        title = title[:LIMITS["YouTube title"] - 1] + "…"

    approved = _status(edition, d) == "approved"
    out = [f"CAPTIONS — {d['brand']} {d['date_gc']}",
           "Before posting: switch ON the platform's AI-generated / synthetic-content label (AI voice)."]
    if not approved:
        out.append("!! DRAFT — this edition is not approved (or changed after approval). Do not post yet.")
    out.append("")
    blocks = [("YouTube title", title)] + [(k, "\n".join(v).strip()) for k, v in posts.items()]
    for name, text in blocks:
        n, lim = len(text), LIMITS[name]
        out += [f"===== {name.upper()}  ({n}/{lim} characters{' — TOO LONG' if n > lim else ''}) =====",
                text, ""]
        if n > lim:
            print(f"  WARNING: {name} caption is {n} characters (limit {lim})")
    (edition / "captions.txt").write_text("\n".join(out), encoding="utf-8")


def write_all(edition):
    write_digest(edition)
    write_captions(edition)


def main(args):
    if args:
        ed = EDITIONS / args[0]
    else:
        ed = sorted(p for p in EDITIONS.iterdir() if (p / "stories.json").exists())[-1]
    if not (ed / "stories.json").exists():
        sys.exit(f"No edition at {ed}")
    write_all(ed)
    print(f"digest → {(ed / 'digest.md').relative_to(ROOT)}   captions → {(ed / 'captions.txt').relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
