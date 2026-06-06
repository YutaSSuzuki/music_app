#!/usr/bin/env python3
"""Register new local tracks from a TSV and copy files into hosted audio storage."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default="/tmp/new_tracks.tsv",
        help="UTF-8 TSV: title, artist, source_path, optional duration_sec",
    )
    parser.add_argument(
        "--audio-root",
        default=os.environ.get("HOSTED_AUDIO_ROOT", "/data/music-app/audio"),
    )
    parser.add_argument(
        "--has-header",
        action="store_true",
        help="Skip the first TSV row.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate input and print actions without changing DB or files.",
    )
    return parser.parse_args()


def normalize(value: str) -> str:
    return value.strip().lower()


def get_oracledb():
    import oracledb

    return oracledb


def connect() -> oracledb.Connection:
    oracledb = get_oracledb()
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ["ORACLE_DSN"],
    )


def read_manifest(path: Path, has_header: bool) -> list[tuple[str, str, Path, int | None]]:
    rows = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        if has_header:
            next(reader, None)
        for line_no, row in enumerate(reader, start=2 if has_header else 1):
            if not row or all(not value.strip() for value in row):
                continue
            if len(row) not in (3, 4):
                raise ValueError(
                    f"line {line_no}: expected 3 or 4 columns, got {len(row)}"
                )
            title = row[0].strip()
            artist = row[1].strip()
            source_path = Path(row[2].strip())
            duration_sec = int(row[3]) if len(row) == 4 and row[3].strip() else None
            if not title:
                raise ValueError(f"line {line_no}: title is empty")
            if not artist:
                raise ValueError(f"line {line_no}: artist is empty")
            if not source_path.is_file():
                raise FileNotFoundError(f"line {line_no}: missing file: {source_path}")
            rows.append((title, artist, source_path, duration_sec))
    return rows


def find_existing_source(
    cur: oracledb.Cursor, normalized_title: str, normalized_artist: str
) -> int | None:
    cur.execute(
        """
        SELECT MIN(track_source_id)
        FROM track_sources
        WHERE source_name = 'local'
          AND normalized_title = :normalized_title
          AND normalized_artist = :normalized_artist
        """,
        normalized_title=normalized_title,
        normalized_artist=normalized_artist,
    )
    value = cur.fetchone()[0]
    return int(value) if value is not None else None


def register_one(
    conn: oracledb.Connection,
    audio_root: Path,
    title: str,
    artist: str,
    source_path: Path,
    duration_sec: int | None,
    dry_run: bool,
) -> tuple[str, int | None]:
    oracledb = get_oracledb()
    normalized_title = normalize(title)
    normalized_artist = normalize(artist)
    size_bytes = source_path.stat().st_size

    with conn.cursor() as cur:
        existing_source_id = find_existing_source(
            cur, normalized_title, normalized_artist
        )
        if existing_source_id is not None:
            return ("skipped_existing", existing_source_id)

        if dry_run:
            print(
                "DRY RUN add: "
                f"title={title!r} artist={artist!r} path={source_path} "
                f"bytes={size_bytes}"
            )
            return ("dry_run", None)

        track_id_var = cur.var(oracledb.NUMBER)
        source_id_var = cur.var(oracledb.NUMBER)

        cur.execute(
            """
            INSERT INTO tracks (title, normalized_title, duration_sec)
            VALUES (:title, :normalized_title, :duration_sec)
            RETURNING track_id INTO :track_id
            """,
            title=title,
            normalized_title=normalized_title,
            duration_sec=duration_sec,
            track_id=track_id_var,
        )
        track_id = int(track_id_var.getvalue()[0])

        cur.execute(
            """
            MERGE INTO artists target
            USING (
                SELECT :name AS name, :normalized_name AS normalized_name
                FROM dual
            ) source
            ON (target.normalized_name = source.normalized_name)
            WHEN NOT MATCHED THEN INSERT (name, normalized_name)
            VALUES (source.name, source.normalized_name)
            """,
            name=artist,
            normalized_name=normalized_artist,
        )

        cur.execute(
            """
            SELECT artist_id
            FROM artists
            WHERE normalized_name = :normalized_name
            """,
            normalized_name=normalized_artist,
        )
        artist_id = int(cur.fetchone()[0])

        cur.execute(
            """
            INSERT INTO track_artists (track_id, artist_id)
            VALUES (:track_id, :artist_id)
            """,
            track_id=track_id,
            artist_id=artist_id,
        )

        cur.execute(
            """
            INSERT INTO track_sources (
                track_id,
                source_name,
                raw_title,
                raw_artist,
                normalized_title,
                normalized_artist,
                availability_status
            ) VALUES (
                :track_id,
                'local',
                :raw_title,
                :raw_artist,
                :normalized_title,
                :normalized_artist,
                'available'
            )
            RETURNING track_source_id INTO :track_source_id
            """,
            track_id=track_id,
            raw_title=title,
            raw_artist=artist,
            normalized_title=normalized_title,
            normalized_artist=normalized_artist,
            track_source_id=source_id_var,
        )
        track_source_id = int(source_id_var.getvalue()[0])
        hosted_path = audio_root / f"{track_source_id}{source_path.suffix.lower()}"
        if hosted_path.exists():
            raise FileExistsError(f"target already exists: {hosted_path}")

        shutil.copy2(source_path, hosted_path)

        cur.execute(
            """
            INSERT INTO hosted_audio_files (
                track_source_id,
                track_id,
                file_path_linux,
                file_size_bytes,
                is_available
            ) VALUES (
                :track_source_id,
                :track_id,
                :file_path_linux,
                :file_size_bytes,
                1
            )
            """,
            track_source_id=track_source_id,
            track_id=track_id,
            file_path_linux=str(hosted_path),
            file_size_bytes=size_bytes,
        )

    conn.commit()
    print(
        f"added track_id={track_id} track_source_id={track_source_id} "
        f"path={hosted_path}"
    )
    return ("added", track_source_id)


def main() -> int:
    args = parse_args()
    manifest = Path(args.manifest)
    audio_root = Path(args.audio_root)
    rows = read_manifest(manifest, args.has_header)
    added = 0
    skipped = 0

    if not audio_root.is_dir():
        raise FileNotFoundError(f"audio root does not exist: {audio_root}")

    with connect() as conn:
        for title, artist, source_path, duration_sec in rows:
            status, source_id = register_one(
                conn,
                audio_root,
                title,
                artist,
                source_path,
                duration_sec,
                args.dry_run,
            )
            if status in {"added", "dry_run"}:
                added += 1
            elif status == "skipped_existing":
                skipped += 1
                print(
                    f"SKIP existing track_source_id={source_id} "
                    f"title={title!r} artist={artist!r}"
                )

    print(f"processed={len(rows)} added={added} skipped_existing={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
