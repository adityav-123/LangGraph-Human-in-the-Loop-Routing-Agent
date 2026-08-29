"""
LangGraph state machine definition.

This file wires together all nodes and edges into a compiled graph.
The graph uses PostgresSaver for checkpointing — this is what enables:
  1. The human-in-the-loop pause (interrupt_before)
  2. Full state persistence across the hours/days a doc sits in the queue
  3. Compliance audit trail (every state transition is stored)

Usage:
    from backend.agents.graph import get_graph

    graph = get_graph(conn)

    # Start the workflow (will pause at human_checkpoint automatically)
    config = {"configurable": {"thread_id": document_id}}
    state  = graph.invoke(initial_state, config)

    # Later: resume after a human decision
    graph.invoke(None, config)  # resumes from checkpoint
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from .state import DocumentState
from .nodes import (
    classify,
    extract_metadata,
    route,
    human_checkpoint,
    post_approval_action,
    audit_log,
    route_after_human,
)


def build_graph(checkpointer: PostgresSaver) -> StateGraph:
    """
    Builds and compiles the document routing graph.

    Graph flow:
        classify
            ↓
        extract_metadata
            ↓
        route
            ↓
        [PAUSE] human_checkpoint  ← interrupt_before here
            ↓
        post_approval_action  (conditional on decision)
            ↓
        audit_log
            ↓
        END

    The interrupt_before on human_checkpoint means the graph saves state
    and exits cleanly after route(). When the FastAPI /approve or /reject
    endpoint calls graph.invoke(None, config), LangGraph resumes from the
    checkpoint, runs human_checkpoint with the updated state, then continues.
    """
    workflow = StateGraph(DocumentState)

    # --- Add nodes ---
    workflow.add_node("classify",             classify)
    workflow.add_node("extract_metadata",     extract_metadata)
    workflow.add_node("route",                route)
    workflow.add_node("human_checkpoint",     human_checkpoint)
    workflow.add_node("post_approval_action", post_approval_action)
    workflow.add_node("audit_log",            audit_log)

    # --- Add edges ---
    workflow.set_entry_point("classify")
    workflow.add_edge("classify",         "extract_metadata")
    workflow.add_edge("extract_metadata", "route")
    workflow.add_edge("route",            "human_checkpoint")

    # Conditional edge: after human_checkpoint, branch on decision
    workflow.add_conditional_edges(
        "human_checkpoint",
        route_after_human,
        {
            "post_approval_action": "post_approval_action",
            "audit_log":            "audit_log",
        },
    )

    workflow.add_edge("post_approval_action", "audit_log")
    workflow.add_edge("audit_log",            END)

    # Compile with checkpointer + interrupt before the human node
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_checkpoint"],
    )


# ---------------------------------------------------------------------------
# Singleton helper — call once at app startup
# ---------------------------------------------------------------------------
_graph_instance = None


def get_graph(db_conn) -> StateGraph:
    """
    Returns a compiled graph with a PostgresSaver checkpointer.
    Call this at FastAPI startup with a live DB connection.

    Example:
        from psycopg import Connection
        conn = Connection.connect(DATABASE_URL)
        graph = get_graph(conn)
    """
    global _graph_instance
    if _graph_instance is None:
        checkpointer    = PostgresSaver(db_conn)
        checkpointer.setup()          # creates LangGraph checkpoint tables if not exist
        _graph_instance = build_graph(checkpointer)
    return _graph_instance
