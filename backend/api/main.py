"""
FastAPI application entrypoint.

Run with:
    uvicorn backend.api.main:app --reload --port 8000
"""

import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file into environment variables before other imports

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router as docs_router
from backend.api.auth import router as auth_router
from backend.db.database import create_tables

app = FastAPI(
    title="Document Routing & Approval Agent",
    description="LangGraph-powered document classification, routing, and human-in-the-loop approval",
    version="1.0.0",
)

# CORS — tighten origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(docs_router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    """Create DB tables on first launch."""
    create_tables()


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# JWT auth stub — wire in your auth provider here
# ---------------------------------------------------------------------------
# from fastapi.security import HTTPBearer
# security = HTTPBearer()
# Add `token: HTTPAuthorizationCredentials = Depends(security)` to protected routes
