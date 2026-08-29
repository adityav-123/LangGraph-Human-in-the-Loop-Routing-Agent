"""
State schema for the document routing LangGraph agent.

Every node reads from and writes to this TypedDict.
LangGraph's PostgresSaver serializes this to Postgres on each transition.
"""

from typing import TypedDict, Optional, Literal
from datetime import datetime


# Valid document types the classifier can assign
DocType = Literal[
    "invoice",
    "contract",
    "medical_record",
    "hr_form",
    "legal_notice",
    "compliance_report",
    "purchase_order",
    "other",
]

# Urgency levels that drive routing priority
UrgencyLevel = Literal["critical", "high", "normal", "low"]

# Department queues
Department = Literal["finance", "legal", "hr", "medical", "operations", "compliance"]

# Human decision
HumanDecision = Literal["approved", "rejected", "rerouted", "pending"]


class DocumentState(TypedDict):
    # --- Input ---
    document_id: str
    file_name: str
    file_path: str          # Path to uploaded file on disk
    raw_text: str           # Extracted text (post-OCR)
    uploaded_at: str        # ISO datetime string

    # --- Classifier output ---
    doc_type: Optional[DocType]
    urgency: Optional[UrgencyLevel]
    confidence: Optional[float]         # 0.0–1.0, classifier confidence
    classification_reasoning: Optional[str]

    # --- Extracted metadata ---
    parties: Optional[list[str]]        # Names/entities mentioned
    key_dates: Optional[list[str]]      # Dates found in document
    monetary_amounts: Optional[list[str]]
    summary: Optional[str]              # 2-sentence summary for reviewer

    # --- Routing ---
    assigned_department: Optional[Department]
    routing_reason: Optional[str]
    reviewer_id: Optional[str]          # Assigned human reviewer

    # --- Human checkpoint ---
    human_decision: Optional[HumanDecision]
    reviewer_notes: Optional[str]
    decision_at: Optional[str]          # ISO datetime string
    rerouted_to: Optional[Department]   # Only set if decision == "rerouted"

    # --- Post-approval ---
    downstream_action: Optional[str]    # e.g. "docusign_sent", "webhook_fired"
    action_result: Optional[dict]

    # --- Audit ---
    audit_trail: list[dict]             # Append-only list of state transitions
    error: Optional[str]                # Set if any node fails
    current_node: Optional[str]         # Which node is executing
