from __future__ import annotations

import json
import os
import threading
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .history import MetricsHistory
from .snapshot import collect_system_snapshot

POLL_INTERVAL_SECONDS = float(os.getenv("SYSTEM_PROFILER_POLL_INTERVAL_SECONDS", "2"))
HISTORY_MAXLEN = int(os.getenv("SYSTEM_PROFILER_HISTORY_MAXLEN", "300"))
ALLOWED_ORIGINS = [
    item.strip()
    for item in os.getenv("SYSTEM_PROFILER_ALLOWED_ORIGINS", "http://localhost:6342").split(",")
    if item.strip()
]

history = MetricsHistory(maxlen=HISTORY_MAXLEN)
stop_event = threading.Event()
worker_thread: threading.Thread | None = None


def _sampler_loop() -> None:
    while not stop_event.is_set():
        snapshot = collect_system_snapshot()
        history.append(snapshot)
        stop_event.wait(POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_thread
    history.append(collect_system_snapshot())
    stop_event.clear()
    worker_thread = threading.Thread(target=_sampler_loop, name="system-profiler-sampler", daemon=True)
    worker_thread.start()
    yield
    stop_event.set()
    if worker_thread and worker_thread.is_alive():
        worker_thread.join(timeout=1.0)


app = FastAPI(title="LLM Benchmark Studio System Profiler", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _ok(data: Any) -> JSONResponse:
    return JSONResponse({"ok": True, "data": data, "meta": {}})


@app.get("/health")
async def health() -> JSONResponse:
    return _ok({"service": "system_profiler", "status": "ok"})


@app.get("/snapshot")
async def snapshot() -> JSONResponse:
    latest = history.latest() or collect_system_snapshot()
    return _ok(latest)


@app.get("/history")
async def get_history() -> JSONResponse:
    return _ok(
        {
            "interval_seconds": POLL_INTERVAL_SECONDS,
            "window_minutes": round((HISTORY_MAXLEN * POLL_INTERVAL_SECONDS) / 60, 2),
            "snapshots": history.list(),
        }
    )


@app.get("/stream")
async def stream() -> StreamingResponse:
    def event_stream():
        while not stop_event.is_set():
            payload = {"ok": True, "data": history.latest() or collect_system_snapshot(), "meta": {}}
            yield f"event: profiler-snapshot\ndata: {json.dumps(payload)}\n\n"
            time.sleep(POLL_INTERVAL_SECONDS)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
