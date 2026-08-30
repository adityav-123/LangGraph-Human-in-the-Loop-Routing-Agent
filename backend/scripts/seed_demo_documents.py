import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db.database import SessionLocal, create_tables
from backend.db import crud

DEMO_DIR = ROOT / "demo_uploads"
DEMO_DIR.mkdir(exist_ok=True)


def iso_minutes_ago(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


DEMO_DOCS = [
    {
        "file_name": "invoice_acme_q3.txt",
        "raw_text": "Invoice #4312 Vendor: Acme Corp Amount Due: $12,450 Payment due: 2026-09-15",
        "uploaded_at": iso_minutes_ago(10),
        "state": {
            "processing_status": "awaiting_review",
            "status_updated_at": iso_minutes_ago(8),
            "doc_type": "invoice",
            "urgency": "normal",
            "confidence": 0.93,
            "classification_reasoning": "Invoice keywords and payment terms matched finance documents.",
            "parties": ["Acme Corp"],
            "key_dates": ["2026-09-15"],
            "monetary_amounts": ["$12,450"],
            "summary": "Quarterly vendor invoice awaiting finance approval.",
            "assigned_department": "finance",
            "reviewer_id": "reviewer-finance-001",
            "routing_reason": "Invoice documents default to finance.",
            "human_decision": "pending",
            "audit_trail": [],
            "current_node": "human_checkpoint",
            "error": None,
        },
    },
    {
        "file_name": "employment_onboarding_packet.txt",
        "raw_text": "Employee benefits enrollment W-4 direct deposit new hire onboarding packet",
        "uploaded_at": iso_minutes_ago(18),
        "state": {
            "processing_status": "awaiting_review",
            "status_updated_at": iso_minutes_ago(16),
            "doc_type": "hr_form",
            "urgency": "normal",
            "confidence": 0.91,
            "classification_reasoning": "Benefits and onboarding language indicates HR paperwork.",
            "parties": ["Jordan Lee"],
            "key_dates": ["2026-08-30"],
            "monetary_amounts": [],
            "summary": "New hire onboarding packet waiting in the HR queue.",
            "assigned_department": "hr",
            "reviewer_id": "reviewer-hr-001",
            "routing_reason": "Employee forms route to HR.",
            "human_decision": "pending",
            "audit_trail": [],
            "current_node": "human_checkpoint",
            "error": None,
        },
    },
    {
        "file_name": "patient_transfer_notice.txt",
        "raw_text": "Patient transfer request, diagnosis summary, urgent treatment continuation required.",
        "uploaded_at": iso_minutes_ago(42),
        "state": {
            "processing_status": "awaiting_review",
            "status_updated_at": iso_minutes_ago(41),
            "doc_type": "medical_record",
            "urgency": "critical",
            "confidence": 0.9,
            "classification_reasoning": "Patient treatment language suggests a time-sensitive medical record.",
            "parties": ["City General Hospital"],
            "key_dates": ["2026-08-30"],
            "monetary_amounts": [],
            "summary": "Urgent medical transfer notice needing immediate clinical review.",
            "assigned_department": "medical",
            "reviewer_id": "senior-reviewer-medical-001",
            "routing_reason": "Critical medical records route to senior medical review.",
            "human_decision": "pending",
            "audit_trail": [],
            "current_node": "human_checkpoint",
            "error": None,
        },
    },
    {
        "file_name": "regulatory_breach_notice.txt",
        "raw_text": "Compliance violation notice. Response required within 24 hours to avoid penalties.",
        "uploaded_at": iso_minutes_ago(65),
        "state": {
            "processing_status": "awaiting_review",
            "status_updated_at": iso_minutes_ago(63),
            "doc_type": "compliance_report",
            "urgency": "critical",
            "confidence": 0.95,
            "classification_reasoning": "Regulatory violation and 24-hour deadline indicate critical compliance handling.",
            "parties": ["State Regulator"],
            "key_dates": ["within 24 hours"],
            "monetary_amounts": [],
            "summary": "Critical compliance notice waiting for immediate review.",
            "assigned_department": "compliance",
            "reviewer_id": "senior-reviewer-compliance-001",
            "routing_reason": "Compliance violations route to compliance with high priority.",
            "human_decision": "pending",
            "audit_trail": [],
            "current_node": "human_checkpoint",
            "error": None,
        },
    },
    {
        "file_name": "msa_signature_request.txt",
        "raw_text": "Master service agreement pending signature before kickoff on 2026-09-02.",
        "uploaded_at": iso_minutes_ago(95),
        "state": {
            "processing_status": "completed",
            "status_updated_at": iso_minutes_ago(80),
            "doc_type": "contract",
            "urgency": "high",
            "confidence": 0.92,
            "classification_reasoning": "Agreement and signature terms map to contract handling.",
            "parties": ["Northwind", "Apex Systems"],
            "key_dates": ["2026-09-02"],
            "monetary_amounts": [],
            "summary": "Service agreement was approved and sent for signature.",
            "assigned_department": "legal",
            "reviewer_id": "reviewer-legal-001",
            "routing_reason": "Contracts route to legal.",
            "human_decision": "approved",
            "decision_at": iso_minutes_ago(82),
            "downstream_action": "docusign_envelope_sent",
            "action_result": {"envelope_id": "env_demo1234", "status": "sent"},
            "audit_trail": [],
            "current_node": "audit_log",
            "error": None,
        },
    },
    {
        "file_name": "vendor_packet_scan.txt",
        "raw_text": "Scanned vendor packet with low OCR confidence",
        "uploaded_at": iso_minutes_ago(15),
        "state": {
            "processing_status": "failed",
            "status_updated_at": iso_minutes_ago(14),
            "doc_type": None,
            "urgency": None,
            "confidence": None,
            "classification_reasoning": None,
            "parties": [],
            "key_dates": [],
            "monetary_amounts": [],
            "summary": None,
            "assigned_department": "operations",
            "reviewer_id": None,
            "routing_reason": None,
            "human_decision": "pending",
            "audit_trail": [],
            "current_node": "classify",
            "error": "OCR output was too noisy to classify. Retry with a clearer scan.",
        },
    },
]


def seed_demo_documents():
    create_tables()
    db = SessionLocal()
    try:
        db.query(crud.Document).filter(crud.Document.file_name.in_([doc["file_name"] for doc in DEMO_DOCS])).delete(synchronize_session=False)
        db.commit()

        for demo in DEMO_DOCS:
            file_path = DEMO_DIR / demo["file_name"]
            file_path.write_text(demo["raw_text"], encoding="utf-8")
            state = {
                "document_id": "demo-placeholder",
                "file_name": demo["file_name"],
                "file_path": str(file_path),
                "raw_text": demo["raw_text"],
                "uploaded_at": demo["uploaded_at"],
                "rerouted_to": None,
                **demo["state"],
            }
            crud.create_demo_document(
                db,
                file_name=demo["file_name"],
                file_path=str(file_path),
                raw_text=demo["raw_text"],
                state=state,
            )
            print(f"Seeded demo document: {demo['file_name']}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_documents()
