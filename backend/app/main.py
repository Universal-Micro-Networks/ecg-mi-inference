"""
ECG MI Inference Backend
FastAPI application with examination and inference endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.examinations import router as examinations_router
from .api.inferences import router as inferences_router
from .database import init_db

# Create FastAPI app
app = FastAPI(
    title="ECG MI Inference API",
    description="API for ECG examination and MI inference",
    version="0.1.0",
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(examinations_router, prefix="/api")
app.include_router(inferences_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Initialize database with sample data on startup."""
    init_db()


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
