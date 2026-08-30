"""
CRUD helpers. All DB writes go through here — keeps the API layer clean.
"""

import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import Document
from datetime import datetime, timezone


def create_document(db: Session, doc_id: str, file_name: str, file_path: str, raw_text: str) -> Document:
    now = datetime.now(timezone.utc).isoformat()
    doc = Document(
        document_id=doc_id,
        file_name=file_name,
        file_path=file_path,
        raw_text=raw_text,
        uploaded_at=now,
        processing_status="uploaded",
        status_updated_at=now,
        audit_trail=[],
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def sync_state_to_db(db: Session, doc_id: str, state: dict) -> Document:
    """
    After each graph node completes, call this to mirror the LangGraph
    state into our documents table. This gives the React UI fast reads
    without querying LangGraph's checkpoint tables directly.
    """
    doc = db.query(Document).filter(Document.document_id == doc_id).first()
    if not doc:
        return None

    status = _derive_processing_status(state)
    if status and doc.processing_status != status:
        doc.processing_status = status
        doc.status_updated_at = datetime.now(timezone.utc).isoformat()

    fields = [
        "processing_status", "status_updated_at",
        "doc_type", "urgency", "confidence", "classification_reasoning",
        "parties", "key_dates", "monetary_amounts", "summary",
        "assigned_department", "reviewer_id", "routing_reason",
        "human_decision", "reviewer_notes", "decision_at", "rerouted_to",
        "downstream_action", "action_result", "audit_trail", "error", "current_node",
    ]
    for field in fields:
        if field in state and state[field] is not None:
            setattr(doc, field, state[field])

    db.commit()
    db.refresh(doc)
    return doc


def _derive_processing_status(state: dict) -> str:
    if state.get("error"):
        return "failed"
    if state.get("downstream_action"):
        return "completed"
    if state.get("human_decision") == "pending" and state.get("assigned_department"):
        return "awaiting_review"

    current_node = state.get("current_node")
    if current_node == "classify":
        return "classifying"
    if current_node == "extract_metadata":
        return "extracting_metadata"
    if current_node == "route":
        return "routing"
    if current_node == "human_checkpoint":
        return "awaiting_review"
    if current_node == "post_approval_action":
        return "post_approval"
    if current_node == "audit_log":
        return "completed"

    return state.get("processing_status") or "uploaded"


def get_document(db: Session, doc_id: str) -> Document | None:
    return db.query(Document).filter(Document.document_id == doc_id).first()


def list_documents(
    db: Session,
    department: str | None = None,
    decision: str | None = None,
    urgency: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Document]:
    q = db.query(Document)
    if department:
        q = q.filter(Document.assigned_department == department)
    if decision:
        q = q.filter(Document.human_decision == decision)
    if urgency:
        q = q.filter(Document.urgency == urgency)
    return q.order_by(Document.uploaded_at.desc()).limit(limit).offset(offset).all()


def get_queue_stats(db: Session) -> dict:
    total    = db.query(func.count(Document.document_id)).scalar()
    pending  = db.query(func.count(Document.document_id)).filter(Document.human_decision == "pending").scalar()
    approved = db.query(func.count(Document.document_id)).filter(Document.human_decision == "approved").scalar()
    rejected = db.query(func.count(Document.document_id)).filter(Document.human_decision == "rejected").scalar()
    processing = (
        db.query(func.count(Document.document_id))
        .filter(Document.processing_status.in_(["uploaded", "classifying", "extracting_metadata", "routing", "post_approval"]))
        .scalar()
    )
    awaiting_review = (
        db.query(func.count(Document.document_id))
        .filter(Document.processing_status == "awaiting_review")
        .scalar()
    )
    failed = (
        db.query(func.count(Document.document_id))
        .filter(Document.processing_status == "failed")
        .scalar()
    )

    dept_rows = (
        db.query(Document.assigned_department, func.count(Document.document_id))
        .group_by(Document.assigned_department)
        .all()
    )
    urgency_rows = (
        db.query(Document.urgency, func.count(Document.document_id))
        .group_by(Document.urgency)
        .all()
    )
    alerts = build_alerts(db)

    return {
        "total":           total or 0,
        "pending":         pending or 0,
        "approved":        approved or 0,
        "rejected":        rejected or 0,
        "processing":      processing or 0,
        "awaiting_review": awaiting_review or 0,
        "failed":          failed or 0,
        "by_department":   {r[0] or "unknown": r[1] for r in dept_rows},
        "by_urgency":      {r[0] or "unknown": r[1] for r in urgency_rows},
        "alerts":          alerts,
    }


def update_human_decision(
    db: Session,
    doc_id: str,
    decision: str,
    reviewer_notes: str | None = None,
    rerouted_to: str | None = None,
) -> Document | None:
    doc = get_document(db, doc_id)
    if not doc:
        return None
    doc.human_decision  = decision
    doc.reviewer_notes  = reviewer_notes
    doc.rerouted_to     = rerouted_to
    doc.processing_status = "post_approval"
    doc.status_updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(doc)
    return doc


def build_alerts(db: Session) -> list[dict]:
    now = datetime.now(timezone.utc)
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).limit(100).all()
    alerts = []

    for doc in docs:
        uploaded = _parse_iso(doc.uploaded_at)
        if not uploaded:
            continue
        age_minutes = int((now - uploaded).total_seconds() // 60)

        if doc.processing_status == "awaiting_review" and doc.urgency == "critical":
            alerts.append({
                "id": f"critical-{doc.document_id}",
                "severity": "critical",
                "title": f"{doc.file_name} needs urgent review",
                "message": f"Critical {doc.doc_type or 'document'} has been waiting in {doc.assigned_department or 'unassigned'} for {age_minutes} minutes.",
                "document_id": doc.document_id,
            })
        elif doc.processing_status == "awaiting_review" and age_minutes >= 30:
            alerts.append({
                "id": f"overdue-{doc.document_id}",
                "severity": "warning",
                "title": f"{doc.file_name} is overdue for review",
                "message": f"Pending review for {age_minutes} minutes in {doc.assigned_department or 'unassigned'}.",
                "document_id": doc.document_id,
            })
        elif doc.processing_status == "failed":
            alerts.append({
                "id": f"failed-{doc.document_id}",
                "severity": "warning",
                "title": f"{doc.file_name} needs reprocessing",
                "message": "The workflow failed and requires manual retry or correction.",
                "document_id": doc.document_id,
            })

    return alerts[:6]


def _parse_iso(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def create_demo_document(
    db: Session,
    *,
    file_name: str,
    file_path: str,
    raw_text: str,
    state: dict,
) -> Document:
    doc_id = str(uuid.uuid4())
    create_document(db, doc_id, file_name, file_path, raw_text)
    sync_state_to_db(db, doc_id, state)
    return get_document(db, doc_id)
