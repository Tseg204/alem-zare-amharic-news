"""Human approval gate: only the owner marks an edition as ready to publish.

Every edition starts as a draft ("status": "draft" in stories.json). After reading every card,
checking the fact-check and listening to the draft video, the owner runs:

    python3 approve.py               approve the latest edition
    python3 approve.py 2026-11-11    approve that date's edition
    python3 approve.py 2026-11-11 --revoke    back to draft

Approval asks for a typed "yes" in the terminal, so it can't happen by accident or be done by an
AI agent running commands. It also saves a fingerprint (hash) of the stories and photos: if
anything changes afterwards, the approval no longer counts and make_video.py makes a draft again.
"""
import hashlib, json, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EDITIONS = ROOT / "editions"
APPROVAL_FIELDS = ("status", "approved_at", "approved_hash")


def fingerprint(edition, d):
    """A hash of everything that ends up in the video: the stories (without the approval fields)
    and the photo files they use."""
    h = hashlib.sha256()
    content = {k: v for k, v in d.items() if k not in APPROVAL_FIELDS}
    h.update(json.dumps(content, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    for s in d.get("stories") or []:
        f = (s.get("image") or {}).get("file") if isinstance(s, dict) else None
        if f and (edition / f).is_file():
            h.update(f.encode("utf-8"))
            h.update((edition / f).read_bytes())
    return h.hexdigest()[:16]


def approval_state(edition, d=None):
    """'approved', 'changed' (approved, but edited since) or 'draft'."""
    if d is None:
        d = json.loads((edition / "stories.json").read_text(encoding="utf-8"))
    if d.get("status") != "approved":
        return "draft"
    if d.get("approved_hash") != fingerprint(edition, d):
        return "changed"
    return "approved"


def set_draft(d):
    """Remove any approval (used by --revoke and by render_cards.py --new)."""
    for k in APPROVAL_FIELDS:
        d.pop(k, None)
    return {"status": "draft", **d}


def save(edition, d):
    (edition / "stories.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")


def approve(edition):
    from validate import validate
    path = edition / "stories.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    if approval_state(edition, d) == "approved":
        print(f"{edition.name} is already approved ({d.get('approved_at')}).")
        return
    r = validate(edition)
    r.print(edition.name)
    if r.errors:
        sys.exit("Not approved: fix the errors above first.")
    if not (edition / "factcheck.json").exists():
        print("  NOTE: there is no factcheck.json — the facts were not independently checked.")
    if not (edition / "stories.draft.json").exists():
        print("  NOTE: there is no stories.draft.json — your edits can't be measured for this day.")
    print("\nStories to approve:")
    for i, s in enumerate(d.get("stories", []), 1):
        print(f"  {i}. {s.get('headline')}")
    print("\nHave you read every card, checked the fact-check, and listened to the draft video?")
    try:
        answer = input('Type "yes" to approve: ').strip().lower()
    except EOFError:
        answer = ""
    if answer != "yes":
        sys.exit("Not approved (nothing changed).")
    d = set_draft(d)
    d["status"] = "approved"
    d["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    d["approved_hash"] = fingerprint(edition, d)
    save(edition, d)
    from runlog import log
    log(edition, "approve", fingerprint=d["approved_hash"])
    print(f"Approved {edition.name}.")
    from evaluate import evaluate          # how much was changed vs the AI draft (Phase 5)
    if evaluate(edition, quiet=True):
        print("  weekly table: python3 evaluate.py --summary")
    print(f"\nNow run: python3 make_video.py {edition.name}")


def revoke(edition):
    d = json.loads((edition / "stories.json").read_text(encoding="utf-8"))
    save(edition, set_draft(d))
    from runlog import log
    log(edition, "revoke")
    print(f"{edition.name} is a draft again.")


def main(args):
    flags = [a for a in args if a.startswith("--")]
    rest = [a for a in args if not a.startswith("--")]
    if rest:
        ed = EDITIONS / rest[0]
    else:
        eds = sorted(p for p in EDITIONS.iterdir() if (p / "stories.json").exists())
        if not eds:
            sys.exit("No editions yet.")
        ed = eds[-1]
    if not (ed / "stories.json").exists():
        sys.exit(f"No edition at {ed}")
    if "--revoke" in flags:
        revoke(ed)
    else:
        approve(ed)


if __name__ == "__main__":
    main(sys.argv[1:])
