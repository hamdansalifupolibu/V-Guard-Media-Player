"""Run automated model evaluation and export thesis performance artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from app.analysis.keyword_filter import KeywordFilter
from app.analysis.speech_detector import TranscriptSegment, TranscriptWord
from app.analysis.visual_detector import VisualDetector
from app.config import (
    BLOCKED_WORDS_PATH,
    THESIS_FIGURES_DIR,
    VISUAL_CONFIDENCE_THRESHOLD,
)
from app.reporting.model_metrics import (
    ClassificationMetrics,
    KeywordMetrics,
    compute_classification_metrics,
    compute_keyword_metrics,
)

EVAL_DIR = Path(__file__).resolve().parents[2] / "data" / "evaluation"
EVAL_FRAMES_DIR = EVAL_DIR / "frames"
PRIMARY = "#7C3AED"
DANGER = "#EF4444"
SAFE = "#10B981"


class ModelEvaluationRunner:
    """Evaluate visual classifier and keyword pipeline; write metrics + plots."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = Path(output_dir or THESIS_FIGURES_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_all(self, threshold: float = VISUAL_CONFIDENCE_THRESHOLD) -> dict:
        results: dict = {"threshold": threshold}

        keyword_metrics, keyword_df = self.evaluate_keyword_filter()
        results["keyword"] = keyword_metrics.to_dict()
        keyword_df.to_csv(self.output_dir / "keyword_evaluation_details.csv", index=False)

        if VisualDetector.is_model_available():
            visual_metrics, visual_df = self.evaluate_visual_model(threshold)
            results["visual"] = visual_metrics.to_dict()
            visual_df.to_csv(self.output_dir / "visual_evaluation_details.csv", index=False)
            self._plot_visual_confusion_matrix(visual_metrics)
            self._plot_roc_curve(visual_df, threshold)
            self._plot_pr_curve(visual_df, threshold)
            self._plot_calibration(visual_df)
            self._plot_threshold_metrics_curve(visual_df)
        else:
            results["visual"] = {"error": "ONNX model not found"}

        self._plot_keyword_metrics(keyword_metrics)
        self._write_metrics_summary(results)

        with open(self.output_dir / "model_metrics.json", "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)

        return results

    def evaluate_keyword_filter(self) -> tuple[KeywordMetrics, pd.DataFrame]:
        cases_path = EVAL_DIR / "keyword_test_cases.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
        filt = KeywordFilter(BLOCKED_WORDS_PATH)

        expected_sets: list[set[str]] = []
        detected_sets: list[set[str]] = []
        rows: list[dict] = []

        for case in cases:
            segments = [_dict_to_segment(s) for s in case["segments"]]
            hits, _ranges = filt.scan_segments(segments)
            detected = {h.matched_keyword for h in hits}
            expected = set(case.get("expected_keywords", []))
            expected_sets.append(expected)
            detected_sets.append(detected)
            rows.append(
                {
                    "case_id": case["id"],
                    "description": case.get("description", ""),
                    "expected": ",".join(sorted(expected)),
                    "detected": ",".join(sorted(detected)),
                    "pass": expected == detected,
                }
            )

        metrics = compute_keyword_metrics(expected_sets, detected_sets)
        return metrics, pd.DataFrame(rows)

    def evaluate_visual_model(
        self, threshold: float
    ) -> tuple[ClassificationMetrics, pd.DataFrame]:
        """Run Open-NSFW on synthetic safe frames + optional labeled challenge set."""
        detector = VisualDetector(threshold=threshold)
        rows: list[dict] = []

        for name, label, generator in _safe_test_generators():
            frame = generator()
            pred = detector.predict_frame(frame, 0.0)
            rows.append(
                {
                    "sample": name,
                    "true_label": label,
                    "nsfw_probability": pred.confidence,
                    "predicted_label": 1 if pred.is_flagged else 0,
                    "category": "safe_corpus",
                }
            )

        challenge_path = EVAL_DIR / "visual_challenge_labels.csv"
        if challenge_path.is_file():
            challenges = pd.read_csv(challenge_path, comment="#")
            for _, row in challenges.iterrows():
                frame = _load_challenge_frame(row)
                if frame is None:
                    continue
                pred = detector.predict_frame(frame, 0.0)
                rows.append(
                    {
                        "sample": row["sample_name"],
                        "true_label": int(row["true_label"]),
                        "nsfw_probability": pred.confidence,
                        "predicted_label": 1 if pred.is_flagged else 0,
                        "category": row.get("category", "challenge"),
                    }
                )

        df = pd.DataFrame(rows)
        metrics = compute_classification_metrics(
            df["true_label"].to_numpy(),
            df["nsfw_probability"].to_numpy(),
            threshold=threshold,
        )
        return metrics, df

    def _plot_visual_confusion_matrix(self, metrics: ClassificationMetrics) -> Path:
        fig, ax = plt.subplots(figsize=(5, 4))
        cm = np.array(
            [
                [metrics.true_negatives, metrics.false_positives],
                [metrics.false_negatives, metrics.true_positives],
            ]
        )
        im = ax.imshow(cm, cmap="Purples")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred Safe", "Pred Unsafe"])
        ax.set_yticklabels(["True Safe", "True Unsafe"])
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", color="white", fontsize=14)
        ax.set_title("Visual model — confusion matrix")
        fig.colorbar(im, ax=ax, fraction=0.046)
        fig.tight_layout()
        path = self.output_dir / "M1_visual_confusion_matrix.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _plot_roc_curve(self, df: pd.DataFrame, threshold: float) -> Path:
        y_true = df["true_label"].to_numpy()
        y_prob = df["nsfw_probability"].to_numpy()
        thresholds = np.linspace(0, 1, 50)
        tprs, fprs = [], []
        for t in thresholds:
            pred = (y_prob >= t).astype(int)
            tp = np.sum((pred == 1) & (y_true == 1))
            fn = np.sum((pred == 0) & (y_true == 1))
            fp = np.sum((pred == 1) & (y_true == 0))
            tn = np.sum((pred == 0) & (y_true == 0))
            tprs.append(tp / (tp + fn) if (tp + fn) else 0)
            fprs.append(fp / (fp + tn) if (fp + tn) else 0)

        fig, ax = plt.subplots(figsize=(6, 5))
        ax.plot(fprs, tprs, color=PRIMARY, linewidth=2, label="ROC")
        ax.plot([0, 1], [0, 1], "--", color="#999", label="Random")
        # Operating point at default threshold
        pred = (y_prob >= threshold).astype(int)
        fp_rate = np.sum((pred == 1) & (y_true == 0)) / max(np.sum(y_true == 0), 1)
        tp_rate = np.sum((pred == 1) & (y_true == 1)) / max(np.sum(y_true == 1), 1)
        ax.scatter([fp_rate], [tp_rate], color=DANGER, s=60, zorder=5, label="Operating point")
        ax.set_xlabel("False positive rate")
        ax.set_ylabel("True positive rate (recall)")
        ax.set_title("Visual model — ROC curve")
        ax.legend()
        fig.tight_layout()
        path = self.output_dir / "M2_visual_roc_curve.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _plot_pr_curve(self, df: pd.DataFrame, threshold: float) -> Path:
        y_true = df["true_label"].to_numpy()
        y_prob = df["nsfw_probability"].to_numpy()
        order = np.argsort(-y_prob)
        y_true = y_true[order]
        y_prob = y_prob[order]
        tp_cum = np.cumsum(y_true)
        fp_cum = np.cumsum(1 - y_true)
        precision = tp_cum / (tp_cum + fp_cum + 1e-9)
        recall = tp_cum / (np.sum(y_true) + 1e-9)

        fig, ax = plt.subplots(figsize=(6, 5))
        ax.plot(recall, precision, color=PRIMARY, linewidth=2)
        ax.axvline(
            VISUAL_CONFIDENCE_THRESHOLD,
            color=DANGER,
            linestyle="--",
            alpha=0.5,
            label=f"Default threshold {VISUAL_CONFIDENCE_THRESHOLD}",
        )
        ax.set_xlabel("Recall")
        ax.set_ylabel("Precision")
        ax.set_title("Visual model — precision-recall curve")
        ax.legend()
        fig.tight_layout()
        path = self.output_dir / "M3_visual_precision_recall.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _plot_calibration(self, df: pd.DataFrame) -> Path:
        fig, ax = plt.subplots(figsize=(6, 5))
        bins = np.linspace(0, 1, 11)
        df = df.copy()
        df["bin"] = pd.cut(df["nsfw_probability"], bins=bins, include_lowest=True)
        grouped = df.groupby("bin", observed=True)
        mean_pred = grouped["nsfw_probability"].mean()
        mean_true = grouped["true_label"].mean()
        ax.plot([0, 1], [0, 1], "--", color="#999", label="Perfect calibration")
        ax.scatter(mean_pred, mean_true, color=PRIMARY, s=80, zorder=3)
        ax.set_xlabel("Mean predicted NSFW probability")
        ax.set_ylabel("Fraction actually unsafe (label)")
        ax.set_title("Visual model — calibration (Brier / reliability)")
        ax.legend()
        fig.tight_layout()
        path = self.output_dir / "M4_visual_calibration.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _plot_threshold_metrics_curve(self, df: pd.DataFrame) -> Path:
        thresholds = np.arange(0.1, 0.96, 0.05)
        y_true = df["true_label"].to_numpy()
        y_prob = df["nsfw_probability"].to_numpy()
        f1s, precisions, recalls = [], [], []
        for t in thresholds:
            m = compute_classification_metrics(y_true, y_prob, threshold=t)
            f1s.append(m.f1_score)
            precisions.append(m.precision)
            recalls.append(m.recall)

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.plot(thresholds, precisions, label="Precision", color=PRIMARY)
        ax.plot(thresholds, recalls, label="Recall", color=DANGER)
        ax.plot(thresholds, f1s, label="F1-score", color=SAFE, linewidth=2)
        ax.axvline(VISUAL_CONFIDENCE_THRESHOLD, linestyle="--", color="#333", label="Default threshold")
        ax.set_xlabel("Threshold")
        ax.set_ylabel("Score")
        ax.set_title("Visual model — metrics vs. threshold")
        ax.legend()
        ax.set_ylim(0, 1.05)
        fig.tight_layout()
        path = self.output_dir / "M5_visual_metrics_vs_threshold.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _plot_keyword_metrics(self, metrics: KeywordMetrics) -> Path:
        fig, ax = plt.subplots(figsize=(6, 4))
        names = ["Precision", "Recall", "F1", "Case accuracy"]
        values = [
            metrics.word_level_precision,
            metrics.word_level_recall,
            metrics.word_level_f1,
            metrics.case_accuracy,
        ]
        bars = ax.bar(names, values, color=[PRIMARY, DANGER, SAFE, "#6366F1"])
        ax.set_ylim(0, 1.05)
        ax.set_title("Keyword filter — detection metrics")
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.02, f"{val:.2f}", ha="center")
        fig.tight_layout()
        path = self.output_dir / "M6_keyword_metrics.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _write_metrics_summary(self, results: dict) -> Path:
        lines = ["V-Guard Model Performance Summary", "=" * 40, ""]
        if "visual" in results and "error" not in results["visual"]:
            v = results["visual"]
            lines.extend(
                [
                    "VISUAL MODEL (Open-NSFW binary classifier)",
                    f"  Samples evaluated: {v['n_samples']}",
                    f"  Threshold: {v['threshold']}",
                    f"  Accuracy:  {v['accuracy']}",
                    f"  Precision: {v['precision']}",
                    f"  Recall:    {v['recall']}",
                    f"  F1-score:  {v['f1_score']}",
                    f"  Specificity (TNR): {v['specificity']}",
                    f"  FPR: {v['false_positive_rate']}  |  FNR: {v['false_negative_rate']}",
                    f"  Brier score (prob MSE): {v['brier_score']}",
                    f"  Log loss: {v['log_loss']}",
                    f"  ROC-AUC:  {v.get('roc_auc', 'N/A')}",
                    f"  TP={v['true_positives']} TN={v['true_negatives']} "
                    f"FP={v['false_positives']} FN={v['false_negatives']}",
                    "",
                ]
            )
        if "keyword" in results:
            k = results["keyword"]
            lines.extend(
                [
                    "KEYWORD FILTER (audio moderation)",
                    f"  Test cases: {k['n_cases']}",
                    f"  Word-level precision: {k['word_level_precision']}",
                    f"  Word-level recall:    {k['word_level_recall']}",
                    f"  Word-level F1:        {k['word_level_f1']}",
                    f"  Case accuracy:        {k['case_accuracy']}",
                    f"  TP={k['true_positives']} FP={k['false_positives']} FN={k['false_negatives']}",
                    "",
                    "Note: Visual recall/sensitivity requires a labeled unsafe test set",
                    "(institutional / research dataset). Safe-corpus tests measure specificity.",
                ]
            )
        text = "\n".join(lines)
        path = self.output_dir / "M0_model_metrics_summary.txt"
        path.write_text(text, encoding="utf-8")

        fig, ax = plt.subplots(figsize=(9, 6))
        ax.axis("off")
        ax.text(0.02, 0.98, text, va="top", family="monospace", fontsize=10)
        fig.tight_layout()
        fig.savefig(self.output_dir / "M0_model_metrics_summary.png", dpi=150)
        plt.close(fig)
        return path


def _dict_to_segment(data: dict) -> TranscriptSegment:
    words = tuple(
        TranscriptWord(
            word=w["word"],
            start_sec=float(w["start"]),
            end_sec=float(w["end"]),
            confidence=float(w.get("conf", 0.9)),
        )
        for w in data.get("words", [])
    )
    return TranscriptSegment(
        text=data.get("text", ""),
        start_sec=float(data.get("start", 0)),
        end_sec=float(data.get("end", 0)),
        words=words,
    )


def _safe_test_generators():
    def black():
        return np.zeros((224, 224, 3), dtype=np.uint8)

    def white():
        return np.full((224, 224, 3), 255, dtype=np.uint8)

    def blue():
        img = np.zeros((224, 224, 3), dtype=np.uint8)
        img[:, :, 0] = 200
        return img

    def gradient():
        row = np.linspace(0, 255, 224, dtype=np.uint8)
        img = np.tile(row, (224, 1))
        return np.stack([img] * 3, axis=-1)

    def noise_low():
        rng = np.random.default_rng(42)
        return rng.integers(0, 80, (224, 224, 3), dtype=np.uint8)

    return [
        ("black_frame", 0, black),
        ("white_frame", 0, white),
        ("blue_frame", 0, blue),
        ("gradient_frame", 0, gradient),
        ("low_noise_frame", 0, noise_low),
    ]


def _load_challenge_frame(row: pd.Series) -> np.ndarray | None:
    """
    Load a labeled evaluation frame.

    Prefer `image_file` column (path under data/evaluation/).
    Falls back to built-in synthetic names for legacy CSV rows.
    """
    if "image_file" in row and pd.notna(row["image_file"]) and str(row["image_file"]).strip():
        rel = Path(str(row["image_file"]).strip())
        path = rel if rel.is_absolute() else EVAL_DIR / rel
        if not path.is_file():
            return None
        frame = cv2.imread(str(path))
        return frame if frame is not None else None

    name = str(row["sample_name"])
    if name == "high_luminance":
        return np.full((224, 224, 3), 240, dtype=np.uint8)
    if name == "mid_gray":
        return np.full((224, 224, 3), 128, dtype=np.uint8)
    return np.zeros((224, 224, 3), dtype=np.uint8)
