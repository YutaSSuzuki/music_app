#!/usr/bin/env python3
"""Local audio file server intended to run on gerbera only."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse


def allowed_roots() -> list[Path]:
    raw_roots = os.environ.get("MUSIC_ALLOWED_ROOTS")
    if raw_roots:
        return [Path(root).expanduser().resolve() for root in raw_roots.split(os.pathsep)]
    return [
        Path("/mnt/d/yu28s/Music").resolve(),
        (Path.home() / "Music").resolve(),
    ]


app = FastAPI(title="Local Audio Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://192.168.11.23:8000",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, object]:
    roots = allowed_roots()
    return {
        "status": "ok",
        "allowed_roots": [str(root) for root in roots],
        "existing_roots": [str(root) for root in roots if root.exists()],
    }


@app.get("/audio")
def audio(path: str = Query(...)) -> FileResponse:
    target = Path(unquote(path)).expanduser().resolve()
    roots = allowed_roots()

    if not any(target == root or target.is_relative_to(root) for root in roots):
        raise HTTPException(
            status_code=403,
            detail="Path is outside allowed music roots",
        )

    if not target.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return FileResponse(target, media_type=media_type, filename=target.name)
