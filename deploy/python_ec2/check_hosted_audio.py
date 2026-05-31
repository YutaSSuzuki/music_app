#!/usr/bin/env python3
"""Check hosted audio DB rows against files on the API server."""

from __future__ import annotations

import os
from pathlib import Path

import oracledb


def connect() -> oracledb.Connection:
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ["ORACLE_DSN"],
    )


def main() -> int:
    missing = []
    total_bytes = 0
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT track_source_id, file_path_linux, file_size_bytes
            FROM hosted_audio_files
            WHERE is_available = 1
            ORDER BY track_source_id
            """
        )
        rows = list(cur)

    for source_id, file_path_linux, expected_size in rows:
        path = Path(file_path_linux)
        if not path.is_file():
            missing.append((source_id, path))
            continue
        actual_size = path.stat().st_size
        total_bytes += actual_size
        if expected_size is not None and actual_size != expected_size:
            print(
                f"SIZE MISMATCH: source={source_id} "
                f"expected={expected_size} actual={actual_size} path={path}"
            )

    for source_id, path in missing:
        print(f"MISSING: source={source_id} path={path}")
    print(
        f"registered={len(rows)} existing={len(rows) - len(missing)} "
        f"missing={len(missing)} GiB={total_bytes / 1024 / 1024 / 1024:.2f}"
    )
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
