"""Photo proposals → approved photos in the edition (stage 4b, after the owner says which ones).

The photo-scout subagent writes editions/DATE/photos.json (proposals with licence + links); nothing
is downloaded until the owner has looked at them. Then:

    python3 photos.py 2026-11-11                 list the proposals (story, option, licence, link)
    python3 photos.py 2026-11-11 --use 1=1 2=2 4=1
        downloads story 1 option 1, story 2 option 2, story 4 option 1 into images/, scales them to
        at most 2400 px on the long side, and fills each story's "image" {file, credit, source, position}
        in stories.json. Stories not named are left as they are.
    python3 photos.py 2026-11-11 --use all=1     option 1 for every story that has one

Only https links on upload.wikimedia.org, images.unsplash.com and images.pexels.com are downloaded.
"""
import io, json, sys, urllib.request
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

ROOT = Path(__file__).resolve().parent
EDITIONS = ROOT / "editions"
ALLOWED_HOSTS = {"upload.wikimedia.org", "images.unsplash.com", "images.pexels.com"}
MAX_SIDE = 2400
# Wikimedia asks automated clients for a descriptive User-Agent (no personal details here).
UA = "AlemZareCards/1.0 (Amharic news cards; photo download after manual approval)"


def load(ed):
    return json.loads((ed / "photos.json").read_text(encoding="utf-8"))


def show(ed):
    for st in load(ed)["stories"]:
        print(f"\nstory {st['story']}: {st.get('headline', '')}")
        if not st.get("proposals"):
            print("   (no proposal) " + st.get("note", ""))
        for n, p in enumerate(st.get("proposals", []), 1):
            print(f"   {n}. {p.get('why', '')}\n      {p['licence']} · {p['author']} · {p.get('size', '')}\n      {p['page']}")


def download(url, dest):
    u = urlparse(url)
    if u.scheme != "https" or u.hostname not in ALLOWED_HOSTS:
        sys.exit(f"refusing to download from {url} (allowed: {', '.join(sorted(ALLOWED_HOSTS))})")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=92)
    return im.size


def use(ed, picks):
    props = {st["story"]: st.get("proposals", []) for st in load(ed)["stories"]}
    if "all" in picks:
        n = picks.pop("all")
        picks = {s: n for s, p in props.items() if len(p) >= n} | picks
    path = ed / "stories.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    for s, n in sorted(picks.items()):           # check every pick before downloading anything
        if not 1 <= n <= len(props.get(s, [])):
            sys.exit(f"story {s} has no option {n}")
        p = props[s][n - 1]
        if not str((ed / p["file"]).resolve()).startswith(str((ed / "images").resolve()) + "/"):
            sys.exit(f"file must be inside images/: {p['file']}")
        u = urlparse(p["download"])
        if u.scheme != "https" or u.hostname not in ALLOWED_HOSTS:
            sys.exit(f"story {s}: refusing to download from {p['download']} "
                     f"(allowed: {', '.join(sorted(ALLOWED_HOSTS))})")
    for s, n in sorted(picks.items()):
        p = props[s][n - 1]
        dest = ed / p["file"]
        size = download(p["download"], dest)
        d["stories"][s - 1]["image"] = {"file": p["file"], "credit": p["credit"],
                                        "source": p["page"], "position": p.get("position", "center")}
        print(f"story {s}: {p['file']} {size[0]}×{size[1]} — {p['credit']}")
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(args):
    if not args:
        sys.exit(__doc__)
    ed = EDITIONS / args[0]
    if not (ed / "photos.json").exists():
        sys.exit(f"no photos.json in {ed} — run the photo-scout subagent first")
    if "--use" not in args:
        return show(ed)
    picks = {}
    for a in args[args.index("--use") + 1:]:
        k, _, v = a.partition("=")
        picks[k if k == "all" else int(k)] = int(v or 1)
    use(ed, picks)


if __name__ == "__main__":
    main(sys.argv[1:])
