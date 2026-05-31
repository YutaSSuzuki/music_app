#!/usr/bin/env python3
"""Register audio files copied to the hosted audio directory."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import oracledb


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default="/tmp/hosted_audio_manifest.tsv",
        help="TSV: track_source_id, track_id, original_path, file_size_bytes",
    )
    parser.add_argument(
        "--audio-root",
        default=os.environ.get("HOSTED_AUDIO_ROOT", "/data/music-app/audio"),
    )
    return parser.parse_args()


def connect() -> oracledb.Connection:
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ["ORACLE_DSN"],
    )


def main() -> int:
    args = parse_args()
    manifest = Path(args.manifest)
    audio_root = Path(args.audio_root)
    processed = 0
    missing = 0

    with connect() as conn, conn.cursor() as cur:
        for line in manifest.read_text(encoding="utf-8").splitlines():
            source_id, track_id, original_path, size = line.split("\t")
            hosted_path = audio_root / f"{source_id}{Path(original_path).suffix}"
            if not hosted_path.is_file():
                print(f"SKIP missing: {hosted_path}")
                missing += 1
                continue

            cur.execute(
                """
                MERGE INTO hosted_audio_files target
                USING (
                    SELECT :source_id AS track_source_id,
                           :track_id AS track_id,
                           :hosted_path AS file_path_linux,
                           :size_bytes AS file_size_bytes
                    FROM dual
                ) source
                ON (target.track_source_id = source.track_source_id)
                WHEN MATCHED THEN UPDATE SET
                    target.track_id = source.track_id,
                    target.file_path_linux = source.file_path_linux,
                    target.file_size_bytes = source.file_size_bytes,
                    target.is_available = 1,
                    target.updated_at = CURRENT_TIMESTAMP
                WHEN NOT MATCHED THEN INSERT (
                    track_source_id, track_id, file_path_linux, file_size_bytes
                ) VALUES (
                    source.track_source_id, source.track_id,
                    source.file_path_linux, source.file_size_bytes
                )
                """,
                {
                    "source_id": int(source_id),
                    "track_id": int(track_id),
                    "hosted_path": str(hosted_path),
                    "size_bytes": int(size),
                },
            )
            processed += 1

        conn.commit()
        cur.execute(
            "SELECT COUNT(*) FROM hosted_audio_files WHERE is_available = 1"
        )
        available = cur.fetchone()[0]

    print(f"processed={processed} missing={missing} available={available}")
    return 0 if missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
