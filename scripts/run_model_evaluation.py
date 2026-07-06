"""Run full model evaluation and write thesis performance artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import THESIS_FIGURES_DIR
from app.reporting.model_evaluation import ModelEvaluationRunner


def main() -> int:
    runner = ModelEvaluationRunner(THESIS_FIGURES_DIR)
    results = runner.run_all()
    print("Model evaluation complete.")
    print(f"Output: {THESIS_FIGURES_DIR.resolve()}")
    if "visual" in results and "error" not in results.get("visual", {}):
        v = results["visual"]
        print(
            f"Visual — Acc={v['accuracy']} Prec={v['precision']} "
            f"Rec={v['recall']} F1={v['f1_score']} Brier={v['brier_score']}"
        )
    if "keyword" in results:
        k = results["keyword"]
        print(
            f"Keyword — P={k['word_level_precision']} R={k['word_level_recall']} "
            f"F1={k['word_level_f1']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
