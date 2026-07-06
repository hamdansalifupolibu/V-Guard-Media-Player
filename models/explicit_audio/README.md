# Explicit sexual-sound CNN

Small PyTorch classifier on **log-mel spectrograms**, inspired by:

- Lovenia et al. (2022), *What Did I Just Hear? Detecting Pornographic Sounds in Adult Videos*
- [sexual-content-audio-classifier](https://github.com/xaverhimmelsbach/sexual-content-audio-classifier) (mel spectrogram + moan annotations)

## Setup (one time)

```powershell
python scripts/download_explicit_audio_model.py
```

This caches training spectrograms (~50 MB without the upstream 247 MB YOLO file), trains a **~2 MB** `explicit_audio_cnn.pt`, and saves it here.

## Manual steps

```powershell
python scripts/download_explicit_audio_data.py
python scripts/train_explicit_audio_cnn.py
```

## Add your own training clips

See **“Adding your own audio to improve the explicit-sound model”** in the main [README.md](../../README.md).

```powershell
python scripts/prepare_explicit_audio_clip.py --wav "data\my_clips\clip.wav" --split train --label positive --moan-start 3 --moan-end 6
python scripts/train_explicit_audio_cnn.py
```

## Test a clip

```powershell
python tests/test_explicit_audio_detector.py path\to\clip.wav
```
