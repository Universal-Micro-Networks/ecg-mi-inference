"""
ECG MI Inference Backend
FastAPI application with examination and inference endpoints.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import examination_events
from .api.auth import router as auth_router
from .api.examinations import router as examinations_router
from .api.inferences import router as inferences_router
from .auth_security import get_current_user, require_jwt_secret
from .database import init_db, purge_sensitive_generated_artifacts
from .file_importer import import_mfer_file
from .folder_watcher import FolderWatcherService

# app.* ロガーの INFO を明示的に有効化（Uvicorn の既定設定でも推論詳細ログを見えるようにする）
_APP_LOG_LEVEL_NAME = os.getenv("APP_LOG_LEVEL", "INFO").upper()
_APP_LOG_LEVEL = getattr(logging, _APP_LOG_LEVEL_NAME, logging.INFO)
_APP_LOGGER = logging.getLogger("app")
_APP_LOGGER.setLevel(_APP_LOG_LEVEL)
# Uvicorn の設定によっては app.* にハンドラが付かず、WARNING 以上だけ lastResort で出る。
# その場合 INFO が捨てられるため、app ロガーに明示ハンドラを付ける。
if not _APP_LOGGER.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(_APP_LOG_LEVEL)
    _h.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    _APP_LOGGER.addHandler(_h)
_APP_LOGGER.propagate = True

watcher_service = FolderWatcherService(importer_func=import_mfer_file)


def _purge_ephemeral_files() -> None:
    """過去実行で残った生成物（画像キャッシュ/波形CSV）を削除する。"""
    backend_root = Path(__file__).resolve().parent.parent
    ecg_cache_dir = backend_root / "data" / "ecg_cache"
    waves_dir = backend_root / "data" / "waves"

    for p in ecg_cache_dir.glob("*.png"):
        try:
            p.unlink()
        except OSError:
            _APP_LOGGER.warning("failed to delete cached ECG image: %s", p)

    for p in waves_dir.glob("*.csv"):
        try:
            p.unlink()
        except OSError:
            _APP_LOGGER.warning("failed to delete cached wave CSV: %s", p)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup/shutdown lifecycle."""
    init_db()
    if os.getenv("ECG_MI_EPHEMERAL_MODE", "1").lower() in {"1", "true", "yes", "on"}:
        purge_sensitive_generated_artifacts()
        _purge_ephemeral_files()
    require_jwt_secret()
    examination_events.set_main_event_loop(asyncio.get_running_loop())
    watcher_service.start()
    try:
        yield
    finally:
        examination_events.set_main_event_loop(None)
        watcher_service.stop()


# Create FastAPI app
app = FastAPI(
    title="ECG MI Inference API",
    description="API for ECG examination and MI inference",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8200",
        "*",
    ],  # Vite dev server / API port mapping
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(examinations_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(inferences_router, prefix="/api", dependencies=[Depends(get_current_user)])


@app.get("/health")
def health_check():
    """Health check endpoint."""
    watcher = watcher_service.snapshot()
    # 監視フォルダ待ち（bootstrap スレッド）はプロセスは正常のため 200 とする
    ok_watcher = watcher["watching"] or not watcher["folder"] or watcher.get("bootstrap_pending")
    if ok_watcher:
        return {"status": "ok", "folder_watcher": watcher}
    return JSONResponse(status_code=503, content={"status": "degraded", "folder_watcher": watcher})
