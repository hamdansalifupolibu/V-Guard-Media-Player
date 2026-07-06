"""Integration tests for automated model evaluation."""

import json
from pathlib import Path

import pytest

from app.reporting.model_evaluation import ModelEvaluationRunner
from app.analysis.visual_detector import VisualDetector


def test_keyword_evaluation_runs():
    runner = ModelEvaluationRunner()
    metrics, df = runner.evaluate_keyword_filter()
    assert metrics.n_cases >= 5
    assert metrics.word_level_f1 >= 0.9
    assert df["pass"].all()


@pytest.mark.skipif(
    not VisualDetector.is_model_available(),
    reason="ONNX model required",
)
def test_full_evaluation_pipeline():
    runner = ModelEvaluationRunner()
    results = runner.run_all()
    assert "keyword" in results
    assert results["keyword"]["word_level_f1"] >= 0.9
    assert "visual" in results
    assert results["visual"]["n_samples"] >= 5
