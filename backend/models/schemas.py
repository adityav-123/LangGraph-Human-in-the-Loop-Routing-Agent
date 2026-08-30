"""Pydantic request/response schemas for all API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class UploadResponse(BaseModel):
    document_id: str
    file_name: str
    status: str = "processing"
    message: str = "Document uploaded. Classification starting."


class DocumentSummary(BaseModel):
    document_id: str
    file_name: str
    processing_status: str = "uploaded"
    status_updated_at: str
    doc_type: Optional[str] = None
    urgency: Optional[str] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    assigned_department: Optional[str] = None
    reviewer_id: Optional[str] = None
    human_decision: Optional[str] = "pending"
    uploaded_at: str
    decision_at: Optional[str] = None
    downstream_action: Optional[str] = None


class DocumentDetail(DocumentSummary):
    classification_reasoning: Optional[str] = None
    parties: list[str] = []
    key_dates: list[str] = []
    monetary_amounts: list[str] = []
    routing_reason: Optional[str] = None
    reviewer_notes: Optional[str] = None
    audit_trail: list[dict] = []


class ApproveRequest(BaseModel):
    reviewer_notes: Optional[str] = Field(None, max_length=1000)


class RejectRequest(BaseModel):
    reviewer_notes: str = Field(..., min_length=5, max_length=1000,
                                description="Reason for rejection is required")


class RerouteRequest(BaseModel):
    new_department: Literal["finance", "legal", "hr", "medical", "operations", "compliance"]
    reviewer_notes: Optional[str] = Field(None, max_length=1000)


class AuditEntry(BaseModel):
    event: str
    node: str
    at: str
    data: dict = {}


class QueueStats(BaseModel):
    total: int
    pending: int
    approved: int
    rejected: int
    processing: int
    awaiting_review: int
    failed: int
    by_department: dict[str, int]
    by_urgency: dict[str, int]
    alerts: list[dict]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
