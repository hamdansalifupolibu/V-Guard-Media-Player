"""Tests for classification metric helpers."""

import numpy as np

from app.reporting.model_metrics import (
    compute_classification_metrics,
    compute_keyword_metrics,
)


def test_perfect_classifier():
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.9, 0.8])
    m = compute_classification_metrics(y_true, y_prob, threshold=0.5)
    assert m.accuracy == 1.0
    assert m.f1_score == 1.0
    assert m.brier_score < 0.05


def test_keyword_metrics_perfect():
    expected = [{"damn"}, set()]
    detected = [{"damn"}, set()]
    m = compute_keyword_metrics(expected, detected)
    assert m.word_level_f1 == 1.0
    assert m.case_accuracy == 1.0


def test_keyword_false_positive():
    expected = [set()]
    detected = [{"damn"}]
    m = compute_keyword_metrics(expected, detected)
    assert m.false_positives == 1
    assert m.word_level_precision == 0.0
