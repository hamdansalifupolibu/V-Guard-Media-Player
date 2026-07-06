# Model evaluation datasets

## Keyword tests (`keyword_test_cases.json`)

Automated transcript cases with expected blocked words.  
Run: `python scripts/run_model_evaluation.py`

## Visual tests

- **Safe corpus**: synthetic frames (black, white, blue, etc.) — all labeled `0` (safe).
- **Challenge set**: `visual_challenge_labels.csv` — extend with frames you manually label.

### Important (thesis)

| Model | Appropriate metrics |
|-------|---------------------|
| Visual (binary classifier) | Accuracy, precision, recall, F1, **Brier score** (MSE on probabilities), log loss, ROC-AUC, confusion matrix |
| Keyword filter | Word-level precision/recall/F1 |

**MSE** applies to probability calibration (Brier score), not raw pixels.  
**Recall on unsafe content** needs a properly labeled unsafe validation set.

**→ Step-by-step instructions:** [VISUAL_VALIDATION_GUIDE.md](VISUAL_VALIDATION_GUIDE.md)

Place images in `frames/safe/` and `frames/unsafe/`, then list them in `visual_challenge_labels.csv` with column `image_file` (e.g. `frames/safe/photo01.jpg`).
