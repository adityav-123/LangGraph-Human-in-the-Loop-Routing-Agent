"""
Unit tests for LangGraph nodes.

Run: pytest tests/test_graph.py -v
These tests mock the Gemini client so they run without credentials.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from backend.agents.nodes import classify, extract_metadata, route, route_after_human
from backend.agents.state import DocumentState


def make_state(**overrides) -> DocumentState:
    base: DocumentState = {
        "document_id":   "test-123",
        "file_name":     "invoice.pdf",
        "file_path":     "/tmp/invoice.pdf",
        "raw_text":      "Invoice #1234 from Acme Corp. Amount: $5,000. Due: 2026-09-01.",
        "uploaded_at":   datetime.now(timezone.utc).isoformat(),
        "doc_type":               None,
        "urgency":                None,
        "confidence":             None,
        "classification_reasoning": None,
        "parties":                None,
        "key_dates":              None,
        "monetary_amounts":       None,
        "summary":                None,
        "assigned_department":    None,
        "reviewer_id":            None,
        "routing_reason":         None,
        "human_decision":         None,
        "reviewer_notes":         None,
        "decision_at":            None,
        "rerouted_to":            None,
        "downstream_action":      None,
        "action_result":          None,
        "audit_trail":            [],
        "error":                  None,
        "current_node":           None,
    }
    return {**base, **overrides}


def mock_gemini_response(text: str):
    """Build a minimal mock Gemini response."""
    response = MagicMock()
    response.text = text
    return response


# ---------------------------------------------------------------------------
# classify node
# ---------------------------------------------------------------------------

class TestClassify:

    @patch("backend.agents.nodes.client")
    def test_classifies_invoice(self, mock_client):
        mock_client.models.generate_content.return_value = mock_gemini_response(
            '{"doc_type": "invoice", "urgency": "normal", "confidence": 0.95, "reasoning": "Standard invoice format."}'
        )
        state  = make_state()
        result = classify(state)

        assert result["doc_type"]  == "invoice"
        assert result["urgency"]   == "normal"
        assert result["confidence"] == 0.95
        assert len(result["audit_trail"]) == 1
        assert result["audit_trail"][0]["event"] == "classified"

    @patch("backend.agents.nodes.client")
    def test_handles_parse_error(self, mock_client):
        mock_client.models.generate_content.return_value = mock_gemini_response("not valid json at all")
        state  = make_state()
        result = classify(state)

        # Should fall back gracefully
        assert result["doc_type"]  == "other"
        assert result["urgency"]   == "normal"
        assert result["confidence"] == 0.3

    @patch("backend.agents.nodes.client")
    def test_classifies_critical_legal(self, mock_client):
        mock_client.models.generate_content.return_value = mock_gemini_response(
            '{"doc_type": "legal_notice", "urgency": "critical", "confidence": 0.88, "reasoning": "Court deadline."}'
        )
        state  = make_state(raw_text="Court order: response required within 24 hours.")
        result = classify(state)

        assert result["doc_type"] == "legal_notice"
        assert result["urgency"]  == "critical"


# ---------------------------------------------------------------------------
# route node
# ---------------------------------------------------------------------------

class TestRoute:

    def test_invoice_routes_to_finance(self):
        state  = make_state(doc_type="invoice", urgency="normal")
        result = route(state)

        assert result["assigned_department"] == "finance"
        assert result["human_decision"]      == "pending"
        assert "finance" in result["reviewer_id"]

    def test_contract_routes_to_legal(self):
        state  = make_state(doc_type="contract", urgency="high")
        result = route(state)

        assert result["assigned_department"] == "legal"

    def test_critical_gets_senior_reviewer(self):
        state  = make_state(doc_type="invoice", urgency="critical")
        result = route(state)

        assert "senior" in result["reviewer_id"]

    def test_unknown_type_routes_to_operations(self):
        state  = make_state(doc_type="other", urgency="low")
        result = route(state)

        assert result["assigned_department"] == "operations"


# ---------------------------------------------------------------------------
# route_after_human conditional edge
# ---------------------------------------------------------------------------

class TestRouteAfterHuman:

    def test_approved_goes_to_post_action(self):
        state = make_state(human_decision="approved")
        assert route_after_human(state) == "post_approval_action"

    def test_rejected_goes_to_post_action(self):
        state = make_state(human_decision="rejected")
        assert route_after_human(state) == "post_approval_action"

    def test_rerouted_goes_to_post_action(self):
        state = make_state(human_decision="rerouted")
        assert route_after_human(state) == "post_approval_action"

    def test_pending_falls_back_to_audit(self):
        state = make_state(human_decision="pending")
        assert route_after_human(state) == "audit_log"


# ---------------------------------------------------------------------------
# extract_metadata node
# ---------------------------------------------------------------------------

class TestExtractMetadata:

    @patch("backend.agents.nodes.client")
    def test_extracts_parties_and_amounts(self, mock_client):
        mock_client.models.generate_content.return_value = mock_gemini_response(
            '{"parties": ["Acme Corp", "BuyerCo"], "key_dates": ["2026-09-01"], '
            '"monetary_amounts": ["$5,000"], "summary": "Invoice from Acme. Payment due Sept 1."}'
        )
        state  = make_state(doc_type="invoice")
        result = extract_metadata(state)

        assert "Acme Corp" in result["parties"]
        assert "$5,000"    in result["monetary_amounts"]
        assert result["summary"] != ""

    @patch("backend.agents.nodes.client")
    def test_handles_empty_result(self, mock_client):
        mock_client.models.generate_content.return_value = mock_gemini_response(
            '{"parties": [], "key_dates": [], "monetary_amounts": [], "summary": ""}'
        )
        state  = make_state()
        result = extract_metadata(state)

        assert result["parties"]          == []
        assert result["monetary_amounts"] == []
