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

## Phase 2 — Rules checked by code (`validate.py`) ← *next*

- [ ] 2.1 Check `stories.json` structure (5 stories, required fields, 0–2 stats).
- [ ] 2.2 Editorial rules: no «…» / quotation marks, headline ≤ ~8 words, no flag emoji.
- [ ] 2.3 Photo rules: credit + source URL present, licence in the allowed list (no NC).
- [ ] 2.4 Narration rules: no Latin letters or digits left in `speech`.
- [ ] 2.5 Run it automatically at the start of `render_cards.py`.

## Phase 3 — Clear pipeline stages with saved hand-offs

- [ ] 3.1 `research.json` — candidate stories + source links (research step output).
- [ ] 3.2 `factcheck.json` — each claim (number/name/date) → 2+ sources → verified / rejected.
- [ ] 3.3 Separate fact-checker (a Claude Code subagent that only sees the draft + sources).
- [ ] 3.4 Write the stages + hand-off files into CLAUDE.md.

## Phase 4 — Human approval gate

- [ ] 4.1 `"status": "draft" | "approved"` in `stories.json`.
- [ ] 4.2 `make_video.py` / exports refuse to run on a draft.

## Phase 5 — Measuring quality (evaluation)

- [ ] 5.1 Save the AI's first draft (`stories.draft.json`) before the owner edits.
- [ ] 5.2 Script comparing draft vs approved → % of headlines/bodies changed, kinds of fixes.
- [ ] 5.3 Weekly summary table (great for the portfolio).

## Phase 6 — Run log (observability)

- [ ] 6.1 `run_log.json` per edition: searches, sources, validation failures, time, cost (tokens + Azure TTS).

## Phase 7 — Packaging & automation

- [ ] 7.1 Claude Code skill `/todays-cards` for the daily workflow.
- [ ] 7.2 Subagents: researcher, fact-checker, Amharic writer, photo scout.
- [ ] 7.3 Morning scheduled run that prepares a *draft* and notifies the owner (never auto-posts).

## Phase 8 — Personal use & sharing extras

- [ ] 8.1 `digest.md` per day — longer summaries + links, for reading yourself.
- [ ] 8.2 `captions.txt` per day — ready-to-paste caption, hashtags, credits per platform.

## Phase 9 — Portfolio

- [~] 9.1 README: architecture diagram, design decisions (why human review, why separate checker…).
- [~] 9.2 Quality numbers from Phase 5 + a sample video / screenshots.

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
