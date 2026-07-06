# Visual safety model

V-Guard uses the pre-trained **Yahoo Open-NSFW** classifier (ONNX) for visual moderation.

## Download

From the project root:

```powershell
python scripts/download_visual_model.py
```

This saves `open_nsfw.onnx` (~24 MB) in this folder.

## Usage

- Frames are sampled every 2 seconds during pre-scan.
- Each frame receives an NSFW probability score.
- Scores above the confidence threshold (default **0.65**) are grouped into timestamp ranges and stored in SQLite.

## Notes

- This is a prototype classifier; expect false positives and false negatives.
- Do not commit `open_nsfw.onnx` to Git (see root `.gitignore`).
