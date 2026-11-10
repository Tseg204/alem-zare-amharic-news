"""Run log (observability): what happened while an edition was made, and what it cost.

Two sources go into editions/YYYY-MM-DD/run_log.json:

1. "events" — written automatically by the scripts each time they run:
   validate (errors/warnings), render (time, overflow), video (time, draft/final, Azure voice characters),
   draft saved, approve.
2. "claude" — collected from Claude Code's own session records (~/.claude/projects/…/*.jsonl):
   tokens, web searches (queries) and pages fetched, subagents, and Claude Code's own cost estimate.
   A session counts for an edition when it started that edition (render_cards.py --new DATE) or
   wrote its stories.json / research.json / factcheck.json.

Usage:
    python3 runlog.py               report for the latest edition (collects Claude usage first)
    python3 runlog.py 2026-11-11    report for that date
"""
import json, re, sys, time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EDITIONS = ROOT / "editions"
LOG = "run_log.json"
# Claude Code keeps one folder of session records per project folder: '/' and '.' become '-'.
CLAUDE_DIR = Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))
HANDOFF_FILES = ("stories.json", "research.json", "factcheck.json")


def _read(edition):
    p = edition / LOG
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"edition": edition.name, "events": []}


def _write(edition, data):
    (edition / LOG).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def log(edition, stage, **info):
    """Add one event. Never lets a logging problem stop the real work."""
    try:
        data = _read(edition)
        data["events"].append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "stage": stage, **info})
        _write(edition, data)
    except OSError as e:
        print(f"  NOTE: could not write {LOG}: {e}")


@contextmanager
def timed(edition, stage, **info):
    """with timed(ed, "render") as info: …  → logs the stage with its duration in seconds."""
    t0 = time.time()
    yield info
    log(edition, stage, seconds=round(time.time() - t0, 1), **info)


# ---------- Claude Code usage ----------
def _entries(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _tool_uses(e):
    m = e.get("message")
    if e.get("type") == "assistant" and isinstance(m, dict) and isinstance(m.get("content"), list):
        for c in m["content"]:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                yield c["name"], c.get("input") or {}


def _belongs(name, inp, date):
    """Does this tool call work on this edition?"""
    if name == "Bash":
        return re.search(rf"render_cards\.py\s+--new\s+{date}\b", inp.get("command", "")) is not None
    if name in ("Write", "Edit"):
        return any(str(inp.get("file_path", "")).endswith(f"editions/{date}/{f}") for f in HANDOFF_FILES)
    return False


def _usage(paths):
    """Token totals and tool activity in some transcript files (each API message counted once)."""
    seen, tok = set(), Counter()
    searches, fetches, agents, first, last = [], [], [], None, None
    for p in paths:
        for e in _entries(p):
            ts = e.get("timestamp")
            if ts:
                first, last = min(first or ts, ts), max(last or ts, ts)
            m = e.get("message")
            if e.get("type") == "assistant" and isinstance(m, dict) and m.get("usage") and m.get("id") not in seen:
                seen.add(m.get("id"))
                u = m["usage"]
                tok["input"] += u.get("input_tokens", 0)
                tok["output"] += u.get("output_tokens", 0)
                tok["cache_read"] += u.get("cache_read_input_tokens", 0)
                tok["cache_write"] += u.get("cache_creation_input_tokens", 0)
            for name, inp in _tool_uses(e):
                if name == "WebSearch":
                    searches.append(inp.get("query"))
                elif name == "WebFetch":
                    fetches.append(inp.get("url"))
                elif name in ("Agent", "Task"):
                    agents.append(inp.get("subagent_type") or "general-purpose")
    return dict(tok), searches, fetches, agents, first, last


def collect_claude(edition):
    """Find the Claude Code sessions that worked on this edition and sum up their usage."""
    if not CLAUDE_DIR.exists():
        return None
    sessions = []
    for main in sorted(CLAUDE_DIR.glob("*.jsonl")):
        if not any(_belongs(n, i, edition.name) for e in _entries(main) for n, i in _tool_uses(e)):
            continue
        sub = sorted((CLAUDE_DIR / main.stem / "subagents").glob("*.jsonl"))
        tok, searches, fetches, agents, first, last = _usage([main])
        stok, ssearch, sfetch, _, _, _ = _usage(sub)
        cost, by_model = None, None
        for e in _entries(main):
            if e.get("type") == "cost-state":           # Claude Code's own totals (all models, at API prices)
                cost = e.get("totalCostUSD")
                by_model = {m: {"input": u.get("inputTokens", 0), "output": u.get("outputTokens", 0),
                                "cache_read": u.get("cacheReadInputTokens", 0),
                                "cache_write": u.get("cacheCreationInputTokens", 0)}
                            for m, u in (e.get("modelUsage") or {}).items()}
        sessions.append({
            "session": main.stem, "from": first, "to": last,
            "tokens": tok, "subagent_tokens": stok, "tokens_by_model": by_model,
            "web_searches": searches + ssearch, "pages_fetched": len(fetches) + len(sfetch),
            "subagents": agents, "cost_estimate_usd": round(cost, 2) if cost is not None else None,
        })
    return sessions


# ---------- report ----------
def report(edition):
    data = _read(edition)
    sessions = collect_claude(edition)
    if sessions is not None:
        data["claude"] = {"collected_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "sessions": sessions}
        _write(edition, data)

    print(f"Run log — {edition.name}")
    ev = data.get("events", [])
    if not ev:
        print("  no script events yet (they are logged from now on by render / video / approve)")
    for e in ev:
        extra = {k: v for k, v in e.items() if k not in ("time", "stage")}
        print(f"  {e['time']}  {e['stage']:<12} " + ", ".join(f"{k}={v}" for k, v in extra.items()
                                                          if not isinstance(v, (list, dict)) or v))
    videos = [e for e in ev if e["stage"] == "video"]
    if videos:
        print(f"  Azure voice: {sum(e.get('tts_chars_sent', 0) for e in videos)} characters sent "
              f"({sum(e.get('tts_new_clips', 0) for e in videos)} new clips, the rest re-used)")

    sessions = data.get("claude", {}).get("sessions") or []
    if not sessions:
        print("  Claude Code: no session found that worked on this edition")
    for s in sessions:
        t, st = s["tokens"], s["subagent_tokens"]
        print(f"  Claude session {s['session'][:8]}  {(s['from'] or '')[:16]} → {(s['to'] or '')[11:16]} UTC")
        if not s.get("tokens_by_model"):
            print(f"    tokens: output {t.get('output', 0):,} · input {t.get('input', 0):,} · "
                      f"cache read {t.get('cache_read', 0):,} · cache write {t.get('cache_write', 0):,}"
                  + (f"  (+ subagents: output {st.get('output', 0):,})" if st else ""))
        for m, u in (s.get("tokens_by_model") or {}).items():
            print(f"    {m}: output {u['output']:,} · input {u['input']:,} · cache read {u['cache_read']:,}")
        print(f"    web searches: {len(s['web_searches'])} · pages fetched: {s['pages_fetched']} · "
              f"subagents: {', '.join(s['subagents']) or 'none'}")
        if s["cost_estimate_usd"] is not None:
            print(f"    Claude Code's cost estimate (whole session, at API prices): ${s['cost_estimate_usd']}")
    print(f"  saved → {(edition / LOG).relative_to(ROOT)}")


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
    report(ed)


if __name__ == "__main__":
    main(sys.argv[1:])
