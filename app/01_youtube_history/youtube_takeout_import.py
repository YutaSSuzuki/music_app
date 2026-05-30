#!/usr/bin/env python3
"""Import YouTube Music Takeout watch history into play_events."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import oracledb


DEFAULT_USER = "music_app_v2"
DEFAULT_PASSWORD = "CHANGE_ME"
DEFAULT_DSN = "localhost:1521/FREEPDB1"


def env_or_default(name: str, default: str) -> str:
    return os.environ.get(name, default)


def connect() -> oracledb.Connection:
    return oracledb.connect(
        user=env_or_default("ORACLE_USER", DEFAULT_USER),
        password=env_or_default("ORACLE_PASSWORD", DEFAULT_PASSWORD),
        dsn=env_or_default("ORACLE_DSN", DEFAULT_DSN),
    )


def normalize(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"\s+", " ", value.strip()).lower()
    return normalized or None


def clean_title(title: str) -> str:
    title = re.sub(r"\s*を視聴しました\s*$", "", title.strip())
    return title.strip()


def clean_artist(name: str | None) -> str | None:
    if not name:
        return None
    artist = re.sub(r"\s*-\s*Topic\s*$", "", name.strip(), flags=re.IGNORECASE)
    artist = re.sub(
        r"\s*(Official YouTube Channel|Official YouTube|official YouTube channel)\s*$",
        "",
        artist,
        flags=re.IGNORECASE,
    )
    return artist.strip() or None


def parse_played_at(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def is_youtube_music_item(item: dict[str, Any]) -> bool:
    title_url = str(item.get("titleUrl") or "")
    return item.get("header") == "YouTube Music" or title_url.startswith(
        "https://music.youtube.com/"
    )


def parse_takeout_items(content: str) -> list[dict[str, Any]]:
    raw_items = json.loads(content)
    if not isinstance(raw_items, list):
        raise ValueError("watch-history.json must contain a JSON array")

    rows = []
    for item in raw_items:
        if not isinstance(item, dict) or not is_youtube_music_item(item):
            continue
        title = clean_title(str(item.get("title") or ""))
        if not title or not item.get("time"):
            continue

        subtitles = item.get("subtitles") or []
        raw_artist = None
        if subtitles and isinstance(subtitles[0], dict):
            raw_artist = clean_artist(subtitles[0].get("name"))

        rows.append(
            {
                "raw_title": title,
                "raw_artist": raw_artist,
                "normalized_title": normalize(title),
                "normalized_artist": normalize(raw_artist),
                "played_at": parse_played_at(str(item["time"])),
                "source_url": item.get("titleUrl"),
                "source_payload": json.dumps(item, ensure_ascii=False),
            }
        )
    return rows


def find_local_match(
    cur: oracledb.Cursor,
    normalized_title: str | None,
    normalized_artist: str | None,
) -> tuple[int | None, int | None]:
    if not normalized_title or not normalized_artist:
        return None, None
    cur.execute(
        """
        SELECT ts.track_id, ts.track_source_id
        FROM track_sources ts
        WHERE ts.source_name = 'local'
          AND ts.availability_status = 'available'
          AND ts.normalized_title = :normalized_title
          AND ts.normalized_artist = :normalized_artist
        FETCH FIRST 1 ROWS ONLY
        """,
        {
            "normalized_title": normalized_title,
            "normalized_artist": normalized_artist,
        },
    )
    row = cur.fetchone()
    if row:
        return int(row[0]), int(row[1])

    cur.execute(
        """
        SELECT t.track_id, ts.track_source_id
        FROM tracks t
        JOIN track_sources ts
          ON ts.track_id = t.track_id
         AND ts.source_name = 'local'
         AND ts.availability_status = 'available'
        JOIN track_artists ta
          ON ta.track_id = t.track_id
         AND ta.artist_role = 'primary'
         AND ta.artist_order = 1
        JOIN artists a
          ON a.artist_id = ta.artist_id
        WHERE t.normalized_title = :normalized_title
          AND a.normalized_name = :normalized_artist
        FETCH FIRST 1 ROWS ONLY
        """,
        {
            "normalized_title": normalized_title,
            "normalized_artist": normalized_artist,
        },
    )
    row = cur.fetchone()
    if row:
        return int(row[0]), int(row[1])
    return None, None


def event_exists(
    cur: oracledb.Cursor,
    source_url: str | None,
    played_at: datetime,
    normalized_title: str | None,
) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM play_events
        WHERE source_name = 'youtube_music'
          AND played_at = :played_at
          AND (
              source_url = :source_url
              OR (
                  :source_url IS NULL
                  AND source_url IS NULL
                  AND normalized_title = :normalized_title
              )
          )
        FETCH FIRST 1 ROWS ONLY
        """,
        {
            "source_url": source_url,
            "played_at": played_at,
            "normalized_title": normalized_title,
        },
    )
    return cur.fetchone() is not None


def import_takeout_content(content: str, dry_run: bool = False) -> dict[str, Any]:
    rows = parse_takeout_items(content)
    summary = {
        "youtube_music_items": len(rows),
        "inserted": 0,
        "skipped_duplicates": 0,
        "matched": 0,
        "unmatched": 0,
        "preview_rows": [],
    }

    with connect() as conn:
        with conn.cursor() as cur:
            for index, row in enumerate(rows, start=1):
                duplicate = event_exists(
                    cur,
                    row["source_url"],
                    row["played_at"],
                    row["normalized_title"],
                )
                preview_row = {
                    "row_no": index,
                    "action": "skip_duplicate" if duplicate else "insert",
                    "raw_title": row["raw_title"],
                    "raw_artist": row["raw_artist"],
                    "played_at": row["played_at"].isoformat(),
                    "source_url": row["source_url"],
                    "match_status": None,
                    "track_id": None,
                    "track_source_id": None,
                }
                if duplicate:
                    summary["skipped_duplicates"] += 1
                    summary["preview_rows"].append(preview_row)
                    continue

                track_id, track_source_id = find_local_match(
                    cur,
                    row["normalized_title"],
                    row["normalized_artist"],
                )
                match_status = "matched" if track_id else "unmatched"
                preview_row["match_status"] = match_status
                preview_row["track_id"] = track_id
                preview_row["track_source_id"] = track_source_id
                summary["preview_rows"].append(preview_row)
                cur.execute(
                    """
                    INSERT INTO play_events (
                        source_name,
                        track_id,
                        track_source_id,
                        raw_title,
                        raw_artist,
                        normalized_title,
                        normalized_artist,
                        played_at,
                        skipped_flag,
                        match_status,
                        source_url,
                        source_payload
                    ) VALUES (
                        'youtube_music',
                        :track_id,
                        :track_source_id,
                        :raw_title,
                        :raw_artist,
                        :normalized_title,
                        :normalized_artist,
                        :played_at,
                        0,
                        :match_status,
                        :source_url,
                        :source_payload
                    )
                    """,
                    {
                        **row,
                        "track_id": track_id,
                        "track_source_id": track_source_id,
                        "match_status": match_status,
                    },
                )
                summary["inserted"] += 1
                summary[match_status] += 1

        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    summary["dry_run"] = dry_run
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    content = Path(args.input).read_text(encoding="utf-8")
    print(json.dumps(import_takeout_content(content, args.dry_run), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
