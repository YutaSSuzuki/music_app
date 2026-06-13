#!/usr/bin/env python3
"""Small FastAPI preview for Oracle-backed music recommendations."""

from __future__ import annotations

import mimetypes
import json
import os
import sys
from pathlib import Path
from typing import Any

import oracledb
from fastapi import FastAPI, HTTPException, Query
from openai import APIConnectionError, APITimeoutError
from pydantic import BaseModel
from fastapi.responses import FileResponse, HTMLResponse


DEFAULT_USER = "music_app_v2"
DEFAULT_PASSWORD = "CHANGE_ME"
DEFAULT_DSN = "localhost:1521/FREEPDB1"
AVAILABLE_OPENAI_MODELS = [
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-4.1",
]

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent
PROMPT_PATH = APP_ROOT / "prompt_template.txt"
PROMPT_TEMPLATES_DIR = APP_ROOT / "prompt_templates"
DEFAULT_PROMPT_TEMPLATE_ID = "youtube_history"
MATCHING_DIR = REPO_ROOT / "03_matching_recommendation"
if str(MATCHING_DIR) not in sys.path:
    sys.path.append(str(MATCHING_DIR))
YOUTUBE_HISTORY_DIR = REPO_ROOT / "01_youtube_history"
if str(YOUTUBE_HISTORY_DIR) not in sys.path:
    sys.path.append(str(YOUTUBE_HISTORY_DIR))

from phase1_cli import (  # noqa: E402
    DEFAULT_OPENAI_MODEL,
    build_context,
    recommend_with_openai,
    save_recommendation_logs,
    validate_recommendations,
)
from youtube_takeout_import import import_takeout_content  # noqa: E402

app = FastAPI(title="Music App")


class PromptPayload(BaseModel):
    prompt: str


class PromptTemplatePayload(BaseModel):
    prompt: str


class YouTubeHistoryImportPayload(BaseModel):
    filename: str
    content: str
    dry_run: bool = False


class RunRecommendationPayload(BaseModel):
    history_limit: int = 20
    history_days: int | None = 7
    track_limit: int = 20
    max_recommendations: int = 3
    input_source: str = "youtube_music"
    target_source: str = "local"
    model: str = DEFAULT_OPENAI_MODEL
    recommendation_type: str = "web_prompt"
    random_library_sample: bool = True
    prompt_template_id: str = DEFAULT_PROMPT_TEMPLATE_ID
    recommendation_mode: str = "youtube_history"
    use_history: bool = True
    use_all_candidates: bool = False


def env_or_default(name: str, default: str) -> str:
    return os.environ.get(name, default)


def connect() -> oracledb.Connection:
    return oracledb.connect(
        user=env_or_default("ORACLE_USER", DEFAULT_USER),
        password=env_or_default("ORACLE_PASSWORD", DEFAULT_PASSWORD),
        dsn=env_or_default("ORACLE_DSN", DEFAULT_DSN),
    )


def safe_template_id(template_id: str) -> str:
    if not template_id or not all(
        char.isalnum() or char in {"_", "-"} for char in template_id
    ):
        raise HTTPException(status_code=400, detail="Invalid prompt template id")
    return template_id


def prompt_template_path(template_id: str) -> Path:
    return PROMPT_TEMPLATES_DIR / f"{safe_template_id(template_id)}.txt"


def read_prompt_template(template_id: str) -> str:
    path = prompt_template_path(template_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return path.read_text(encoding="utf-8")


def dedupe_recommendations(result: dict[str, Any]) -> dict[str, Any]:
    seen_track_ids = set()
    unique_items = []
    duplicate_track_ids = []
    for item in result.get("recommendations", []):
        track_id = item.get("track_id")
        if track_id in seen_track_ids:
            duplicate_track_ids.append(track_id)
            continue
        seen_track_ids.add(track_id)
        unique_items.append(item)
    deduped = dict(result)
    deduped["recommendations"] = unique_items
    if duplicate_track_ids:
        deduped["duplicate_track_ids_removed"] = duplicate_track_ids
    return deduped


def run_random_db_recommendations(payload: RunRecommendationPayload) -> dict[str, Any]:
    context = build_context(
        0,
        min(max(payload.max_recommendations * 5, payload.max_recommendations), 100),
        payload.input_source,
        payload.target_source,
        None,
        True,
        False,
    )
    recommendations = [
        {
            "track_id": track["track_id"],
            "track_source_id": track["track_source_id"],
            "title": track["title"],
            "artist": track["artist"],
            "reason": "DBからランダムに選出しました。",
        }
        for track in context["library_tracks"][: payload.max_recommendations]
    ]
    result = {
        "recommendations": recommendations,
        "validation": {
            "candidate_track_ids": sorted(track["track_id"] for track in context["library_tracks"]),
            "candidate_track_source_ids": sorted(
                track["track_source_id"] for track in context["library_tracks"]
            ),
            "invalid_track_ids": [],
            "invalid_track_source_ids": [],
            "valid": True,
        },
    }
    result = dedupe_recommendations(result)
    result["saved_logs"] = save_recommendation_logs(
        context,
        result,
        "web_random_db",
        "oracle-db-random",
    )
    return result


def row_to_item(row: tuple[Any, ...]) -> dict[str, Any]:
    track_source_id = row[4]
    file_path_linux = row[6]
    file_exists_on_server = bool(file_path_linux and Path(file_path_linux).is_file())
    return {
        "recommendation_run_id": row[0],
        "rank_no": row[1],
        "track_id": row[2],
        "title": row[3],
        "track_source_id": track_source_id,
        "artist": row[5],
        "reason": row[7],
        "audio_url": f"/tracks/{track_source_id}/audio",
        "file_exists_on_server": file_exists_on_server,
    }


def random_row_to_item(row: tuple[Any, ...], rank_no: int) -> dict[str, Any]:
    track_source_id = row[2]
    file_path_linux = row[5]
    return {
        "recommendation_run_id": None,
        "rank_no": rank_no,
        "track_id": row[0],
        "title": row[1],
        "track_source_id": track_source_id,
        "artist": row[3],
        "reason": "DBからランダムに選出しました。",
        "audio_url": f"/tracks/{track_source_id}/audio",
        "file_exists_on_server": bool(file_path_linux and Path(file_path_linux).is_file()),
    }


@app.get("/api/status")
def status() -> dict[str, Any]:
    return {
        "openai_api_key_configured": bool(os.environ.get("OPENAI_API_KEY")),
        "oracle_user": env_or_default("ORACLE_USER", DEFAULT_USER),
        "oracle_dsn": env_or_default("ORACLE_DSN", DEFAULT_DSN),
    }


@app.get("/api/models")
def models() -> dict[str, Any]:
    return {
        "default_model": DEFAULT_OPENAI_MODEL,
        "models": AVAILABLE_OPENAI_MODELS,
    }


@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    return FileResponse(APP_ROOT / "static" / "index.html")


@app.get("/api/prompt")
def get_prompt() -> dict[str, str]:
    return {"prompt": PROMPT_PATH.read_text(encoding="utf-8")}


@app.put("/api/prompt")
def put_prompt(payload: PromptPayload) -> dict[str, str]:
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty")
    PROMPT_PATH.write_text(prompt + "\n", encoding="utf-8")
    return {"status": "saved", "prompt": prompt}


@app.get("/api/prompt-templates")
def list_prompt_templates() -> dict[str, Any]:
    templates = []
    for path in sorted(PROMPT_TEMPLATES_DIR.glob("*.txt")):
        template_id = path.stem
        templates.append(
            {
                "id": template_id,
                "label": template_id.replace("_", " ").title(),
                "prompt": path.read_text(encoding="utf-8"),
            }
        )
    return {
        "default_template_id": DEFAULT_PROMPT_TEMPLATE_ID,
        "templates": templates,
    }


@app.get("/api/prompt-templates/{template_id}")
def get_prompt_template(template_id: str) -> dict[str, str]:
    return {"id": safe_template_id(template_id), "prompt": read_prompt_template(template_id)}


@app.put("/api/prompt-templates/{template_id}")
def put_prompt_template(
    template_id: str, payload: PromptTemplatePayload
) -> dict[str, str]:
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty")
    path = prompt_template_path(template_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Prompt template not found")
    path.write_text(prompt + "\n", encoding="utf-8")
    return {"status": "saved", "id": safe_template_id(template_id), "prompt": prompt}


@app.post("/api/youtube-history/import")
def import_youtube_history(payload: YouTubeHistoryImportPayload) -> dict[str, Any]:
    if not payload.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Upload watch-history.json")
    try:
        result = import_takeout_content(payload.content, payload.dry_run)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@app.post("/api/recommendations/run")
def run_recommendations(payload: RunRecommendationPayload) -> dict[str, Any]:
    if payload.recommendation_mode not in {"youtube_history", "random"}:
        raise HTTPException(status_code=400, detail="Invalid recommendation_mode")
    if payload.max_recommendations < 1 or payload.max_recommendations > 20:
        raise HTTPException(
            status_code=400,
            detail="max_recommendations must be between 1 and 20",
        )
    if payload.recommendation_mode == "random":
        return run_random_db_recommendations(payload)

    if payload.model not in AVAILABLE_OPENAI_MODELS:
        raise HTTPException(status_code=400, detail="Invalid model")
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set on the Web API server",
        )

    prompt = read_prompt_template(payload.prompt_template_id).strip()
    effective_track_limit = 100000 if payload.use_all_candidates else payload.track_limit
    context = build_context(
        payload.history_limit,
        effective_track_limit,
        payload.input_source,
        payload.target_source,
        payload.history_days,
        False,
        True,
    )
    context["requested_recommendation_count"] = payload.max_recommendations
    context["use_all_candidates"] = payload.use_all_candidates
    context["constraints"].append(
        f"Return exactly {payload.max_recommendations} recommendation(s) if enough valid candidates exist."
    )
    context["constraints"].append("Do not return the same track_id more than once.")
    try:
        recommendations = recommend_with_openai(
            context,
            payload.model,
            prompt,
            payload.max_recommendations,
        )
    except APITimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=(
                "OpenAI API request timed out. Check AP EC2 outbound TCP 443, "
                "the Network ACL, and the route table."
            ),
        ) from exc
    except APIConnectionError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not connect to the OpenAI API. Check AP EC2 outbound "
                "TCP 443, DNS, the Network ACL, and the route table."
            ),
        ) from exc
    result = validate_recommendations(context, dedupe_recommendations(recommendations))
    if not result["validation"]["valid"]:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Refusing to save recommendations with invalid track IDs",
                "validation": result["validation"],
            },
        )

    result["saved_logs"] = save_recommendation_logs(
        context,
        result,
        payload.recommendation_type,
        payload.model,
    )
    return result


@app.get("/api/recommendations/latest")
def latest_recommendations() -> list[dict[str, Any]]:
    sql = """
        SELECT
            rr.recommendation_run_id,
            ri.rank_no,
            t.track_id,
            t.title,
            ri.track_source_id,
            LISTAGG(a.name, ', ') WITHIN GROUP (ORDER BY ta.artist_order) AS artist,
            haf.file_path_linux,
            ri.reason_text
        FROM recommendation_runs rr
        JOIN recommendation_items ri
          ON ri.recommendation_run_id = rr.recommendation_run_id
        JOIN tracks t
          ON t.track_id = ri.track_id
        JOIN track_artists ta
          ON ta.track_id = t.track_id
        JOIN artists a
          ON a.artist_id = ta.artist_id
        LEFT JOIN hosted_audio_files haf
          ON haf.track_source_id = ri.track_source_id
        WHERE rr.recommendation_run_id = (
            SELECT MAX(recommendation_run_id)
            FROM recommendation_runs
        )
        GROUP BY
            rr.recommendation_run_id,
            ri.rank_no,
            t.track_id,
            t.title,
            ri.track_source_id,
            haf.file_path_linux,
            ri.reason_text
        ORDER BY ri.rank_no
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [row_to_item(row) for row in cur]


@app.get("/api/recommendations/random")
def random_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict[str, Any]]:
    sql = """
        WITH candidate_tracks AS (
        SELECT
            t.track_id,
            t.title,
            ts.track_source_id,
            LISTAGG(a.name, ', ') WITHIN GROUP (ORDER BY ta.artist_order) AS artist,
            DBMS_RANDOM.VALUE AS random_order,
            MAX(haf.file_path_linux) AS file_path_linux
        FROM tracks t
        JOIN track_sources ts
          ON ts.track_id = t.track_id
         AND ts.source_name = 'local'
         AND ts.availability_status = 'available'
        JOIN hosted_audio_files haf
          ON haf.track_source_id = ts.track_source_id
         AND haf.is_available = 1
        JOIN track_artists ta
          ON ta.track_id = t.track_id
        JOIN artists a
          ON a.artist_id = ta.artist_id
        GROUP BY
            t.track_id,
            t.title,
            ts.track_source_id
        ),
        deduped_tracks AS (
            SELECT
                candidate_tracks.*,
                ROW_NUMBER() OVER (
                    PARTITION BY track_id
                    ORDER BY track_source_id
                ) AS source_rank
            FROM candidate_tracks
        )
        SELECT
            track_id,
            title,
            track_source_id,
            artist,
            random_order,
            file_path_linux
        FROM deduped_tracks
        WHERE source_rank = 1
        ORDER BY DBMS_RANDOM.VALUE
        FETCH FIRST :limit ROWS ONLY
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"limit": limit})
            return [
                random_row_to_item(row, rank_no)
                for rank_no, row in enumerate(cur, start=1)
            ]


@app.get("/tracks/{track_source_id}/audio")
def track_audio(track_source_id: int) -> FileResponse:
    sql = """
        SELECT file_path_linux
        FROM hosted_audio_files
        WHERE track_source_id = :track_source_id
          AND is_available = 1
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"track_source_id": track_source_id})
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Audio file not found in DB")

    path = Path(row[0])
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Hosted audio file is missing on server",
        )

    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)
