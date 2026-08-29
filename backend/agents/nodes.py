"""
LangGraph node functions for document routing.

Each function signature: (state: DocumentState) -> dict
The dict contains only the keys being updated — LangGraph merges it into state.

Node order:
  classify → extract_metadata → route → human_checkpoint → post_approval → audit_log
"""

import json
import uuid
from datetime import datetime, timezone
from google import genai
from google.genai import types

from .state import DocumentState, Department

client = genai.Client()

# ---------------------------------------------------------------------------
# Routing rules: doc_type → default department
# Override with a YAML config in production.
# ---------------------------------------------------------------------------
ROUTING_RULES: dict[str, Department] = {
    "invoice":           "finance",
    "purchase_order":    "finance",
    "contract":          "legal",
    "legal_notice":      "legal",
    "medical_record":    "medical",
    "hr_form":           "hr",
    "compliance_report": "compliance",
    "other":             "operations",
}

URGENCY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_audit(state: DocumentState, event: str, data: dict = {}) -> list[dict]:
    """Return a new audit trail with one entry appended."""
    trail = list(state.get("audit_trail", []))
    trail.append({
        "event":    event,
        "node":     state.get("current_node", "unknown"),
        "at":       _now(),
        "data":     data,
    })
    return trail


# ---------------------------------------------------------------------------
# Node 1: classify
# ---------------------------------------------------------------------------
def classify(state: DocumentState) -> dict:
    """
    Uses Gemini to classify document type and urgency.
    Returns classification + confidence + short reasoning.
    Falls back to ("other", "normal") if parsing fails.
    """
    text_preview = state["raw_text"][:4000]  # keep token cost manageable

    prompt = f"""You are a document classification system. Analyze the following document text and return a JSON object.

Document text:
<document>
{text_preview}
</document>

Return ONLY valid JSON with these exact keys:
{{
  "doc_type": one of: invoice | contract | medical_record | hr_form | legal_notice | compliance_report | purchase_order | other,
  "urgency": one of: critical | high | normal | low,
  "confidence": float between 0.0 and 1.0,
  "reasoning": "one sentence explaining your classification"
}}

Urgency guide:
- critical: legal deadlines within 48h, medical emergencies, regulatory violations
- high: financial documents over $50k, contracts pending signature
- normal: routine invoices, standard HR forms
- low: informational documents, no action required"""

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()
    try:
        result = json.loads(raw)
        doc_type   = result.get("doc_type", "other")
        urgency    = result.get("urgency", "normal")
        confidence = float(result.get("confidence", 0.5))
        reasoning  = result.get("reasoning", "")
    except (json.JSONDecodeError, KeyError, ValueError):
        doc_type, urgency, confidence, reasoning = "other", "normal", 0.3, "Parse error — defaulted"

    audit = _append_audit(
        {**state, "current_node": "classify"},
        "classified",
        {"doc_type": doc_type, "urgency": urgency, "confidence": confidence},
    )

    return {
        "current_node":               "classify",
        "doc_type":                   doc_type,
        "urgency":                    urgency,
        "confidence":                 confidence,
        "classification_reasoning":   reasoning,
        "audit_trail":                audit,
    }


# ---------------------------------------------------------------------------
# Node 2: extract_metadata
# ---------------------------------------------------------------------------
def extract_metadata(state: DocumentState) -> dict:
    """
    Extracts structured metadata: parties, dates, amounts, and a 2-sentence summary.
    This gives the human reviewer enough context without reading the full doc.
    """
    text_preview = state["raw_text"][:5000]

    prompt = f"""Extract structured metadata from this {state.get("doc_type", "document")}.

Document:
<document>
{text_preview}
</document>

Return ONLY valid JSON:
{{
  "parties":           ["list of named entities, companies, or people"],
  "key_dates":         ["dates found, in original format"],
  "monetary_amounts":  ["dollar/currency amounts found"],
  "summary":           "2 sentences: what this document is and what action is required"
}}

If a field has no data, return an empty list or empty string."""

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()
    try:
        meta = json.loads(raw)
        parties    = meta.get("parties", [])
        key_dates  = meta.get("key_dates", [])
        amounts    = meta.get("monetary_amounts", [])
        summary    = meta.get("summary", "")
    except (json.JSONDecodeError, KeyError):
        parties, key_dates, amounts, summary = [], [], [], "Could not extract metadata."

    audit = _append_audit(
        {**state, "current_node": "extract_metadata"},
        "metadata_extracted",
        {"parties_found": len(parties), "amounts_found": len(amounts)},
    )

    return {
        "current_node":    "extract_metadata",
        "parties":         parties,
        "key_dates":       key_dates,
        "monetary_amounts": amounts,
        "summary":         summary,
        "audit_trail":     audit,
    }


# ---------------------------------------------------------------------------
# Node 3: route
# ---------------------------------------------------------------------------
def route(state: DocumentState) -> dict:
    """
    Applies routing rules to assign a department and reviewer.
    Critical urgency documents get a senior reviewer assignment stub.
    """
    doc_type   = state.get("doc_type", "other")
    urgency    = state.get("urgency", "normal")
    department = ROUTING_RULES.get(doc_type, "operations")

    # In production, pull from a real reviewer assignment service
    reviewer_map = {
        "finance":    "reviewer-finance-001",
        "legal":      "reviewer-legal-001",
        "medical":    "reviewer-medical-001",
        "hr":         "reviewer-hr-001",
        "compliance": "reviewer-compliance-001",
        "operations": "reviewer-ops-001",
    }

    # Critical urgency: escalate to senior reviewer
    if urgency == "critical":
        reviewer_id = f"senior-{reviewer_map.get(department, 'reviewer-ops-001')}"
    else:
        reviewer_id = reviewer_map.get(department, "reviewer-ops-001")

    routing_reason = (
        f"Doc type '{doc_type}' maps to {department} queue. "
        f"Urgency '{urgency}' → assigned to {reviewer_id}."
    )

    audit = _append_audit(
        {**state, "current_node": "route"},
        "routed",
        {"department": department, "reviewer_id": reviewer_id},
    )

    return {
        "current_node":       "route",
        "assigned_department": department,
        "reviewer_id":        reviewer_id,
        "routing_reason":     routing_reason,
        "human_decision":     "pending",
        "audit_trail":        audit,
    }


# ---------------------------------------------------------------------------
# Node 4: human_checkpoint
# ---------------------------------------------------------------------------
def human_checkpoint(state: DocumentState) -> dict:
    """
    This node is configured with interrupt_before=["human_checkpoint"] in graph.py.
    LangGraph pauses execution here. The FastAPI /approve and /reject endpoints
    resume the graph by updating state and calling graph.invoke() again.

    When the graph resumes, this node validates the human decision is present.
    """
    decision = state.get("human_decision", "pending")

    if decision == "pending":
        # Graph should have been interrupted before reaching this node's body.
        # If we reach here without a decision, something is wrong — log and halt.
        return {
            "current_node": "human_checkpoint",
            "error": "Graph reached human_checkpoint body with no decision set.",
        }

    audit = _append_audit(
        {**state, "current_node": "human_checkpoint"},
        f"human_decision_{decision}",
        {
            "decision":       decision,
            "reviewer_notes": state.get("reviewer_notes", ""),
            "rerouted_to":    state.get("rerouted_to"),
        },
    )

    return {
        "current_node": "human_checkpoint",
        "decision_at":  _now(),
        "audit_trail":  audit,
    }


# ---------------------------------------------------------------------------
# Node 5: post_approval_action
# ---------------------------------------------------------------------------
def post_approval_action(state: DocumentState) -> dict:
    """
    Fires downstream integrations based on doc_type and decision.
    Currently stubbed — swap in real DocuSign / webhook clients.
    """
    decision  = state.get("human_decision")
    doc_type  = state.get("doc_type")
    dept      = state.get("assigned_department")

    if decision == "rejected":
        action     = "rejected_archived"
        action_res = {"archived": True, "reason": state.get("reviewer_notes", "")}

    elif decision == "rerouted":
        new_dept   = state.get("rerouted_to", "operations")
        action     = f"rerouted_to_{new_dept}"
        action_res = {"new_department": new_dept}

    elif doc_type in ("contract", "legal_notice"):
        # Stub: would call DocuSign API here
        action     = "docusign_envelope_sent"
        action_res = {"envelope_id": f"env_{uuid.uuid4().hex[:8]}", "status": "sent"}

    else:
        # Generic: fire a webhook to the department's downstream system
        action     = "department_webhook_fired"
        action_res = {"department": dept, "status": "queued"}

    audit = _append_audit(
        {**state, "current_node": "post_approval_action"},
        "downstream_action",
        {"action": action, "result": action_res},
    )

    return {
        "current_node":    "post_approval_action",
        "downstream_action": action,
        "action_result":   action_res,
        "audit_trail":     audit,
    }


# ---------------------------------------------------------------------------
# Node 6: audit_log
# ---------------------------------------------------------------------------
def audit_log(state: DocumentState) -> dict:
    """
    Terminal node. Writes final audit record to DB.
    In production, also emits to a SIEM or compliance platform.
    """
    # The db.crud module writes this on each state transition via the API layer,
    # but we do a final flush here to mark the document as "complete".
    audit = _append_audit(
        {**state, "current_node": "audit_log"},
        "workflow_complete",
        {
            "doc_type":   state.get("doc_type"),
            "decision":   state.get("human_decision"),
            "department": state.get("assigned_department"),
            "action":     state.get("downstream_action"),
        },
    )

    return {
        "current_node": "audit_log",
        "audit_trail":  audit,
    }


# ---------------------------------------------------------------------------
# Conditional edge: after human_checkpoint, branch on decision
# ---------------------------------------------------------------------------
def route_after_human(state: DocumentState) -> str:
    """
    LangGraph conditional edge function.
    Returns the name of the next node based on human decision.
    """
    decision = state.get("human_decision", "pending")

    if decision in ("approved", "rejected", "rerouted"):
        return "post_approval_action"

    # Still pending — shouldn't happen after interrupt resumes, but safe fallback
    return "audit_log"
