import pytest

import db


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure escalations table is cleared before and after each test."""
    db.clear_all_escalation_tickets()
    yield
    db.clear_all_escalation_tickets()


def test_escalation_ticket_creation_and_retrieval():
    """Test creating an escalation ticket in SQLite and retrieving it."""
    ticket = db.create_escalation_ticket(
        learner_name="Priya",
        reason="Learner Frustration",
        summary="Learner felt overwhelmed during grammar exercise. Requested teacher review.",
        urgency="high",
    )

    assert ticket["reference_id"].startswith("ESC-")
    assert ticket["learner_name"] == "Priya"
    assert ticket["urgency"] == "high"
    assert ticket["status"] == "OPEN"

    # Retrieve all tickets from DB
    tickets = db.get_all_escalation_tickets()
    matching = [t for t in tickets if t["reference_id"] == ticket["reference_id"]]
    assert len(matching) == 1
    assert matching[0]["reason"] == "Learner Frustration"


def test_escalation_ticket_status_update():
    """Test updating escalation ticket status from OPEN to RESOLVED."""
    ticket = db.create_escalation_ticket(
        learner_name="Ramesh",
        reason="Teacher Review Requested",
        summary="Asked for human teacher to check pronunciation notes.",
        urgency="medium",
    )

    ref_id = ticket["reference_id"]
    updated = db.update_escalation_status(ref_id, "RESOLVED")
    assert updated is True

    tickets = db.get_all_escalation_tickets()
    matching = [t for t in tickets if t["reference_id"] == ref_id]
    assert matching[0]["status"] == "RESOLVED"
