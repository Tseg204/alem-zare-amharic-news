# Project progress — agentic workflow upgrade

This file tracks the plan to turn ዓለም ዛሬ into a well-structured agentic AI project:
for daily use, for social media, and as a portfolio piece for job applications.

**To continue in any new session, just say:**
> Read PROGRESS.md and let's continue.

Claude reads this file, finds the first unchecked step, and picks up from there.
After each step, Claude ticks the box `[x]` and adds a line to the *Session log* at the bottom.

Legend: `[ ]` to do · `[x]` done · `[~]` started / partly done · 👤 = a step only you can do
(needs your password, account, or decision).

---

## Phase 1 — Git & GitHub (version control) ✅ done

*Why:* Git saves a history of every change ("snapshots" called commits), so nothing is ever lost and
you can show how the project grew. GitHub is the website that hosts that history online and is
what recruiters look at.

- [x] 1.1 Create `.gitignore` — the list of files Git must **never** save
      (`.env` with your Azure key, generated cards/videos, music files we may not redistribute, `.DS_Store`).
- [x] 1.2 Create `.env.example` — a copy of `.env` with fake values, so others know what settings exist.
- [x] 1.3 👤 Accept Apple's Xcode licence so the `git` command works on your Mac.
      In the Terminal app run: `sudo xcodebuild -license accept` (it asks for your Mac password).
- [x] 1.4 👤 Tell Git who you are (name + email shown on every commit). Run once:
      `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`
      (for privacy you can later use GitHub's "noreply" email instead — see 1.8).
- [x] 1.5 Turn the folder into a Git repository (`git init`) and check that `.env` is ignored.
- [x] 1.6 First commit (the first saved snapshot).
- [x] 1.7 👤 GitHub account (owner already has one).
- [x] 1.8 👤 Install GitHub CLI (`gh`, the GitHub command-line tool) from https://cli.github.com (macOS installer),
      then log in from Terminal: `gh auth login` → GitHub.com → HTTPS → Yes (authenticate Git) →
      Login with a web browser. (Installed via Homebrew: `/opt/homebrew/bin/gh`.)
      Optional privacy: github.com/settings/emails → tick "Keep my email addresses private".
- [x] 1.9 Switch commits to GitHub's private "noreply" email (the 7 local commits currently carry the
      personal email; rewrite them *before* the first upload), then create the repository on GitHub with
      `gh repo create` (owner picks name + Public/Private) and upload ("push").
- [x] 1.10 Learn the daily routine: `git status` → `git add` → `git commit` → `git push`
       (Claude will do it with you a few times; cheat-sheet goes here when done).

## Phase 2 — Rules checked by code (`validate.py`) ✅ done

- [x] 2.1 Check `stories.json` structure (5 stories, required fields, 0–2 stats).
- [x] 2.2 Editorial rules: no «…» / quotation marks, headline ≤ ~8 words, no flag emoji.
- [x] 2.3 Photo rules: credit + source URL present, licence in the allowed list (no NC).
- [x] 2.4 Narration rules: no Latin letters or digits left in `speech`.
- [x] 2.5 Run it automatically at the start of `render_cards.py`.

## Phase 3 — Clear pipeline stages with saved hand-offs ✅ done

- [x] 3.1 `research.json` — candidate stories + source links (research step output).
- [x] 3.2 `factcheck.json` — each claim (number/name/date) → 2+ sources → verified / rejected.
- [x] 3.3 Separate fact-checker (a Claude Code subagent that only sees the draft + sources).
- [x] 3.4 Write the stages + hand-off files into CLAUDE.md.

## Phase 4 — Human approval gate ✅ done

- [x] 4.1 `"status": "draft" | "approved"` in `stories.json`.
- [x] 4.2 `make_video.py` / exports refuse to run on a draft.

## Phase 5 — Measuring quality (evaluation) ✅ done

- [x] 5.1 Save the AI's first draft (`stories.draft.json`) before the owner edits.
- [x] 5.2 Script comparing draft vs approved → % of headlines/bodies changed, kinds of fixes.
- [x] 5.3 Weekly summary table (great for the portfolio).

## Phase 6 — Run log (observability) ✅ done

- [x] 6.1 `run_log.json` per edition: searches, sources, validation failures, time, cost (tokens + Azure TTS).

## Phase 7 — Packaging & automation ✅ done

- [x] 7.1 Claude Code skill `/todays-cards` for the daily workflow.
- [x] 7.2 Subagents: researcher, fact-checker, Amharic writer, photo scout.
- [x] 7.3 Morning scheduled run that prepares a *draft* and notifies the owner (never auto-posts).

## Phase 8 — Personal use & sharing extras ✅ done

- [x] 8.1 `digest.md` per day — longer summaries + links, for reading yourself.
- [x] 8.2 `captions.txt` per day — ready-to-paste caption, hashtags, credits per platform.

## Phase 9 — Portfolio ← *next: 9.2 once the first full-pipeline edition is approved*

- [x] 9.1 README: architecture diagram, design decisions (why human review, why separate checker…).
- [~] 9.2 Quality numbers from Phase 5 + a sample video / screenshots.
      Done: screenshots, Results section with the metrics table (values *pending*).
      To do: after the first edition made with `/todays-cards` is approved, fill the table from
      `reports/quality.md`, `eval.json`, `factcheck.json`, `run_log.json`.
      👤 Upload an approved `short.mp4` to YouTube (Shorts) and send Claude the link for the README.

---

## Git cheat-sheet (everyday routine)

Run these in Terminal from the project folder (`cd ~/Documents/Claude/amharic-news`).

| Step | Command | What it does |
|---|---|---|
| 1. Look | `git status` | Lists what changed since the last snapshot (red = not yet picked). |
| 2. See details | `git diff` | Shows the exact lines changed (press `q` to exit). |
| 3. Pick | `git add PROGRESS.md` (or `git add .` for everything) | Puts changes into the next snapshot ("staging"; shown green). |
| 4. Save | `git commit -m "Short description of what and why"` | Saves the snapshot on your Mac. |
| 5. Upload | `git push` | Sends your new snapshots to GitHub. |
| History | `git log --oneline` | Lists snapshots, newest first (press `q` to exit). |
| Undo a pick | `git restore --staged FILE` | Takes a file back out of the next snapshot (keeps your edits). |

After reviewing a day: `python3 approve.py YYYY-MM-DD` (type yes), then `python3 make_video.py YYYY-MM-DD`.
Captions to paste: `editions/DATE/captions.txt` · reading version: `digest.md` (`python3 share.py DATE` remakes both).
Weekly quality table: `python3 evaluate.py --summary` → `reports/quality.md`.
What a day took and cost: `python3 runlog.py YYYY-MM-DD` → `run_log.json`.
Before rendering, `python3 validate.py` checks the day's `stories.json` (also runs automatically).

Good commit messages: start with a verb, say *what* changed — "Add validate.py for editorial rules",
"Fix overflow on story cards". One topic per commit.
Never `git add` the `.env` file (`.gitignore` already blocks it).

## Decisions made

- 10 Nov 2026 — Never auto-post; the owner reviews and posts manually (safety + credibility).
- 10 Nov 2026 — Not saved in Git: `.env`, generated `cards/ layers/ audio/ video/`, `music/*.mp3`
  (Pixabay licence lets us use tracks in videos but not re-share the files; `tracks.json` lists them).
  Photos in `editions/*/images/` *are* saved (free licences, credited in `credits.md`).

## Session log

- 10 Nov 2026 — Plan agreed. Created PROGRESS.md, `.gitignore`, `.env.example`.
  Found that `git` is blocked until the Xcode licence is accepted (step 1.3).
- 10 Nov 2026 — Owner accepted Xcode licence + set Git name/email. `git init` done (branch `main`);
  `.env` confirmed ignored, key not found in any file to be saved. 53 files (~21 MB) ready for the first commit (1.6).

- 10 Nov 2026 — Added portfolio pieces: README front page (pipeline diagram, design decisions,
  tech stack), `showcase/` sample cards, MIT `LICENSE`; `.vscode/` now ignored.
  Made the first 6 commits, grouped by topic. Next: step 1.7 (GitHub account).
  To-do for 9.2: upload a sample video to YouTube and link it in the README (videos are too big for Git).
- 10 Nov 2026 — Step 1.7 done (has GitHub account). No `gh`, Homebrew or SSH key on the Mac; plan: install gh
  via the official installer, `gh auth login`, switch to noreply email, then create repo + push.
- 10 Nov 2026 — gh installed (Homebrew) and logged in as Tseg204. Git email switched to the GitHub noreply
  address and all 8 commits rewritten with it (verified no personal email or Azure key in history).
  Public repo created and pushed: https://github.com/Tseg204/alem-zare-amharic-news (description + topics set).
  Next: step 1.10 — practise the daily save routine (status → add → commit → push).
- 10 Nov 2026 — Owner ran status/add/commit/push themselves (cheat-sheet commit). Phase 1 complete.
  Next session: Phase 2, step 2.1.
- 10 Nov 2026 — Phase 2 done: `validate.py` checks structure (+ date_gc = folder date, stories not still
  copied from yesterday), editorial rules (no quotation marks, no flag emoji, headline ≤ 8 words and 2-sentence
  body as warnings), photos (file exists, https source, licence CC0/CC BY/CC BY-SA/PD/Unsplash/Pexels, no NC/ND —
  ND added because we crop + tone-adjust), narration (no Latin letters/digits/symbols in `speech`).
  `render_cards.py` runs it first and stops on errors. Tested: 10 Nov passes; 9 Nov passes with 6 warnings
  (made before `speech` existed); a broken test copy triggered all 12 planted errors. Next: Phase 3, step 3.1.
- 10 Nov 2026 — Phase 3 done: stages + hand-off formats in `docs/pipeline.md` (research.json → stories.json →
  factcheck.json → validate → render → human review). `validate.py` now checks both files: 5 selected stories
  with 2+ sources from different websites; claims verified by 2+ websites; open claims (corrected / rejected /
  unclear) are errors; every number on a card must be covered by a verified claim; warns if the card text changed
  after the check. Missing files = warnings (old editions have none). Fact-checker subagent:
  `.claude/agents/fact-checker.md` (sees only stories.json + research.json, can search the web, writes
  factcheck.json, never edits cards). Daily workflow in CLAUDE.md updated. Tested on a broken copy: all 7 planted
  problems reported. Not yet tried on a real day — first real run with the next edition. Next: Phase 4, step 4.1.
- 10 Nov 2026 — Phase 4 done: `approve.py` = the owner's approval (validates first, lists the headlines, needs a
  typed "yes", saves `status: approved` + `approved_at` + a fingerprint of stories.json and the photos). Any later edit
  → draft again (validate.py warns). `make_video.py` makes `short.mp4` only when approved; otherwise
  `short_DRAFT.mp4` with a red "DRAFT · NOT APPROVED" banner (needed to review the narration before approving) and
  removes a stale short.mp4. `--new` always starts a draft. Claude is told never to run approve.py.
  Tested on a copy of 10 Nov: no → stays draft, yes → approved → short.mp4; edit → changed → draft video with banner.
  Existing 9 + 10 Nov editions count as drafts until approved. Next: Phase 5, step 5.1.
- 10 Nov 2026 — Phase 5 done: `evaluate.py`. `--snapshot` saves `stories.draft.json` at hand-over (never overwritten);
  on approval, approve.py compares draft vs approved → `eval.json`: per story which fields changed (headline, body,
  note, stats, narration, photo), share of words changed, kind of fix (punctuation / numbers / small wording /
  rewording / rewrite / story replaced). `--summary` → `reports/quality.md`, weekly + per-day table of approved days.
  Tested on copies with 4 planted edits (all labelled right; unapproved day left out). No real data yet: 9 + 10 Nov
  have no saved draft; measuring starts with the next edition. Next: Phase 6, step 6.1.
- 10 Nov 2026 — Phase 6 done: `runlog.py` + `run_log.json` per edition. Scripts log events automatically (validate
  errors/warnings, render time + overflowing cards, video time / draft or final / length / voice / music / Azure
  characters sent + new vs re-used clips, draft saved, approve/revoke). `python3 runlog.py DATE` adds the Claude Code
  sessions that made the edition, read from Claude Code's own session records: tokens per model, web-search queries,
  pages fetched, subagents, and Claude Code's cost estimate (at API prices — not what a subscription pays). Checked
  against a real session: 19 searches matched exactly. 9 + 10 Nov were made before this, so no session is linked to
  them; tracking starts with the next edition (one session per day keeps the numbers clean). Next: Phase 7, step 7.1.
- 10 Nov 2026 — Phase 7.1 + 7.2 done. Skill `.claude/skills/todays-cards/SKILL.md` = the daily workflow as one
  command `/todays-cards [DATE] [--unattended]`: resumes at the first missing stage; main session only coordinates.
  New subagents in `.claude/agents/`: `researcher` (→ research.json, 8–12 candidates, adds `key_facts_en` with
  outlets), `amharic-writer` (→ stories.json from research.json only, runs validate), `photo-scout` (→ photos.json
  proposals, licence read from the Commons file page, never downloads). Fact-checker + photo-scout run in parallel.
  New `photos.py` (list proposals; `--use 1=1 …` downloads the owner's picks, only Commons/Unsplash/Pexels, ≤ 2400 px,
  fills `image`) and `etdate.py` (Ethiopian date, incl. spoken form; validate.py now errors on a wrong `date_et`).
  etdate checked on leap-year edges (New Year 12 Sep 2023, Genna 2024 = ታኅሣሥ 28). photos.py tested on a temp copy
  (real Commons download, bad host refused). Subagents not yet tried on a real day — first run with the next edition
  (project skills/agents load when a new session starts).
- 10 Nov 2026 — 7.3 done: Claude desktop scheduled task "ዓለም ዛሬ morning draft" (id `alem-zare-morning-draft`,
  every day 06:30, the app adds a few minutes → ~06:40; Auto permission mode). Runs `/todays-cards <today> --unattended`:
  research → write → fact-check → photo proposals, then stops at the photo gate and sends a notification. Never
  downloads photos, approves, posts or pushes. Runs only while the Claude app is open (else at next launch).
  Owner then opens a new session: `/todays-cards DATE` → pick photos → render → video → review → approve.py.
  Watch the first real run (tomorrow): runlog may not find the scheduled session if it runs outside the project folder.
  Next: Phase 8, step 8.1.
- 10 Nov 2026 — Phase 8 done: `share.py` builds two files per edition only from existing checked data (no new AI text):
  `digest.md` (Amharic card text + English summary, key facts, fact-checked claims with source links, read-more links,
  stories left out and why) and `captions.txt` (YouTube title ≤ 100, Instagram, TikTok, YouTube description:
  numbered headlines, outlets, photo credits — with Commons links on YouTube —, music credit, AI-disclosure line,
  5 hashtags from the categories, character count vs each platform limit; DRAFT warning until approved, reminder to
  switch on the AI label). Runs automatically after every render (both files) and every video (captions, music).
  Tested on 10 Nov (no research.json → Amharic + outlets only) and a temp copy with research + factcheck. Next: Phase 9.
- 10 Nov 2026 — 9.1 done: README rewritten as the portfolio front page — architecture diagram (agents, hand-off
  files, scripts, the two human gates, measurement), stage table linking each agent/script, 8 design decisions
  (LLM decides/scripts execute, approval enforced in code, independent fact-checker, hand-off files, guardrails as
  checks, licensing, text for the ear, measuring the AI), "How it was built", updated folder layout and daily usage.
  9.2 partly: Results section with metrics marked *pending* — no approved edition with a saved draft exists yet
  (`evaluate.py --summary` confirms). Next: fill it after the first real `/todays-cards` edition; owner uploads a video.
