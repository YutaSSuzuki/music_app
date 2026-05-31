#!/usr/bin/env python3
"""Phase 1 CLI for Oracle-backed LLM music recommendations."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import oracledb


DEFAULT_USER = "music_app_v2"
DEFAULT_PASSWORD = "CHANGE_ME"
DEFAULT_DSN = "localhost:1521/FREEPDB1"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_SYSTEM_PROMPT = (
    "You are a music recommendation engine. "
    "Recommend only tracks included in library_tracks. "
    "Do not invent songs or artists. "
    "Every recommendation must include an existing track_id and reason. "
    "Do not return track_source_id, title, or artist."
)


def env_or_default(name: str, default: str) -> str:
    return os.environ.get(name, default)


def connect() -> oracledb.Connection:
    return oracledb.connect(
        user=env_or_default("ORACLE_USER", DEFAULT_USER),
        password=env_or_default("ORACLE_PASSWORD", DEFAULT_PASSWORD),
        dsn=env_or_default("ORACLE_DSN", DEFAULT_DSN),
    )


def isoformat(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def fetch_one_value(conn: oracledb.Connection, sql: str) -> Any:
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
        return row[0] if row else None


def health() -> dict[str, Any]:
    with connect() as conn:
        return {
            "database_user": fetch_one_value(conn, "SELECT USER FROM dual"),
            "tracks": fetch_one_value(conn, "SELECT COUNT(*) FROM tracks"),
            "track_sources": fetch_one_value(
                conn, "SELECT COUNT(*) FROM track_sources"
            ),
            "hosted_audio_files": fetch_one_value(
                conn, "SELECT COUNT(*) FROM hosted_audio_files"
            ),
            "youtube_music_events": fetch_one_value(
                conn,
                "SELECT COUNT(*) FROM play_events "
                "WHERE source_name = 'youtube_music'",
            ),
            "matched_youtube_music_events": fetch_one_value(
                conn,
                "SELECT COUNT(*) FROM play_events "
                "WHERE source_name = 'youtube_music' "
                "AND match_status = 'matched'",
            ),
            "recommendation_runs": fetch_one_value(
                conn, "SELECT COUNT(*) FROM recommendation_runs"
            ),
            "recommendation_items": fetch_one_value(
                conn, "SELECT COUNT(*) FROM recommendation_items"
            ),
        }


def recent_history(
    conn: oracledb.Connection,
    source_name: str,
    limit: int,
    history_days: int | None = None,
) -> list[dict[str, Any]]:
    sql = """
        SELECT
            pe.play_event_id,
            pe.source_name,
            pe.track_id,
            pe.track_source_id,
            pe.raw_title,
            pe.raw_artist,
            pe.normalized_title,
            pe.normalized_artist,
            pe.played_at,
            pe.match_status,
            pe.source_url
        FROM play_events pe
        WHERE pe.source_name = :source_name
          AND pe.match_status <> 'ignored'
          AND (
              :history_days IS NULL
              OR pe.played_at >= CAST(SYSTIMESTAMP AT TIME ZONE 'UTC' AS TIMESTAMP)
                  - NUMTODSINTERVAL(:history_days, 'DAY')
          )
        ORDER BY pe.played_at DESC, pe.play_event_id DESC
        FETCH FIRST :limit ROWS ONLY
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            {
                "source_name": source_name,
                "limit": limit,
                "history_days": history_days,
            },
        )
        return [
            {
                "play_event_id": row[0],
                "source_name": row[1],
                "track_id": row[2],
                "track_source_id": row[3],
                "title": row[4],
                "artist": row[5],
                "normalized_title": row[6],
                "normalized_artist": row[7],
                "played_at": isoformat(row[8]),
                "match_status": row[9],
                "source_url": row[10],
            }
            for row in cur
        ]


def library_tracks(
    conn: oracledb.Connection,
    target_source: str,
    input_source: str,
    limit: int,
    random_sample: bool = False,
) -> list[dict[str, Any]]:
    order_by = "DBMS_RANDOM.VALUE" if random_sample else "play_count DESC, track_id"
    sql = """
        WITH candidate_tracks AS (
        SELECT
            t.track_id,
            ts.track_source_id,
            t.title,
            LISTAGG(a.name, ', ') WITHIN GROUP (ORDER BY ta.artist_order) AS artist,
            t.normalized_title,
            LISTAGG(a.normalized_name, ', ') WITHIN GROUP (ORDER BY ta.artist_order)
                AS normalized_artist,
            ts.source_name,
            ts.source_url,
            MAX(haf.file_path_linux) AS file_path_linux,
            COUNT(pe.play_event_id) AS play_count
        FROM tracks t
        JOIN track_sources ts ON ts.track_id = t.track_id
        JOIN track_artists ta ON ta.track_id = t.track_id
        JOIN artists a ON a.artist_id = ta.artist_id
        LEFT JOIN hosted_audio_files haf
          ON haf.track_source_id = ts.track_source_id
         AND haf.is_available = 1
        LEFT JOIN play_events pe
          ON pe.track_id = t.track_id
         AND pe.source_name = :input_source
         AND pe.match_status = 'matched'
        WHERE ts.source_name = :target_source
          AND ts.availability_status = 'available'
          AND (
              :target_source <> 'local'
              OR EXISTS (
                  SELECT 1
                  FROM hosted_audio_files haf_exists
                  WHERE haf_exists.track_source_id = ts.track_source_id
                    AND haf_exists.is_available = 1
              )
          )
        GROUP BY
            t.track_id,
            ts.track_source_id,
            t.title,
            t.normalized_title,
            ts.source_name,
            ts.source_url
        ),
        deduped_tracks AS (
            SELECT
                candidate_tracks.*,
                ROW_NUMBER() OVER (
                    PARTITION BY track_id
                    ORDER BY play_count DESC, track_source_id
                ) AS source_rank
            FROM candidate_tracks
        )
        SELECT
            track_id,
            track_source_id,
            title,
            artist,
            normalized_title,
            normalized_artist,
            source_name,
            source_url,
            file_path_linux,
            play_count
        FROM deduped_tracks
        WHERE source_rank = 1
        ORDER BY """ + order_by + """
        FETCH FIRST :limit ROWS ONLY
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            {
                "target_source": target_source,
                "input_source": input_source,
                "limit": limit,
            },
        )
        return [
            {
                "track_id": row[0],
                "track_source_id": row[1],
                "title": row[2],
                "artist": row[3],
                "normalized_title": row[4],
                "normalized_artist": row[5],
                "target_source": row[6],
                "source_url": row[7],
                "file_path_linux": row[8],
                "play_count": row[9],
                "tags": [],
            }
            for row in cur
        ]


def library_track_count(conn: oracledb.Connection, target_source: str) -> int:
    sql = """
        SELECT COUNT(DISTINCT ts.track_id)
        FROM track_sources ts
        WHERE ts.source_name = :target_source
          AND ts.availability_status = 'available'
          AND (
              :target_source <> 'local'
              OR EXISTS (
                  SELECT 1
                  FROM hosted_audio_files haf_exists
                  WHERE haf_exists.track_source_id = ts.track_source_id
                    AND haf_exists.is_available = 1
              )
          )
    """
    with conn.cursor() as cur:
        cur.execute(sql, {"target_source": target_source})
        row = cur.fetchone()
        return int(row[0]) if row else 0


def build_context(
    history_limit: int,
    track_limit: int,
    input_source: str,
    target_source: str,
    history_days: int | None = None,
    random_library_sample: bool = False,
    use_history: bool = True,
) -> dict[str, Any]:
    with connect() as conn:
        recent = (
            recent_history(
                conn,
                input_source,
                history_limit,
                history_days,
            )
            if use_history
            else []
        )
        constraints = [
            "Recommend only tracks included in library_tracks.",
            "Every recommendation must include an existing track_id.",
            "Do not invent songs or artists.",
            "library_tracks is a limited candidate sample, not the whole DB.",
        ]
        if use_history:
            constraints.append("Use recent_history as listening context.")
        else:
            constraints.append("Do not use listening history for this request.")
        constraints.append("Return only track_id and reason for each recommendation.")
        constraints.append("Do not return track_source_id, title, or artist.")
        return {
            "task": "recommend_music_from_library",
            "input_source": input_source,
            "target_source": target_source,
            "history_days": history_days,
            "use_history": use_history,
            "library_track_count": library_track_count(conn, target_source),
            "library_sample_strategy": (
                "random_db_sample" if random_library_sample else "top_play_count"
            ),
            "constraints": constraints,
            "recent_history": recent,
            "library_tracks": library_tracks(
                conn,
                target_source,
                input_source,
                track_limit,
                random_library_sample,
            ),
            "expected_output_shape": {
                "recommendations": [
                    {
                        "track_id": "number",
                        "reason": "string",
                    }
                ]
            },
        }


def recommendation_schema(max_recommendations: int = 3) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "recommendations": {
                "type": "array",
                "minItems": 1,
                "maxItems": max_recommendations,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "track_id": {"type": "integer"},
                        "reason": {"type": "string"},
                    },
                    "required": [
                        "track_id",
                        "reason",
                    ],
                },
            }
        },
        "required": ["recommendations"],
    }


def recommend_with_openai(
    context: dict[str, Any],
    model: str,
    system_prompt: str | None = None,
    max_recommendations: int = 3,
) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "openai package is not installed. Run: pip install -r "
            "03_matching_recommendation/requirements.txt"
        ) from exc

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set.")

    client = OpenAI()
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": system_prompt or DEFAULT_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(context, ensure_ascii=False),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "music_recommendations",
                "schema": recommendation_schema(max_recommendations),
                "strict": True,
            }
        },
    )
    return json.loads(response.output_text)


def validate_recommendations(
    context: dict[str, Any], recommendations: dict[str, Any]
) -> dict[str, Any]:
    tracks_by_id = {track["track_id"]: track for track in context["library_tracks"]}
    invalid_ids = []
    duplicate_track_ids = []
    seen_track_ids = set()
    enriched_items = []
    for item in recommendations.get("recommendations", []):
        track_id = item.get("track_id")
        if track_id in seen_track_ids:
            duplicate_track_ids.append(track_id)
            continue
        seen_track_ids.add(track_id)
        if track_id not in tracks_by_id:
            invalid_ids.append(track_id)
            continue
        track = tracks_by_id[track_id]
        enriched_items.append(
            {
                "track_id": track["track_id"],
                "track_source_id": track["track_source_id"],
                "title": track["title"],
                "artist": track["artist"],
                "reason": item["reason"],
            }
        )

    result = dict(recommendations)
    result["recommendations"] = enriched_items
    result["validation"] = {
        "candidate_track_ids": sorted(tracks_by_id),
        "candidate_track_source_ids": sorted(
            track["track_source_id"] for track in context["library_tracks"]
        ),
        "invalid_track_ids": invalid_ids,
        "invalid_track_source_ids": [],
        "duplicate_track_ids": duplicate_track_ids,
        "valid": not invalid_ids and not duplicate_track_ids,
    }
    return result


def save_recommendation_logs(
    context: dict[str, Any],
    result: dict[str, Any],
    recommendation_type: str,
    model_name: str,
) -> int:
    items = result.get("recommendations", [])
    if not items:
        return 0

    context_json = json.dumps(context, ensure_ascii=False)
    result_json = json.dumps(result, ensure_ascii=False)
    run_sql = """
        INSERT INTO recommendation_runs (
            recommendation_type,
            input_source,
            target_source,
            model_name,
            context_json,
            result_json
        ) VALUES (
            :recommendation_type,
            :input_source,
            :target_source,
            :model_name,
            :context_json,
            :result_json
        )
        RETURNING recommendation_run_id INTO :recommendation_run_id
    """
    item_sql = """
        INSERT INTO recommendation_items (
            recommendation_run_id,
            rank_no,
            track_id,
            track_source_id,
            reason_text,
            item_json
        ) VALUES (
            :recommendation_run_id,
            :rank_no,
            :track_id,
            :track_source_id,
            :reason_text,
            :item_json
        )
    """
    with connect() as conn:
        with conn.cursor() as cur:
            run_id_var = cur.var(oracledb.NUMBER)
            cur.execute(
                run_sql,
                {
                    "recommendation_type": recommendation_type,
                    "input_source": context["input_source"],
                    "target_source": context["target_source"],
                    "model_name": model_name,
                    "context_json": context_json,
                    "result_json": result_json,
                    "recommendation_run_id": run_id_var,
                },
            )
            recommendation_run_id = int(run_id_var.getvalue()[0])
            rows = [
                {
                    "recommendation_run_id": recommendation_run_id,
                    "rank_no": index,
                    "track_id": item["track_id"],
                    "track_source_id": item["track_source_id"],
                    "reason_text": item["reason"],
                    "item_json": json.dumps(item, ensure_ascii=False),
                }
                for index, item in enumerate(items, start=1)
            ]
            cur.executemany(item_sql, rows)
        conn.commit()
    return len(items)


def print_json(data: dict[str, Any], output: str | None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {path}")
        return
    print(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 Oracle recommendation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="Check Oracle connectivity and row counts")

    context_parser = subparsers.add_parser(
        "context", help="Build JSON input for an LLM recommendation request"
    )
    context_parser.add_argument("--history-limit", type=int, default=20)
    context_parser.add_argument("--history-days", type=int)
    context_parser.add_argument("--no-history", action="store_true")
    context_parser.add_argument("--track-limit", type=int, default=20)
    context_parser.add_argument("--random-library-sample", action="store_true")
    context_parser.add_argument("--input-source", default="youtube_music")
    context_parser.add_argument("--target-source", default="local")
    context_parser.add_argument("--output")

    recommend_parser = subparsers.add_parser(
        "recommend", help="Ask OpenAI to recommend tracks from the Oracle context"
    )
    recommend_parser.add_argument("--history-limit", type=int, default=20)
    recommend_parser.add_argument("--history-days", type=int)
    recommend_parser.add_argument("--no-history", action="store_true")
    recommend_parser.add_argument("--track-limit", type=int, default=20)
    recommend_parser.add_argument("--random-library-sample", action="store_true")
    recommend_parser.add_argument("--input-source", default="youtube_music")
    recommend_parser.add_argument("--target-source", default="local")
    recommend_parser.add_argument(
        "--model", default=env_or_default("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    )
    recommend_parser.add_argument("--output")
    recommend_parser.add_argument(
        "--save-db",
        action="store_true",
        help="Save returned recommendations into recommendation tables",
    )
    recommend_parser.add_argument(
        "--recommendation-type",
        default="phase1_llm",
        help="recommendation_type value used when --save-db is enabled",
    )

    args = parser.parse_args()

    if args.command == "health":
        print_json(health(), None)
        return 0

    if args.command == "context":
        data = build_context(
            args.history_limit,
            args.track_limit,
            args.input_source,
            args.target_source,
            args.history_days,
            args.random_library_sample,
            not args.no_history,
        )
        print_json(data, args.output)
        return 0

    if args.command == "recommend":
        context = build_context(
            args.history_limit,
            args.track_limit,
            args.input_source,
            args.target_source,
            args.history_days,
            args.random_library_sample,
            not args.no_history,
        )
        recommendations = recommend_with_openai(context, args.model)
        result = validate_recommendations(context, recommendations)
        if args.save_db:
            if not result["validation"]["valid"]:
                raise SystemExit(
                    "Refusing to save recommendations with invalid track IDs."
                )
            result["saved_logs"] = save_recommendation_logs(
                context, result, args.recommendation_type, args.model
            )
        print_json(result, args.output)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
