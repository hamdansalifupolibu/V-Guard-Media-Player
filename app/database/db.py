"""SQLite database access layer."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from app.config import DB_PATH, PROJECT_ROOT
from app.database.models import DetectionRecord, DownloadRecord, VideoRecord


def _schema_path() -> Path:
    bundled = PROJECT_ROOT / "app" / "database" / "schema.sql"
    if bundled.is_file():
        return bundled
    return Path(__file__).parent / "schema.sql"


class VGuardDatabase:
    """Local SQLite storage for videos, detections, settings, and downloads."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path or DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        sql = _schema_path().read_text(encoding="utf-8")
        with self._connect() as conn:
            conn.executescript(sql)
            self._migrate_schema(conn)
            conn.commit()

    def _migrate_schema(self, conn: sqlite3.Connection) -> None:
        """Apply additive migrations for existing databases."""
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(videos)").fetchall()
        }
        if "scan_progress_sec" not in columns:
            conn.execute(
                "ALTER TABLE videos ADD COLUMN scan_progress_sec REAL NOT NULL DEFAULT 0"
            )

    @staticmethod
    def _normalize_path(file_path: str | Path) -> str:
        return str(Path(file_path).resolve())

    def upsert_video(
        self,
        file_path: str | Path,
        *,
        duration: float | None = None,
        scan_status: str | None = None,
    ) -> int:
        """Insert or update a video record; returns video id."""
        path = self._normalize_path(file_path)
        name = Path(path).name
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM videos WHERE file_path = ?",
                (path,),
            ).fetchone()
            if existing:
                video_id = int(existing["id"])
                if duration is not None or scan_status is not None:
                    conn.execute(
                        """
                        UPDATE videos
                        SET duration = COALESCE(?, duration),
                            scan_status = COALESCE(?, scan_status),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (duration, scan_status, video_id),
                    )
                else:
                    conn.execute(
                        "UPDATE videos SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (video_id,),
                    )
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO videos (file_path, file_name, duration, scan_status)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        path,
                        name,
                        duration,
                        scan_status or "not_scanned",
                    ),
                )
                video_id = int(cursor.lastrowid)
            conn.commit()
            return video_id

    def get_video_by_path(self, file_path: str | Path) -> VideoRecord | None:
        path = self._normalize_path(file_path)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM videos WHERE file_path = ?",
                (path,),
            ).fetchone()
        return self._row_to_video(row) if row else None

    def get_video_by_id(self, video_id: int) -> VideoRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM videos WHERE id = ?",
                (video_id,),
            ).fetchone()
        return self._row_to_video(row) if row else None

    def update_scan_status(self, video_id: int, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE videos
                SET scan_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, video_id),
            )
            conn.commit()

    def update_scan_progress(self, video_id: int, progress_sec: float) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE videos
                SET scan_progress_sec = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (max(0.0, progress_sec), video_id),
            )
            conn.commit()

    def reset_scan_progress(self, video_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE videos
                SET scan_progress_sec = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (video_id,),
            )
            conn.commit()

    def update_duration(self, video_id: int, duration: float) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE videos
                SET duration = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (duration, video_id),
            )
            conn.commit()

    def list_videos(self) -> list[VideoRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM videos ORDER BY updated_at DESC"
            ).fetchall()
        return [self._row_to_video(r) for r in rows]

    def add_detection(
        self,
        video_id: int,
        detection_type: str,
        start_time: float,
        end_time: float,
        *,
        confidence: float | None = None,
        label: str | None = None,
        enabled: bool = True,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO detections (
                    video_id, detection_type, start_time, end_time,
                    confidence, label, enabled
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video_id,
                    detection_type,
                    start_time,
                    end_time,
                    confidence,
                    label,
                    1 if enabled else 0,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def add_detections_batch(
        self,
        video_id: int,
        items: Iterable[dict],
    ) -> int:
        """Insert multiple detections; returns count inserted."""
        rows = [
            (
                video_id,
                item["detection_type"],
                item["start_time"],
                item["end_time"],
                item.get("confidence"),
                item.get("label"),
                1 if item.get("enabled", True) else 0,
            )
            for item in items
        ]
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO detections (
                    video_id, detection_type, start_time, end_time,
                    confidence, label, enabled
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        return len(rows)

    def get_detections(
        self,
        video_id: int,
        *,
        detection_type: str | None = None,
        enabled_only: bool = False,
    ) -> list[DetectionRecord]:
        query = "SELECT * FROM detections WHERE video_id = ?"
        params: list = [video_id]
        if detection_type:
            query += " AND detection_type = ?"
            params.append(detection_type)
        if enabled_only:
            query += " AND enabled = 1"
        query += " ORDER BY start_time ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_detection(r) for r in rows]

    def clear_detections(
        self,
        video_id: int,
        detection_type: str | None = None,
    ) -> int:
        with self._connect() as conn:
            if detection_type:
                cursor = conn.execute(
                    "DELETE FROM detections WHERE video_id = ? AND detection_type = ?",
                    (video_id, detection_type),
                )
            else:
                cursor = conn.execute(
                    "DELETE FROM detections WHERE video_id = ?",
                    (video_id,),
                )
            conn.commit()
            return cursor.rowcount

    def clear_frame_predictions(self, video_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM frame_predictions WHERE video_id = ?",
                (video_id,),
            )
            conn.commit()

    def append_frame_predictions(
        self,
        video_id: int,
        predictions: Iterable[dict],
        *,
        threshold: float,
    ) -> int:
        """Append per-frame scores (progressive scan chunks)."""
        rows = [
            (
                video_id,
                item["timestamp_sec"],
                item["nsfw_confidence"],
                1 if item["is_flagged"] else 0,
                threshold,
            )
            for item in predictions
        ]
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO frame_predictions (
                    video_id, timestamp_sec, nsfw_confidence, is_flagged, threshold_used
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        return len(rows)

    def save_frame_predictions(
        self,
        video_id: int,
        predictions: Iterable[dict],
        *,
        threshold: float,
    ) -> int:
        """Replace all per-frame NSFW scores. Each dict: timestamp_sec, nsfw_confidence, is_flagged."""
        self.clear_frame_predictions(video_id)
        rows = [
            (
                video_id,
                item["timestamp_sec"],
                item["nsfw_confidence"],
                1 if item["is_flagged"] else 0,
                threshold,
            )
            for item in predictions
        ]
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO frame_predictions (
                    video_id, timestamp_sec, nsfw_confidence, is_flagged, threshold_used
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        return len(rows)

    def get_frame_predictions(self, video_id: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT timestamp_sec, nsfw_confidence, is_flagged, threshold_used
                FROM frame_predictions
                WHERE video_id = ?
                ORDER BY timestamp_sec ASC
                """,
                (video_id,),
            ).fetchall()
        return [
            {
                "timestamp_sec": float(r["timestamp_sec"]),
                "nsfw_confidence": float(r["nsfw_confidence"]),
                "is_flagged": bool(r["is_flagged"]),
                "threshold_used": float(r["threshold_used"]),
            }
            for r in rows
        ]

    def get_scan_summary(self) -> list[dict]:
        """Aggregate stats per video for thesis reporting."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    v.id AS video_id,
                    v.file_name,
                    v.duration,
                    v.scan_status,
                    COUNT(DISTINCT fp.id) AS frames_analyzed,
                    SUM(CASE WHEN fp.is_flagged = 1 THEN 1 ELSE 0 END) AS frames_flagged,
                    AVG(fp.nsfw_confidence) AS avg_confidence,
                    MAX(fp.nsfw_confidence) AS max_confidence,
                    (SELECT COUNT(*) FROM detections d
                     WHERE d.video_id = v.id AND d.detection_type = 'visual') AS visual_segments,
                    (SELECT COUNT(*) FROM detections d
                     WHERE d.video_id = v.id AND d.detection_type = 'audio') AS audio_segments
                FROM videos v
                LEFT JOIN frame_predictions fp ON fp.video_id = v.id
                GROUP BY v.id
                ORDER BY v.updated_at DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def set_detection_enabled(self, detection_id: int, enabled: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE detections SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, detection_id),
            )
            conn.commit()

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
            conn.commit()

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ).fetchone()
        return row["value"] if row else default

    def add_download(self, url: str, *, status: str = "pending") -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO downloads (url, status) VALUES (?, ?)",
                (url, status),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def update_download(
        self,
        download_id: int,
        *,
        file_path: str | None = None,
        status: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE downloads
                SET file_path = COALESCE(?, file_path),
                    status = COALESCE(?, status)
                WHERE id = ?
                """,
                (file_path, status, download_id),
            )
            conn.commit()

    def list_downloads(self) -> list[DownloadRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM downloads ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_download(r) for r in rows]

    @staticmethod
    def _row_to_video(row: sqlite3.Row) -> VideoRecord:
        keys = row.keys()
        progress = float(row["scan_progress_sec"]) if "scan_progress_sec" in keys else 0.0
        return VideoRecord(
            id=int(row["id"]),
            file_path=row["file_path"],
            file_name=row["file_name"],
            duration=row["duration"],
            scan_status=row["scan_status"],
            scan_progress_sec=progress,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_detection(row: sqlite3.Row) -> DetectionRecord:
        return DetectionRecord(
            id=int(row["id"]),
            video_id=int(row["video_id"]),
            detection_type=row["detection_type"],
            start_time=float(row["start_time"]),
            end_time=float(row["end_time"]),
            confidence=row["confidence"],
            label=row["label"],
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_download(row: sqlite3.Row) -> DownloadRecord:
        return DownloadRecord(
            id=int(row["id"]),
            url=row["url"],
            file_path=row["file_path"],
            status=row["status"],
            created_at=row["created_at"],
        )
