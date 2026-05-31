#!/usr/bin/env python3
"""Add local file sizes to a DB-exported hosted audio manifest."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="/tmp/hosted_audio_manifest_db.tsv",
        help="TSV: track_source_id, track_id, original_path",
    )
    parser.add_argument(
        "--output",
        default="/tmp/hosted_audio_manifest.tsv",
        help="TSV: track_source_id, track_id, original_path, file_size_bytes",
    )
    parser.add_argument(
        "--missing-log",
        default="/tmp/hosted_audio_missing.log",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.input)
    output = Path(args.output)
    missing_log = Path(args.missing_log)
    existing_rows = []
    missing_rows = []
    total_bytes = 0

    for line in source.read_text(encoding="utf-8").splitlines():
        source_id, track_id, original_path = line.split("\t")
        path = Path(original_path)
        if not path.is_file():
            missing_rows.append(f"missing: {path}")
            continue
        size = path.stat().st_size
        total_bytes += size
        existing_rows.append(f"{source_id}\t{track_id}\t{path}\t{size}")

    output.write_text("\n".join(existing_rows) + "\n", encoding="utf-8")
    missing_log.write_text("\n".join(missing_rows) + ("\n" if missing_rows else ""), encoding="utf-8")
    print(
        f"existing={len(existing_rows)} missing={len(missing_rows)} "
        f"bytes={total_bytes} GiB={total_bytes / 1024 / 1024 / 1024:.2f}"
    )
    return 0 if not missing_rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
