"""
ECG MI Inference Backend
FastAPI application with examination and inference endpoints.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import examination_events
from .api.auth import router as auth_router
from .api.examinations import router as examinations_router
from .api.inferences import router as inferences_router
from .auth_security import get_current_user, init_system_password_if_missing, require_jwt_secret
from .database import SessionLocal, init_db
from .file_importer import import_mfer_file
from .folder_watcher import FolderWatcherService

watcher_service = FolderWatcherService(importer_func=import_mfer_file)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup/shutdown lifecycle."""
    init_db()
    require_jwt_secret()
    db = SessionLocal()
    try:
        init_system_password_if_missing(db)
    finally:
        db.close()
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
