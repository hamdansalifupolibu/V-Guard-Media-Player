"""Classification and probability calibration metrics for thesis evaluation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ClassificationMetrics:
    """Standard metrics for binary classifiers (visual NSFW model)."""

    n_samples: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    specificity: float
    false_positive_rate: float
    false_negative_rate: float
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    # Probability-based (treat NSFW score as P(unsafe))
    brier_score: float  # MSE between probability and 0/1 label
    log_loss: float
    roc_auc: float | None
    mean_predicted_prob: float
    threshold: float

    def to_dict(self) -> dict:
        return {
            "n_samples": self.n_samples,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "specificity": self.specificity,
            "false_positive_rate": self.false_positive_rate,
            "false_negative_rate": self.false_negative_rate,
            "true_positives": self.true_positives,
            "true_negatives": self.true_negatives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "brier_score": self.brier_score,
            "log_loss": self.log_loss,
            "roc_auc": self.roc_auc,
            "mean_predicted_prob": self.mean_predicted_prob,
            "threshold": self.threshold,
        }


@dataclass(frozen=True)
class KeywordMetrics:
    """Metrics for keyword detection on transcript test cases."""

    n_cases: int
    word_level_precision: float
    word_level_recall: float
    word_level_f1: float
    case_accuracy: float
    true_positives: int
    false_positives: int
    false_negatives: int

    def to_dict(self) -> dict:
        return {
            "n_cases": self.n_cases,
            "word_level_precision": self.word_level_precision,
            "word_level_recall": self.word_level_recall,
            "word_level_f1": self.word_level_f1,
            "case_accuracy": self.case_accuracy,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
        }


def compute_classification_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.65,
) -> ClassificationMetrics:
    """
    Compute binary classification metrics.

    For the visual model, y_prob is NSFW probability and y_true is 1=unsafe, 0=safe.
    Brier score is the MSE between predicted probability and the true label.
    """
    y_true = np.asarray(y_true, dtype=int).reshape(-1)
    y_prob = np.asarray(y_prob, dtype=float).reshape(-1)
    y_prob = np.clip(y_prob, 1e-7, 1.0 - 1e-7)
    y_pred = (y_prob >= threshold).astype(int)

    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))
    n = len(y_true)

    accuracy = (tp + tn) / n if n else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0

    brier = float(np.mean((y_prob - y_true) ** 2))
    log_loss = float(
        -np.mean(y_true * np.log(y_prob) + (1 - y_true) * np.log(1 - y_prob))
    )

    roc_auc = _roc_auc(y_true, y_prob)

    return ClassificationMetrics(
        n_samples=n,
        accuracy=round(accuracy, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1, 4),
        specificity=round(specificity, 4),
        false_positive_rate=round(fpr, 4),
        false_negative_rate=round(fnr, 4),
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn,
        brier_score=round(brier, 4),
        log_loss=round(log_loss, 4),
        roc_auc=round(roc_auc, 4) if roc_auc is not None else None,
        mean_predicted_prob=round(float(np.mean(y_prob)), 4),
        threshold=threshold,
    )


def _roc_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    try:
        from sklearn.metrics import roc_auc_score

        return float(roc_auc_score(y_true, y_prob))
    except Exception:
        # Manual AUC trapezoid
        order = np.argsort(-y_prob)
        y_true = y_true[order]
        y_prob = y_prob[order]
        tps = np.cumsum(y_true)
        fps = np.cumsum(1 - y_true)
        tpr = tps / tps[-1] if tps[-1] else tps
        fpr = fps / fps[-1] if fps[-1] else fps
        return float(np.trapz(tpr, fpr))


def compute_keyword_metrics(
    expected_keywords: list[set[str]],
    detected_keywords: list[set[str]],
) -> KeywordMetrics:
    """Compare expected vs detected keyword sets per test case."""
    tp = fp = fn = 0
    case_hits = 0
    n = len(expected_keywords)

    for expected, detected in zip(expected_keywords, detected_keywords):
        tp += len(expected & detected)
        fp += len(detected - expected)
        fn += len(expected - detected)
        if expected == detected:
            case_hits += 1

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )

    return KeywordMetrics(
        n_cases=n,
        word_level_precision=round(precision, 4),
        word_level_recall=round(recall, 4),
        word_level_f1=round(f1, 4),
        case_accuracy=round(case_hits / n, 4) if n else 0.0,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
    )
