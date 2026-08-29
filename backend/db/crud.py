"""
CRUD helpers. All DB writes go through here — keeps the API layer clean.
"""

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

    fields = [
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

    return {
        "total":           total or 0,
        "pending":         pending or 0,
        "approved":        approved or 0,
        "rejected":        rejected or 0,
        "by_department":   {r[0] or "unknown": r[1] for r in dept_rows},
        "by_urgency":      {r[0] or "unknown": r[1] for r in urgency_rows},
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
    db.commit()
    db.refresh(doc)
    return doc
