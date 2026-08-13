import pytest

import db


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure call_logs table is cleared before and after each test."""
    db.clear_all_call_logs()
    yield
    db.clear_all_call_logs()


def test_log_call_session_success_and_failure():
    """Test logging successful and failed calls and verifying outcomes."""
    # Log a successful call (exercises > 0)
    success_call = db.log_call_session(
        call_id="CALL-TEST-SUCCESS-01",
        participant_name="Ramesh",
        channel="Web Browser",
        duration_seconds=45,
        exercises_completed=2,
    )
    assert success_call["call_id"] == "CALL-TEST-SUCCESS-01"
    assert success_call["outcome"] == "SUCCESS"
    assert success_call["exercises_completed"] == 2

    # Log a failed call (exercises == 0)
    fail_call = db.log_call_session(
        call_id="CALL-TEST-FAIL-01",
        participant_name="Unknown",
        channel="Web Browser",
        duration_seconds=5,
        exercises_completed=0,
        failure_reason="Early Disconnect / User Hangup",
    )
    assert fail_call["call_id"] == "CALL-TEST-FAIL-01"
    assert fail_call["outcome"] == "FAILED"
    assert fail_call["failure_reason"] == "Early Disconnect / User Hangup"


def test_get_call_analytics_aggregations():
    """Test that get_call_analytics computes accurate totals and percentages."""
    db.log_call_session(call_id="CALL-TEST-01", exercises_completed=2)
    db.log_call_session(call_id="CALL-TEST-02", exercises_completed=0)

    analytics = db.get_call_analytics()

    assert "total_calls" in analytics
    assert "successful_calls" in analytics
    assert "failed_calls" in analytics
    assert "success_rate" in analytics
    assert "average_duration_seconds" in analytics

    assert analytics["total_calls"] == 2
    assert analytics["successful_calls"] == 1
    assert analytics["failed_calls"] == 1
    assert analytics["success_rate"] == 50.0


def test_get_recent_call_logs():
    """Test retrieving recent call logs from SQLite."""
    db.log_call_session(call_id="CALL-TEST-01", exercises_completed=2)
    db.log_call_session(call_id="CALL-TEST-02", exercises_completed=0)

    logs = db.get_recent_call_logs(limit=5)
    assert isinstance(logs, list)
    assert len(logs) == 2
    for log in logs:
        assert "call_id" in log
        assert "outcome" in log
        assert log["outcome"] in ["SUCCESS", "FAILED"]
