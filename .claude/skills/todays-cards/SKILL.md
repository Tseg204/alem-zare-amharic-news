---
name: todays-cards
description: Make the day's ዓለም ዛሬ edition — research, Amharic cards, fact-check, photo proposals, render, draft video, hand-over for human review. Use when the owner asks for "today's cards", a new edition, or to continue a half-finished day. Arguments - optional date YYYY-MM-DD (default today) and --unattended for the scheduled morning run.
argument-hint: "[YYYY-MM-DD] [--unattended]"
---

# /todays-cards — the daily edition

Arguments: `$ARGUMENTS`
- Date: the `YYYY-MM-DD` in the arguments, else today's local date (`date +%F`).
- `--unattended`: started by the morning schedule, nobody is watching. Never ask questions; stop at
  the photo gate (step 5) and notify. Without it, the owner is here: show results and wait where marked.

You are the **coordinator**. The heavy work happens in subagents that get **only the date** as their
prompt — never pass your own notes, so each stage stays independent and checkable. The hand-off files
are described in `docs/pipeline.md`; the rules in `CLAUDE.md` always apply. One edition per session
(so `runlog.py` attributes cost cleanly). Never run `approve.py`, never edit `status`/`approved_*`,
never post anything.

## 0. Where are we? (resume)
Look in `editions/<date>/` and start at the first step whose output is missing or not done:
| exists? | means |
|---|---|
| no folder / no stories.json | start at 1 |
| no research.json | 2 |
| research.json, but stories.json still has the copied stories (`python3 validate.py <date>` says "same headline as … still the copied story?") | 3 |
| no factcheck.json, or open claims in it | 4 |
| photos.json but stories have no `image` | 5 (photo gate) |
| photos set, no cards/ or cards older than stories.json | 6 |
| cards + video, no stories.draft.json | 7 |
| stories.draft.json exists | already handed over — tell the owner, show `runlog.py`, stop |
Tell the owner in one line where you are resuming.

## 1. Start the edition
`python3 render_cards.py --new <date>` (copies yesterday's file as a draft; the date check in
validate.py will fail until step 3 — that's expected). Never overwrite an existing day.

## 2. Research — subagent `researcher`
Agent tool, `subagent_type: "researcher"`, prompt: just the date. It writes `research.json`.
Check: `python3 -c` load it → exactly 5 `selected`, each with 2+ sources. Show the owner the 5
selected titles (unattended: just continue).

## 3. Write — subagent `amharic-writer`
`subagent_type: "amharic-writer"`, prompt: just the date. It writes stories.json (with `speech`,
`cover_speech`, dates from `etdate.py`) and runs validate.py. Re-run `python3 validate.py <date>`
yourself: no ERRORs except a missing factcheck/photos-related one.

## 4. Fact-check + photo scouting — in parallel
Start both in **one message** (they only read stories.json/research.json):
- `subagent_type: "fact-checker"`, prompt: just the date → `factcheck.json`.
- `subagent_type: "photo-scout"`, prompt: just the date → `photos.json`.
Then apply every `corrected` / `rejected` / `unclear` fix to stories.json yourself: change the card
text **and** its `speech`, keep the meaning neutral, never add facts the sources don't give. Run
the fact-checker again (date only) until every claim is `verified` (max 3 rounds; if a claim still
can't be verified, drop that detail from the card). Keep a list of what had to be fixed — the owner
sees it at hand-over.

## 5. Photo gate (owner decides)
`python3 photos.py <date>` lists the proposals. CLAUDE.md: each photo is proposed with link + licence
before it is downloaded.
- **Owner present:** show the list (what it shows, licence, file-page link) and ask which to use.
  Then `python3 photos.py <date> --use 1=1 2=2 …`. If the owner rejects one, ask the photo-scout again
  for that story only, or leave it without a photo (colour block).
- **Unattended:** stop here. Write the hand-over note (step 8) with the photo list, send the
  notification, end the run. The owner continues later with `/todays-cards <date>`.

## 6. Render and check
`python3 render_cards.py <date>`. Fix every validate ERROR, read the WARNINGs, fix every `OVERFLOW!`
(shorten text — keep `speech` in sync). Open the rendered JPEGs in `editions/<date>/cards/` (Read
tool) and look at each one: text readable on the photo, no awkward crop, nothing graphic.

## 7. Draft video + narration check
`python3 make_video.py <date>` (draft → `video/short_DRAFT.mp4`). Read `audio/narration.txt`:
anything the voice will read badly (abbreviations, Latin names, symbols) → fix the `speech` lines,
re-run make_video. Then save the draft for evaluation and the run log:
`python3 evaluate.py --snapshot <date>` and `python3 runlog.py <date>`.

## 8. Hand-over
Tell the owner, short and in this order:
1. The 5 headlines (Amharic) + lead story.
2. Fact-check: N claims, all verified; the ones that needed fixing (before → after).
3. Photos chosen (or, unattended: the proposals to pick from).
4. Warnings worth a look; time, searches and cost from runlog.
5. Next steps for the owner: review the cards in `editions/<date>/cards/` and the draft video
   `video/short_DRAFT.mp4`, edit stories.json if needed, then
   `python3 approve.py <date>` → `python3 make_video.py <date>` → post manually, with the platform's
   AI-generated label switched on.
Never present the text as final.

**Unattended runs:** end with the `PushNotification` tool (if available), one line under 200
characters, e.g. `ዓለም ዛሬ <date>: 5 stories written + fact-checked (2 fixes). Pick photos: /todays-cards <date>`.
If something failed (no internet, validate errors you could not fix), the notification says what
and where it stopped.
