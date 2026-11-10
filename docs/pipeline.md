# Pipeline stages and hand-off files

Each day's work runs as separate stages. Every stage writes a file into `editions/YYYY-MM-DD/`,
and the next stage reads only that file. This makes each step checkable on its own and leaves a
record of *why* each story and each number is on a card.

```
1. Research      → research.json    candidate stories + source links, 5 selected
2. Write         → stories.json     Amharic cards (headline, body, stats, note, speech)
3. Fact-check    → factcheck.json   every number / name / date → 2+ sources → verdict
   (separate subagent: sees only stories.json + research.json, never the writer's reasoning)
4. Validate      → validate.py      rules + "is every number on a card fact-checked?"
5. Render/video  → cards/, video/short_DRAFT.mp4 (red DRAFT banner)
6. Human review  → the owner checks, edits, then runs approve.py (types "yes")
7. Final video   → make_video.py makes short.mp4 only for approved editions; owner posts manually
```

## research.json (stage 1)

```json
{
  "date_gc": "2026-11-10",
  "searched_at": "2026-11-10T07:30",
  "candidates": [
    {
      "id": "moyale-refugees",
      "title_en": "Thousands flee Moyale clashes into Kenya",
      "summary_en": "One or two neutral English sentences: who, what, where, when.",
      "category": "Africa",                      // world | Africa | health | economy | tech | sport | climate …
      "horn_of_africa": true,
      "sources": [
        {"outlet": "UNHCR", "url": "https://…", "published": "2026-11-08"},
        {"outlet": "Al Jazeera", "url": "https://…", "published": "2026-11-09"}
      ],
      "selected": true,
      "story": 2,                                // card number 1–5 when selected
      "reason": "Why it was picked, or why it was left out"
    }
  ]
}
```

Rules (checked by `validate.py`): exactly 5 candidates `selected`, each with a distinct `story`
number 1–5 and 2+ `https://` sources from different websites. Warning if no Horn of Africa story
was found among the candidates, or if a selected one is missing.

## factcheck.json (stage 3)

```json
{
  "checked_at": "2026-11-10T08:10",
  "checked_by": "fact-checker subagent",
  "claims": [
    {
      "story": 2,
      "field": "body",                           // headline | body | stats | note
      "text": "ወደ 36,000 የሚጠጉ ኢትዮጵያውያን",          // the exact Amharic words as on the card
      "claim_en": "About 36,000 Ethiopians have crossed into Kenya (UNHCR figure).",
      "status": "verified",                      // verified | corrected | rejected | unclear
      "sources": [
        {"outlet": "UNHCR", "url": "https://…", "says": "Short paraphrase of what the source states"},
        {"outlet": "The EastAfrican", "url": "https://…", "says": "…"}
      ],
      "fix": ""                                  // for corrected / rejected / unclear: what to change
    }
  ]
}
```

What counts as a claim: every number (figures, dates, counts, money, percentages), every person
or place name tied to an action, every attribution ("X said that …"), and the core event itself.

Rules (checked by `validate.py`):
- `verified` needs 2+ sources from different websites.
- `rejected` or `unclear` → ERROR: fix the card (or drop the story) before rendering.
- `corrected` → the writer must apply `fix`, update `text`, and the checker re-verifies it
  (so it becomes `verified`). Left as `corrected` → ERROR.
- Every number on a card (headline, body, stats, note) must appear in a claim of the same story → else ERROR.
- A claim whose `text` is no longer on the card → WARNING (the card changed after the check).
- `factcheck.json` missing → WARNING for now (editions before 10 Nov 2026 have none).
