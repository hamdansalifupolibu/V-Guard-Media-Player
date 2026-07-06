# V-Guard Demo Script (5–8 minutes)

Use after a **fresh re-scan** on demo videos with **⬛🔇 Hide + mute** selected.

## Before you start

```powershell
cd "C:\Users\Gebruiker\OneDrive\Desktop\V Guard project"
.\venv\Scripts\activate
python app\main.py
```

Settings (once):

- Default moderation: **⬛🔇 Hide + mute**
- **Require scan before play**: on
- **Auto-scan on load**: on (optional — skips the scan prompt)
- Frame interval: **1.0 s**

## 1. Safe content (30 s)

1. Open a known **safe** clip (or your beach/swimwear test if labeled safe).
2. Let progressive scan finish (or first chunk, then play).
3. Point out: no blackout; status shows scan progress then complete.
4. **View results** — few or no visual segments.

## 2. Flagged content (1–2 min)

1. Open your test video with known explicit segment.
2. Show moderation cards: click **⬛ Hide scene** then **⬛🔇 Hide + mute** — purple border stays on selection.
3. Play through the flagged section:
   - **Black screen** ~2 s before the scene
   - **Mute** on bad audio words (if any)
   - Blackout ends ~1 s after (not lingering too long on safe footage)
4. If you seek past unscanned time during background scan, mention the status warning.

## 3. Settings & policy (30 s)

1. Open **Settings** — threshold, frame interval, scan toggles.
2. Mention `data/blocked_words.txt` is editable for institution policy.

## 4. Thesis metrics (30 s)

```powershell
python scripts/run_model_evaluation.py
```

Show `data/thesis/figures/M0_model_metrics_summary.png` and M1–M3 — pre-trained Open-NSFW evaluated on **your** labeled images.

## 5. Optional — Educational download (30 s)

1. Sidebar → **Downloads**, confirm educational checkbox.
2. Paste an allowed URL → download → **Play in player** → scan.

## Closing line

> “V-Guard scans locally in chunks, applies blackout and mute from stored timestamps, and keeps the user in control with visible moderation modes and per-segment enable/disable.”
