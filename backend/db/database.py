"""
Database setup.

Uses SQLAlchemy for the documents table (our business data).
LangGraph manages its own checkpoint tables via PostgresSaver separately.

Run this file directly to initialize tables:
    python backend/db/database.py
"""

import os
from sqlalchemy import (
    create_engine, Column, String, Float, Text, JSON, inspect, text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/docrouting")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'admin' or department name (e.g., 'legal', 'finance')


class Document(Base):
    __tablename__ = "documents"

    document_id          = Column(String, primary_key=True, index=True)
    file_name            = Column(String, nullable=False)
    file_path            = Column(String, nullable=False)
    raw_text             = Column(Text, default="")
    uploaded_at          = Column(String, nullable=False)
    processing_status    = Column(String, nullable=False, default="uploaded")
    status_updated_at    = Column(String, nullable=False)

    # Classification
    doc_type             = Column(String, nullable=True)
    urgency              = Column(String, nullable=True)
    confidence           = Column(Float, nullable=True)
    classification_reasoning = Column(Text, nullable=True)

    # Metadata extraction
    parties              = Column(JSON, default=list)
    key_dates            = Column(JSON, default=list)
    monetary_amounts     = Column(JSON, default=list)
    summary              = Column(Text, nullable=True)

    # Routing
    assigned_department  = Column(String, nullable=True)
    reviewer_id          = Column(String, nullable=True)
    routing_reason       = Column(Text, nullable=True)

    # Human decision
    human_decision       = Column(String, default="pending")
    reviewer_notes       = Column(Text, nullable=True)
    decision_at          = Column(String, nullable=True)
    rerouted_to          = Column(String, nullable=True)

    # Post-approval
    downstream_action    = Column(String, nullable=True)
    action_result        = Column(JSON, nullable=True)

    # Audit
    audit_trail          = Column(JSON, default=list)
    error                = Column(Text, nullable=True)
    current_node         = Column(String, nullable=True)


def get_db():
    """FastAPI dependency: yields a DB session, closes it after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
    _ensure_documents_columns()
    print("Tables created.")


def _ensure_documents_columns():
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("documents")}
    alter_statements = []

    if "processing_status" not in columns:
        alter_statements.append(
            "ALTER TABLE documents ADD COLUMN processing_status VARCHAR NOT NULL DEFAULT 'uploaded'"
        )
    if "status_updated_at" not in columns:
        now = datetime.now(timezone.utc).isoformat()
        alter_statements.append(
            f"ALTER TABLE documents ADD COLUMN status_updated_at VARCHAR NOT NULL DEFAULT '{now}'"
        )

    with engine.begin() as conn:
        for statement in alter_statements:
            conn.execute(text(statement))


if __name__ == "__main__":
    create_tables()
