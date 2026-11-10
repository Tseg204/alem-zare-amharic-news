# Background music for the videos

Only royalty-free tracks whose licence allows use in YouTube / Instagram / TikTok videos:
- YouTube Audio Library (studio.youtube.com → Audio library) — check whether the track needs attribution
- Pixabay Music (pixabay.com/music)

Never commercial songs (they get muted or copyright-claimed).

Put the audio file (mp3/m4a/wav) in this folder and add an entry to `tracks.json`:
```json
[
  {
    "file": "calm-news-bed.mp3",
    "title": "Track title",
    "artist": "Artist name",
    "source": "https://… (the page you downloaded it from)",
    "licence": "YouTube Audio Library — no attribution required",
    "attribution": ""
  }
]
```
`attribution` = the exact credit text the licence asks for (leave empty if none); it is added to
the edition's `credits.md` so it can go in the caption.

Optional `"start": 18` (seconds) skips the beginning of a track (e.g. a slow intro).

A track with `"default": true` is used every day; otherwise tracks rotate by date. To choose one for a day, add `"music": "calm-news-bed.mp3"` to that
day's `stories.json`.
