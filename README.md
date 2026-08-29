# Document Routing & Approval Agent

> **Agentic AI Portfolio Project** — LangGraph + Gemini + FastAPI + React  
> Difficulty: Advanced | Domain: Healthcare / Legal / Enterprise Ops  
> Target roles: AI Systems Engineer, Enterprise AI Engineer, Workflow Automation Lead

---

## What this builds

A production-grade agentic system that:
1. Accepts uploaded documents (PDF, DOCX, images via OCR)
2. Classifies document type and urgency using Gemini
3. Routes to the correct department queue via a LangGraph state machine
4. Presents a human-in-the-loop review UI (React dashboard)
5. On approval: triggers downstream APIs (DocuSign / webhook)
6. Writes a full audit trail to PostgreSQL for compliance



---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    INGESTION LAYER                       │
│  PDF/DOCX upload → OCR (Tesseract) → text extraction    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  LANGGRAPH STATE MACHINE                 │
│                                                          │
│  [classify] → [extract_metadata] → [route] →            │
│  [human_checkpoint] → [post_approval_action] →          │
│  [audit_log]                                             │
│                                                          │
│  Each node is a pure function. State is persisted        │
│  via PostgresSaver (LangGraph checkpointing).            │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
┌───────▼──────────┐         ┌────────────▼─────────┐
│  FastAPI backend │         │   PostgreSQL           │
│  REST + SSE      │         │   Documents table      │
│  /upload         │         │   Audit log table      │
│  /documents      │         │   (LangGraph state)    │
│  /approve        │         └──────────────────────-─┘
│  /reject         │
└───────┬──────────┘
        │
┌───────▼──────────┐
│  React Dashboard │
│  Upload UI       │
│  Review queue    │
│  Decision UI     │
│  Audit trail     │
└──────────────────┘
```

---

## Project structure

```
doc-routing-agent/
├── backend/
│   ├── agents/
│   │   ├── graph.py          # LangGraph state machine definition
│   │   ├── nodes.py          # All graph node functions
│   │   └── state.py          # Typed state schema (TypedDict)
│   ├── api/
│   │   ├── main.py           # FastAPI app + CORS
│   │   └── routes.py         # All REST endpoints
│   ├── models/
│   │   └── schemas.py        # Pydantic request/response schemas
│   ├── db/
│   │   ├── database.py       # SQLAlchemy engine + session
│   │   └── crud.py           # DB read/write helpers
│   └── utils/
│       ├── ocr.py            # PDF/image text extraction
│       └── notifiers.py      # Slack / webhook / DocuSign stubs
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── UploadZone.jsx
│       │   ├── DocumentCard.jsx
│       │   └── AuditLog.jsx
│       ├── pages/
│       │   ├── Queue.jsx
│       │   └── Dashboard.jsx
│       └── hooks/
│           └── useDocuments.js
├── tests/
│   ├── test_graph.py
│   └── test_api.py
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Key architectural decisions (explain in interviews)

### Why LangGraph over CrewAI here?
This workflow has **branching conditional logic** (high-urgency docs skip one review tier), **persistent state** (docs can sit in the human queue for hours/days), and **compliance requirements** (every state transition must be logged). LangGraph's directed graph with checkpointing handles all three natively. CrewAI's sequential crew model would require custom state hacks.

### Why a human checkpoint node, not just a webhook?
The LangGraph `interrupt_before` pattern lets the agent **pause mid-graph** and resume when a human acts. The alternative (webhook-only) loses graph state between the approval and the post-action step. With checkpointing, the full reasoning context is preserved through the human decision.

### Why PostgreSQL for state AND audit log?
LangGraph's `PostgresSaver` writes graph checkpoints to Postgres. Storing our audit log in the same DB means one consistent source of truth for compliance auditors — no stitching logs from separate systems.

---

## Setup

```bash
# 1. Clone and create virtualenv
python -m venv venv && source venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Set environment variables
cp .env.example .env
# Fill in: GEMINI_API_KEY, DATABASE_URL, DOCUSIGN_API_KEY (optional)

# 4. Start Postgres
docker-compose up -d db

# 5. Run migrations
python backend/db/database.py  # creates tables on first run

# 6. Start FastAPI
uvicorn backend.api.main:app --reload --port 8000

# 7. Start React frontend
cd frontend && npm install && npm run dev
```

---

## Deployment checklist

- [ ] Containerize with Docker (Dockerfile provided)
- [ ] Set `GEMINI_API_KEY` in environment
- [ ] Configure PostgreSQL with connection pooling (PgBouncer for prod)
- [ ] Set `MAX_FILE_SIZE_MB` (default: 10)
- [ ] Configure department routing rules in `config/routing_rules.yaml`
- [ ] Add real DocuSign credentials (currently stubbed)
- [ ] Set up LangSmith tracing: `LANGCHAIN_API_KEY` + `LANGCHAIN_TRACING_V2=true`
- [ ] Add authentication (JWT middleware stub in `api/main.py`)

---

## What to say in interviews

> "I built a LangGraph state machine with five nodes — classify, extract, route, human checkpoint, and post-approval action. The key design decision was using LangGraph's `interrupt_before` on the human node so the graph pauses mid-execution and resumes with full context after a reviewer acts. This is different from a simple webhook pattern because you preserve the entire agent reasoning state across the human latency window. Everything is persisted via PostgresSaver, which doubles as our compliance audit trail."
