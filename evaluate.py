"""Measure how good the AI's drafts are: how much does the owner change before approving?

1. When Claude hands an edition over for review, it saves its first draft:
       python3 evaluate.py --snapshot 2026-11-11      → editions/2026-11-11/stories.draft.json
   (never overwritten: the draft is the AI's work before any human edit)
2. After the owner approves (approve.py does this automatically), compare draft vs approved:
       python3 evaluate.py 2026-11-11                 → prints a report + writes eval.json
3. Summary of all evaluated days, grouped by week:
       python3 evaluate.py --summary                  → prints + writes reports/quality.md

"Words changed" = share of the draft's words that were removed or replaced (word-level diff),
so 0% = untouched and 100% = completely rewritten.
"""
import difflib, json, re, shutil, sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EDITIONS = ROOT / "editions"
REPORTS = ROOT / "reports"
DRAFT, EVAL = "stories.draft.json", "eval.json"
TEXT_FIELDS = ["headline", "body", "note"]
NUMBER = re.compile(r"\d(?:[\d,.]*\d)?")
PUNCT = re.compile(r"[\s።፣፤፥፦፧፨,.;:!?()\[\]\-–—]+")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def words_changed(a, b):
    """Share (0–1) of the words in draft text a that are not kept in final text b."""
    wa, wb = (a or "").split(), (b or "").split()
    if not wa:
        return 0.0 if not wb else 1.0
    kept = sum(m.size for m in difflib.SequenceMatcher(None, wa, wb, autojunk=False).get_matching_blocks())
    return 1 - kept / len(wa)


def kind_of_fix(a, b):
    """A rough label for what kind of change was made to one text field."""
    if (a or "") == (b or ""):
        return None
    if PUNCT.sub("", a or "") == PUNCT.sub("", b or ""):
        return "punctuation"
    w = words_changed(a, b)
    if w > 0.6:
        return "rewrite"
    nums = lambda t: sorted(n.replace(",", "") for n in NUMBER.findall(t or ""))
    if nums(a) != nums(b):
        return "numbers"
    if w <= 0.2:
        return "small wording"
    return "rewording"


def flat_stats(s):
    return " | ".join(" ".join(x) for x in s.get("stats") or [] if isinstance(x, list))


def compare(draft, final):
    """Draft vs final stories.json → dict with per-story and overall numbers."""
    stories = []
    for i, (a, b) in enumerate(zip(draft.get("stories", []), final.get("stories", [])), 1):
        st = {"story": i, "headline_draft": a.get("headline"), "fields": {}}
        for f in TEXT_FIELDS:
            st["fields"][f] = {"changed": a.get(f) != b.get(f),
                               "words_changed": round(words_changed(a.get(f), b.get(f)), 3),
                               "kind": kind_of_fix(a.get(f), b.get(f))}
        st["fields"]["stats"] = {"changed": flat_stats(a) != flat_stats(b),
                                 "kind": kind_of_fix(flat_stats(a), flat_stats(b))}
        sa, sb = " ".join(a.get("speech") or []), " ".join(b.get("speech") or [])
        st["fields"]["speech"] = {"changed": sa != sb,
                                  "words_changed": round(words_changed(sa, sb), 3),
                                  "kind": kind_of_fix(sa, sb)}
        st["photo_changed"] = (a.get("image") or {}).get("file") != (b.get("image") or {}).get("file")
        # a different story altogether: headline and body both almost fully rewritten
        st["replaced"] = (st["fields"]["headline"]["words_changed"] > 0.8
                          and st["fields"]["body"]["words_changed"] > 0.8)
        stories.append(st)
    n = len(stories) or 1
    share = lambda f: sum(s["fields"][f]["changed"] for s in stories) / n
    kinds = defaultdict(int)
    for s in stories:
        if s["replaced"]:
            kinds["story replaced"] += 1      # one fix, not one per field
            continue
        for f, v in s["fields"].items():
            if v["kind"]:
                kinds[v["kind"]] += 1
    return {
        "stories": stories,
        "summary": {
            "headlines_changed": round(share("headline"), 3),
            "bodies_changed": round(share("body"), 3),
            "notes_changed": round(share("note"), 3),
            "stats_changed": round(share("stats"), 3),
            "speech_changed": round(share("speech"), 3),
            "avg_body_words_changed": round(sum(s["fields"]["body"]["words_changed"] for s in stories) / n, 3),
            "untouched_stories": sum(not any(v["changed"] for v in s["fields"].values())
                                     and not s["photo_changed"] for s in stories),
            "stories_replaced": sum(s["replaced"] for s in stories),
            "photos_changed": sum(s["photo_changed"] for s in stories),
            "kinds_of_fixes": dict(kinds),
        },
    }


def pct(x):
    return f"{round(100 * x)}%"


# ---------- commands ----------
def snapshot(edition, force=False):
    target = edition / DRAFT
    if target.exists() and not force:
        print(f"{target.relative_to(ROOT)} already exists — the first draft is kept as it was.")
        return
    shutil.copy(edition / "stories.json", target)
    print(f"Saved the AI draft → {target.relative_to(ROOT)} (compare after approval: python3 evaluate.py {edition.name})")


def evaluate(edition, quiet=False):
    if not (edition / DRAFT).exists():
        print(f"  NOTE: no {DRAFT} in {edition.name} — the AI draft was not saved, nothing to compare.")
        return None
    final = load(edition / "stories.json")
    if final.get("status") != "approved" and not quiet:
        print("  NOTE: this edition is not approved yet — comparing with the current (unfinished) version.")
    res = compare(load(edition / DRAFT), final)
    res.update({"edition": edition.name, "approved": final.get("status") == "approved",
                "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M")})
    (edition / EVAL).write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sm = res["summary"]
    print(f"\nQuality of the AI draft — {edition.name}")
    print(f"  untouched stories: {sm['untouched_stories']} of {len(res['stories'])}"
          f"   replaced: {sm['stories_replaced']}   photos changed: {sm['photos_changed']}")
    print(f"  changed: headlines {pct(sm['headlines_changed'])} · bodies {pct(sm['bodies_changed'])} · "
          f"notes {pct(sm['notes_changed'])} · stats {pct(sm['stats_changed'])} · narration {pct(sm['speech_changed'])}")
    print(f"  body words changed on average: {pct(sm['avg_body_words_changed'])}")
    if sm["kinds_of_fixes"]:
        print("  kinds of fixes: " + ", ".join(f"{k} {v}" for k, v in sorted(sm["kinds_of_fixes"].items())))
    for s in res["stories"]:
        changed = [f"{f} ({v['kind']})" for f, v in s["fields"].items() if v["changed"]]
        if s["photo_changed"]:
            changed.append("photo")
        print(f"   {s['story']}. {'REPLACED — ' if s['replaced'] else ''}{', '.join(changed) or 'no changes'}")
    print(f"  saved → {(edition / EVAL).relative_to(ROOT)}")
    return res


def summary():
    rows = []
    for ed in sorted(EDITIONS.iterdir()):
        if (ed / EVAL).exists():
            r = load(ed / EVAL)
            if not r.get("approved"):
                continue                      # only finished (approved) days count
            r["date"] = date.fromisoformat(ed.name)
            rows.append(r)
    if not rows:
        print("No approved editions with a saved draft yet (eval.json is written by approve.py).")
        return
    weeks = defaultdict(list)
    for r in rows:
        y, w, _ = r["date"].isocalendar()
        weeks[f"{y}-W{w:02d}"].append(r)

    def line(label, rs):
        n = sum(len(r["stories"]) for r in rs)
        avg = lambda k: sum(r["summary"][k] * len(r["stories"]) for r in rs) / n
        tot = lambda k: sum(r["summary"][k] for r in rs)
        return (f"| {label} | {len(rs)} | {n} | {tot('untouched_stories')} | {pct(avg('headlines_changed'))} | "
                f"{pct(avg('bodies_changed'))} | {pct(avg('avg_body_words_changed'))} | "
                f"{pct(avg('speech_changed'))} | {tot('stories_replaced')} | {tot('photos_changed')} |")

    head = ("| Week | Days | Stories | Untouched | Headlines changed | Bodies changed | Body words changed "
            "| Narration changed | Replaced | Photos changed |\n|---|---|---|---|---|---|---|---|---|---|")
    kinds = defaultdict(int)
    for r in rows:
        for k, v in r["summary"]["kinds_of_fixes"].items():
            kinds[k] += v
    out = ["# Draft quality — how much the owner changes the AI's drafts", "",
           "Generated by `python3 evaluate.py --summary`. Each day the AI's first draft (`stories.draft.json`)",
           "is compared with the version the owner approved. Lower = better drafts.", "",
           head, *[line(w, rs) for w, rs in sorted(weeks.items())], line("**All**", rows), "",
           "Kinds of fixes (all days): " + (", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) or "none"), "",
           "## Per day", "",
           head.replace("| Week |", "| Day |"), *[line(r["date"].isoformat(), [r]) for r in rows], ""]
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "quality.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    print(f"saved → reports/quality.md")


def pick_edition(rest):
    if rest:
        return EDITIONS / rest[0]
    eds = sorted(p for p in EDITIONS.iterdir() if (p / "stories.json").exists())
    if not eds:
        sys.exit("No editions yet.")
    return eds[-1]


def main(args):
    flags = {a for a in args if a.startswith("--")}
    rest = [a for a in args if not a.startswith("--")]
    if "--summary" in flags:
        return summary()
    ed = pick_edition(rest)
    if not (ed / "stories.json").exists():
        sys.exit(f"No edition at {ed}")
    if "--snapshot" in flags:
        snapshot(ed, force="--force" in flags)
    else:
        evaluate(ed)


if __name__ == "__main__":
    main(sys.argv[1:])
