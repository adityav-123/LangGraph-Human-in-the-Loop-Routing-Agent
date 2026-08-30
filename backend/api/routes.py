"""
FastAPI route handlers.

Endpoints:
  POST /upload              — Upload a document, kick off the agent graph
  GET  /documents           — List documents with filters
  GET  /documents/{id}      — Full document detail + audit trail
  POST /documents/{id}/approve  — Human approves
  POST /documents/{id}/reject   — Human rejects
  POST /documents/{id}/reroute  — Human reroutes to different department
  GET  /stats               — Queue statistics for dashboard
"""

import uuid
import asyncio
import os
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from backend.db.database import get_db, User
from backend.db import crud
from backend.models.schemas import (
    UploadResponse, DocumentSummary, DocumentDetail,
    ApproveRequest, RejectRequest, RerouteRequest, QueueStats,
)
from backend.api.auth import get_current_user
from backend.utils.ocr import extract_text
from backend.agents.graph import get_graph
from backend.agents.state import DocumentState
from backend.agents.nodes import human_checkpoint, post_approval_action, audit_log
from datetime import datetime, timezone

router    = APIRouter()
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/tmp/doc-routing-uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
ALLOWED_TYPES = {
    "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain", "image/png", "image/jpeg", "image/tiff",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doc_to_summary(doc) -> DocumentSummary:
    return DocumentSummary(
        document_id=doc.document_id,
        file_name=doc.file_name,
        processing_status=doc.processing_status,
        status_updated_at=doc.status_updated_at,
        doc_type=doc.doc_type,
        urgency=doc.urgency,
        confidence=doc.confidence,
        summary=doc.summary,
        assigned_department=doc.assigned_department,
        reviewer_id=doc.reviewer_id,
        human_decision=doc.human_decision,
        uploaded_at=doc.uploaded_at,
        decision_at=doc.decision_at,
        downstream_action=doc.downstream_action,
    )


def _doc_to_detail(doc) -> DocumentDetail:
    return DocumentDetail(
        **_doc_to_summary(doc).model_dump(),
        classification_reasoning=doc.classification_reasoning,
        parties=doc.parties or [],
        key_dates=doc.key_dates or [],
        monetary_amounts=doc.monetary_amounts or [],
        routing_reason=doc.routing_reason,
        reviewer_notes=doc.reviewer_notes,
        audit_trail=doc.audit_trail or [],
    )


def _doc_to_state(doc) -> DocumentState:
    return {
        "document_id": doc.document_id,
        "file_name": doc.file_name,
        "file_path": doc.file_path,
        "raw_text": doc.raw_text or "",
        "uploaded_at": doc.uploaded_at,
        "doc_type": doc.doc_type,
        "urgency": doc.urgency,
        "confidence": doc.confidence,
        "classification_reasoning": doc.classification_reasoning,
        "parties": doc.parties or [],
        "key_dates": doc.key_dates or [],
        "monetary_amounts": doc.monetary_amounts or [],
        "summary": doc.summary,
        "assigned_department": doc.assigned_department,
        "reviewer_id": doc.reviewer_id,
        "routing_reason": doc.routing_reason,
        "human_decision": doc.human_decision,
        "reviewer_notes": doc.reviewer_notes,
        "decision_at": doc.decision_at,
        "rerouted_to": doc.rerouted_to,
        "downstream_action": doc.downstream_action,
        "action_result": doc.action_result,
        "audit_trail": doc.audit_trail or [],
        "error": doc.error,
        "current_node": doc.current_node,
        "processing_status": doc.processing_status,
        "status_updated_at": doc.status_updated_at,
    }


async def _run_graph(doc_id: str, initial_state: DocumentState):
    """
    Background task: runs the LangGraph agent.
    The graph will pause at human_checkpoint automatically.
    We sync state to Postgres after each node.
    """
    try:
        from backend.db.database import SessionLocal
        import psycopg

        db_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/docrouting")
        conn   = psycopg.connect(db_url, autocommit=True)
        graph  = get_graph(conn)

        config = {"configurable": {"thread_id": doc_id}}

        def _collect_events():
            return list(graph.stream(initial_state, config, stream_mode="values"))

        events = await asyncio.to_thread(_collect_events)
        for event in events:
            with SessionLocal() as db:
                crud.sync_state_to_db(db, doc_id, event)

    except Exception as e:
        with SessionLocal() as db:
            doc = crud.get_document(db, doc_id)
            if doc:
                doc.error = str(e)
                doc.processing_status = "failed"
                doc.status_updated_at = datetime.now(timezone.utc).isoformat()
                db.commit()


async def _resume_graph(doc_id: str, decision: str, notes: str, new_department: str = None):
    """Continue the post-decision workflow from the persisted document state."""
    try:
        from backend.db.database import SessionLocal
        with SessionLocal() as db:
            doc = crud.get_document(db, doc_id)
            if not doc:
                return

            state = _doc_to_state(doc)
            state["human_decision"] = decision
            state["reviewer_notes"] = notes
            if new_department:
                state["assigned_department"] = new_department
                state["rerouted_to"] = new_department

            state.update(human_checkpoint(state))
            state.update(post_approval_action(state))
            state.update(audit_log(state))
            crud.sync_state_to_db(db, doc_id, state)

    except Exception as e:
        from backend.db.database import SessionLocal
        with SessionLocal() as db:
            doc = crud.get_document(db, doc_id)
            if doc:
                doc.error = str(e)
                doc.processing_status = "failed"
                doc.status_updated_at = datetime.now(timezone.utc).isoformat()
                db.commit()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}")

    # Read and check file size
    content = await file.read()
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_MB}MB limit")

    # Save to disk
    doc_id    = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"
    file_path.write_bytes(content)

    # Extract text
    try:
        raw_text = extract_text(str(file_path))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Text extraction failed: {e}")

    # Persist to DB
    doc = crud.create_document(db, doc_id, file.filename, str(file_path), raw_text)
    doc.processing_status = "classifying"
    doc.status_updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()

    # Build initial state
    initial_state: DocumentState = {
        "document_id": doc_id,
        "file_name":   file.filename,
        "file_path":   str(file_path),
        "raw_text":    raw_text,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "doc_type":             None,
        "urgency":              None,
        "confidence":           None,
        "classification_reasoning": None,
        "parties":              None,
        "key_dates":            None,
        "monetary_amounts":     None,
        "summary":              None,
        "assigned_department":  None,
        "reviewer_id":          None,
        "routing_reason":       None,
        "human_decision":       None,
        "reviewer_notes":       None,
        "decision_at":          None,
        "rerouted_to":          None,
        "downstream_action":    None,
        "action_result":        None,
        "audit_trail":          [],
        "error":                None,
        "current_node":         None,
    }

    # Kick off the agent in the background
    background_tasks.add_task(_run_graph, doc_id, initial_state)

    return UploadResponse(document_id=doc_id, file_name=file.filename)


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(
    department: str | None = None,
    decision:   str | None = None,
    urgency:    str | None = None,
    limit:      int = 50,
    offset:     int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        if department and department != current_user.role:
            return []
        department = current_user.role

    # Fix: if decision is 'all', we don't want to filter by decision
    if decision == "all":
        decision = None

    docs = crud.list_documents(db, department, decision, urgency, limit, offset)
    return [_doc_to_summary(d) for d in docs]


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != "admin" and doc.assigned_department != current_user.role:
        raise HTTPException(status_code=403, detail="Not authorized to view this document")
    return _doc_to_detail(doc)


@router.post("/documents/{doc_id}/approve", response_model=DocumentSummary)
async def approve_document(
    doc_id: str,
    body: ApproveRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != "admin" and doc.assigned_department != current_user.role:
        raise HTTPException(status_code=403, detail="Not authorized to act on this document")
    if doc.human_decision != "pending":
        raise HTTPException(status_code=409, detail=f"Document already has decision: {doc.human_decision}")

    crud.update_human_decision(db, doc_id, "approved", body.reviewer_notes)
    background_tasks.add_task(_resume_graph, doc_id, "approved", body.reviewer_notes)
    return _doc_to_summary(crud.get_document(db, doc_id))


@router.post("/documents/{doc_id}/reject", response_model=DocumentSummary)
async def reject_document(
    doc_id: str,
    body: RejectRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != "admin" and doc.assigned_department != current_user.role:
        raise HTTPException(status_code=403, detail="Not authorized to act on this document")
    if doc.human_decision != "pending":
        raise HTTPException(status_code=409, detail=f"Document already has decision: {doc.human_decision}")

    crud.update_human_decision(db, doc_id, "rejected", body.reviewer_notes)
    background_tasks.add_task(_resume_graph, doc_id, "rejected", body.reviewer_notes)
    return _doc_to_summary(crud.get_document(db, doc_id))


@router.post("/documents/{doc_id}/reroute", response_model=DocumentSummary)
async def reroute_document(
    doc_id: str,
    body: RerouteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if current_user.role != "admin" and doc.assigned_department != current_user.role:
        raise HTTPException(status_code=403, detail="Not authorized to act on this document")
    if doc.human_decision != "pending":
        raise HTTPException(status_code=409, detail=f"Document already has decision: {doc.human_decision}")

    crud.update_human_decision(db, doc_id, "rerouted", body.reviewer_notes, body.new_department)
    background_tasks.add_task(_resume_graph, doc_id, "rerouted", body.reviewer_notes, body.new_department)
    return _doc_to_summary(crud.get_document(db, doc_id))


@router.get("/stats", response_model=QueueStats)
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stats = crud.get_queue_stats(db)
    if current_user.role == "admin":
        return stats

    docs = crud.list_documents(db, department=current_user.role, limit=200)
    filtered_alerts = [alert for alert in stats["alerts"] if any(d.document_id == alert["document_id"] for d in docs)]
    return {
        **stats,
        "total": len(docs),
        "pending": sum(1 for d in docs if d.human_decision == "pending"),
        "approved": sum(1 for d in docs if d.human_decision == "approved"),
        "rejected": sum(1 for d in docs if d.human_decision == "rejected"),
        "processing": sum(1 for d in docs if d.processing_status in {"uploaded", "classifying", "extracting_metadata", "routing", "post_approval"}),
        "awaiting_review": sum(1 for d in docs if d.processing_status == "awaiting_review"),
        "failed": sum(1 for d in docs if d.processing_status == "failed"),
        "by_department": {current_user.role: len(docs)},
        "by_urgency": {
            urgency: sum(1 for d in docs if d.urgency == urgency)
            for urgency in sorted({d.urgency for d in docs if d.urgency})
        },
        "alerts": filtered_alerts,
    }
