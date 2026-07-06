# Visual validation dataset — step-by-step guide

Use this guide to build `visual_challenge_labels.csv` so your thesis can report **precision, recall, and F1** on both safe and unsafe examples (not only specificity on safe frames).

---

## What you are building

| Item | Purpose |
|------|---------|
| `frames/safe/*.jpg` | Images you label as **safe** (`true_label = 0`) |
| `frames/unsafe/*.jpg` | Images you label as **unsafe** (`true_label = 1`) per your project policy |
| `visual_challenge_labels.csv` | One row per image: filename, label, notes |

V-Guard runs the **same Open-NSFW model** on these images and compares predictions to your labels.

---

## Step 1 — Create folders

```text
data/evaluation/frames/safe/
data/evaluation/frames/unsafe/
```

Already created in the project. Put `.jpg` or `.png` files inside.

---

## Step 2 — Collect **safe** images (easy, online, legal)

Use **royalty-free** sites (check license: free for research/education):

- [Pexels](https://www.pexels.com/)
- [Pixabay](https://pixabay.com/)
- [Unsplash](https://unsplash.com/)
- [Wikimedia Commons](https://commons.wikimedia.org/) (check each file license)

**Search ideas:** landscape, classroom, office, sports, nature, family (fully clothed), cooking, technology.

**How many:** at least **15–30** safe images for a solid thesis table.

**Save as:** `data/evaluation/frames/safe/pexels_landscape_01.jpg` (unique names).

**Label:** `true_label = 0`

---

## Step 3 — Collect **unsafe** images (careful — ethics & university rules)

You need some **positive** examples (`true_label = 1`) so recall/F1 are meaningful.

**Recommended approaches (in order):**

### Option A — Frames from your own demo videos (best for BSc)

1. Use videos you already test with V-Guard (your own files or clips you have **permission** to use).
2. Play the video and note timestamps where content matches your **moderation policy** (visual nudity, violence, etc.).
3. Export a single frame:
   - Pause VLC at that time → screenshot, **or**
   - FFmpeg:

```powershell
ffmpeg -ss 00:01:20 -i "your_video.mp4" -frames:v 1 data/evaluation/frames/unsafe/demo_01.jpg
```

4. In your thesis, state: *“Unsafe validation frames were manually labeled from test clips used in the prototype.”*

### Option B — Frames already flagged by V-Guard

1. Scan a video in the app.
2. Open `data/vguard.db` or **View results** and note flagged times.
3. Export frames at those timestamps (FFmpeg above).
4. **Manually confirm** each frame is actually policy-violating → `true_label = 1`.
5. If the model was wrong, label `0` and mention as false positive in your report.

### Option C — Academic / research datasets (cite in thesis)

Some research papers use public **NSFW detection** benchmarks. Only use if:

- Your university allows it
- License permits research use
- You **cite the dataset** in your references

Search literature for: *“NSFW detection dataset”*, *“content moderation benchmark”*.  
Do **not** use random adult websites or pirated material.

**How many unsafe frames:** at least **10–20** (more is better). Balance safe vs unsafe (e.g. 25 safe + 15 unsafe).

---

## Step 4 — Fill in `visual_challenge_labels.csv`

Open `data/evaluation/visual_challenge_labels.csv`.

**Columns:**

| Column | Meaning |
|--------|---------|
| `sample_name` | Short unique id (no spaces), e.g. `pexels_landscape_01` |
| `true_label` | `0` = safe, `1` = unsafe |
| `category` | `safe` or `unsafe` (or `challenge`) |
| `image_file` | Path under `data/evaluation/`, e.g. `frames/safe/pexels_landscape_01.jpg` |
| `notes` | One sentence for your thesis appendix |

**Example rows:**

```csv
sample_name,true_label,category,image_file,notes
pexels_landscape_01,0,safe,frames/safe/pexels_landscape_01.jpg,Pexels landscape - safe
pexels_office_02,0,safe,frames/safe/pexels_office_02.jpg,Office scene - safe
demo_video_unsafe_01,1,unsafe,frames/unsafe/demo_01.jpg,Manual label - demo clip 1 at 01:20
demo_video_unsafe_02,1,unsafe,frames/unsafe/demo_02.jpg,Manual label - nudity policy
```

Lines starting with `#` are ignored by pandas if you remove them — **delete comment lines** before running evaluation, or keep only valid CSV rows.

---

## Step 5 — Run evaluation and refresh PNGs

```powershell
.\venv\Scripts\activate
python scripts/run_model_evaluation.py
```

Check:

- `data/thesis/figures/model_metrics.json`
- `M0` … `M6` PNG files
- `visual_evaluation_details.csv` (per-image predictions)

---

## Step 6 — Write up in your thesis

Report:

- Number of safe vs unsafe validation images
- How labels were obtained (manual / from demo videos)
- Metrics: accuracy, precision, recall, F1, Brier score, ROC-AUC
- Limitations: small set, English-only audio, pre-trained model not fine-tuned

---

## Ethics checklist

- [ ] No pirated films or illegal downloads  
- [ ] No sharing of explicit material outside your secured project folder  
- [ ] Supervisor approved approach for unsafe samples  
- [ ] Dataset described in methodology; no public redistribution of unsafe frames  

---

## Quick checklist

1. [ ] 15+ images in `frames/safe/`  
2. [ ] 10+ images in `frames/unsafe/` (manual labels)  
3. [ ] CSV updated with `image_file` paths  
4. [ ] `python scripts/run_model_evaluation.py` runs without errors  
5. [ ] Confusion matrix shows both TP and TN (not only safe rows)  
