"""Generate thesis-ready PNG charts from scan metrics in SQLite."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from app.config import THESIS_FIGURES_DIR, VISUAL_CONFIDENCE_THRESHOLD
from app.database.db import VGuardDatabase

# Consistent thesis styling
plt.style.use("seaborn-v0_8-whitegrid")
PRIMARY = "#7C3AED"
DANGER = "#EF4444"
SAFE = "#10B981"


class ThesisFigureGenerator:
    """Build evaluation figures and CSV summaries for dissertation use."""

    def __init__(
        self,
        database: VGuardDatabase | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self._db = database or VGuardDatabase()
        self.output_dir = Path(output_dir or THESIS_FIGURES_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self, video_id: int | None = None) -> list[Path]:
        """Generate all available figures; returns paths created."""
        paths: list[Path] = []
        summary = self._db.get_scan_summary()
        if not summary:
            paths.append(self._write_empty_state_figure())
            return paths

        df_summary = pd.DataFrame(summary)
        df_summary.to_csv(self.output_dir / "scan_summary.csv", index=False)

        paths.append(self._plot_scan_status_overview(df_summary))
        paths.append(self._plot_detection_counts(df_summary))

        if video_id is not None:
            paths.extend(self._generate_video_figures(video_id))
        else:
            for row in summary:
                if row.get("frames_analyzed", 0) > 0:
                    paths.extend(self._generate_video_figures(int(row["video_id"])))
                    break

        paths.append(self._plot_performance_summary(df_summary, video_id))
        paths.append(self._plot_error_overview(df_summary))
        return [p for p in paths if p.exists()]

    def _generate_video_figures(self, video_id: int) -> list[Path]:
        paths: list[Path] = []
        frames = self._db.get_frame_predictions(video_id)
        detections = self._db.get_detections(video_id, detection_type="visual")
        video = self._db.get_video_by_id(video_id)

        if not frames:
            return paths

        df = pd.DataFrame(frames)
        name = video.file_name if video else f"video_{video_id}"
        safe_name = "".join(c if c.isalnum() else "_" for c in name)

        paths.append(self._plot_confidence_histogram(df, video_id, safe_name))
        paths.append(self._plot_confidence_timeline(df, video_id, safe_name))
        paths.append(self._plot_threshold_analysis(df, video_id, safe_name))

        if detections and video and video.duration:
            paths.append(
                self._plot_flagged_timeline(
                    detections,
                    video.duration,
                    video_id,
                    safe_name,
                )
            )

        df.to_csv(self.output_dir / f"frame_predictions_{safe_name}.csv", index=False)
        return paths

    def _plot_confidence_histogram(
        self, df: pd.DataFrame, video_id: int, safe_name: str
    ) -> Path:
        fig, ax = plt.subplots(figsize=(8, 5))
        threshold = (
            df["threshold_used"].iloc[0]
            if "threshold_used" in df.columns
            else VISUAL_CONFIDENCE_THRESHOLD
        )
        ax.hist(df["nsfw_confidence"], bins=20, color=PRIMARY, edgecolor="white", alpha=0.85)
        ax.axvline(threshold, color=DANGER, linestyle="--", linewidth=2, label=f"Threshold ({threshold:.2f})")
        ax.set_xlabel("NSFW probability")
        ax.set_ylabel("Frame count")
        ax.set_title(f"Visual model confidence distribution — {safe_name}")
        ax.legend()
        fig.tight_layout()
        path = self.output_dir / f"01_confidence_histogram_{safe_name}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _plot_confidence_timeline(
        self, df: pd.DataFrame, video_id: int, safe_name: str
    ) -> Path:
        fig, ax = plt.subplots(figsize=(10, 5))
        threshold = float(df["threshold_used"].iloc[0]) if len(df) else VISUAL_CONFIDENCE_THRESHOLD
        colors = np.where(df["is_flagged"], DANGER, SAFE)
        ax.scatter(df["timestamp_sec"], df["nsfw_confidence"], c=colors, alpha=0.75, s=40)
        ax.axhline(threshold, color=DANGER, linestyle="--", linewidth=1.5, label="Threshold")
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("NSFW probability")
        ax.set_title(f"Per-frame model scores over time — {safe_name}")
        ax.legend(["Flagged", "Safe", "Threshold"])
        fig.tight_layout()
        path = self.output_dir / f"02_confidence_timeline_{safe_name}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _plot_flagged_timeline(
        self, detections, duration: float, video_id: int, safe_name: str
    ) -> Path:
        fig, ax = plt.subplots(figsize=(10, 2.8))
        for det in detections:
            ax.barh(
                0,
                det.end_time - det.start_time,
                left=det.start_time,
                height=0.5,
                color=DANGER,
                alpha=0.7,
                edgecolor="white",
            )
        ax.set_xlim(0, max(duration, 1))
        ax.set_yticks([])
        ax.set_xlabel("Time (seconds)")
        ax.set_title(f"Flagged visual segments on video timeline — {safe_name}")
        fig.tight_layout()
        path = self.output_dir / f"03_flagged_timeline_{safe_name}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _plot_threshold_analysis(
        self, df: pd.DataFrame, video_id: int, safe_name: str
    ) -> Path:
        thresholds = np.arange(0.1, 0.96, 0.05)
        flagged_counts = [(df["nsfw_confidence"] >= t).sum() for t in thresholds]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(thresholds, flagged_counts, marker="o", color=PRIMARY, linewidth=2)
        current = float(df["threshold_used"].iloc[0]) if len(df) else VISUAL_CONFIDENCE_THRESHOLD
        ax.axvline(current, color=DANGER, linestyle="--", label=f"Current ({current:.2f})")
        ax.set_xlabel("Confidence threshold")
        ax.set_ylabel("Frames flagged")
        ax.set_title(f"Threshold sensitivity analysis — {safe_name}")
        ax.legend()
        fig.tight_layout()
        path = self.output_dir / f"04_threshold_sensitivity_{safe_name}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _plot_scan_status_overview(self, df: pd.DataFrame) -> Path:
        counts = df["scan_status"].value_counts()
        fig, ax = plt.subplots(figsize=(7, 5))
        counts.plot(kind="bar", ax=ax, color=PRIMARY, edgecolor="white")
        ax.set_xlabel("Scan status")
        ax.set_ylabel("Videos")
        ax.set_title("V-Guard library — scan status overview")
        plt.xticks(rotation=20, ha="right")
        fig.tight_layout()
        path = self.output_dir / "05_scan_status_overview.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _plot_detection_counts(self, df: pd.DataFrame) -> Path:
        fig, ax = plt.subplots(figsize=(8, 5))
        x = np.arange(len(df))
        width = 0.35
        ax.bar(x - width / 2, df["visual_segments"].fillna(0), width, label="Visual", color=DANGER)
        ax.bar(x + width / 2, df["audio_segments"].fillna(0), width, label="Audio", color="#F59E0B")
        ax.set_xticks(x)
        ax.set_xticklabels(df["file_name"], rotation=25, ha="right")
        ax.set_ylabel("Segments flagged")
        ax.set_title("Detection counts per video")
        ax.legend()
        fig.tight_layout()
        path = self.output_dir / "06_detection_counts_by_video.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _plot_performance_summary(
        self, df: pd.DataFrame, video_id: int | None
    ) -> Path:
        total_videos = len(df)
        scanned = (df["scan_status"] == "complete").sum()
        failed = (df["scan_status"] == "failed").sum()
        total_frames = int(df["frames_analyzed"].fillna(0).sum())
        total_flagged = int(df["frames_flagged"].fillna(0).sum())
        flag_rate = (total_flagged / total_frames * 100) if total_frames else 0.0

        lines = [
            "V-Guard Visual Model — Evaluation Summary",
            "",
            f"Videos in library: {total_videos}",
            f"Successfully scanned: {scanned}",
            f"Failed scans: {failed}",
            f"Frames analyzed: {total_frames}",
            f"Frames flagged: {total_flagged}",
            f"Flag rate: {flag_rate:.1f}%",
            f"Default threshold: {VISUAL_CONFIDENCE_THRESHOLD}",
            "",
            "Note: Metrics are from pre-scan frame sampling (Open-NSFW ONNX).",
            "Re-run after audio pipeline (Stage 7–8) for combined charts.",
        ]
        if video_id is not None:
            row = df[df["video_id"] == video_id]
            if not row.empty:
                r = row.iloc[0]
                lines.extend([
                    "",
                    f"Selected video: {r['file_name']}",
                    f"  Frames: {int(r['frames_analyzed'] or 0)}",
                    f"  Visual segments: {int(r['visual_segments'] or 0)}",
                ])

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.axis("off")
        ax.text(
            0.02, 0.98, "\n".join(lines),
            va="top", ha="left", fontsize=11,
            family="monospace",
            bbox=dict(boxstyle="round", facecolor="#EDE9FE", edgecolor=PRIMARY),
        )
        fig.tight_layout()
        path = self.output_dir / "07_model_performance_summary.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _plot_error_overview(self, df: pd.DataFrame) -> Path:
        failed = df[df["scan_status"] == "failed"]
        fig, ax = plt.subplots(figsize=(7, 4))
        if failed.empty:
            ax.text(0.5, 0.5, "No failed scans recorded", ha="center", va="center", fontsize=12)
            ax.set_title("Scan errors")
        else:
            ax.barh(failed["file_name"], [1] * len(failed), color=DANGER)
            ax.set_xlabel("Error count")
            ax.set_title("Videos with failed scans")
        fig.tight_layout()
        path = self.output_dir / "08_scan_errors.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def _write_empty_state_figure(self) -> Path:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(
            0.5, 0.5,
            "No scan data yet.\nOpen a video and run Scan Video first.",
            ha="center", va="center", fontsize=13,
        )
        ax.axis("off")
        path = self.output_dir / "00_no_data_yet.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path
