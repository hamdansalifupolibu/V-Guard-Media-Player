"""Generate thesis PNG figures and CSV summaries from V-Guard scan data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import THESIS_FIGURES_DIR
from app.database.db import VGuardDatabase
from app.reporting.thesis_figures import ThesisFigureGenerator


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate V-Guard thesis figures")
    parser.add_argument(
        "--video-id",
        type=int,
        default=None,
        help="Focus detailed charts on one video id",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=THESIS_FIGURES_DIR,
        help="Output directory for PNG/CSV files",
    )
    args = parser.parse_args()

    db = VGuardDatabase()
    generator = ThesisFigureGenerator(db, args.output)
    paths = generator.generate_all(video_id=args.video_id)

    print(f"Generated {len(paths)} file(s) in {args.output.resolve()}:")
    for path in paths:
        print(f"  - {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
