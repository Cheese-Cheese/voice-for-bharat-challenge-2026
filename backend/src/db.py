import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("agent.db")

DB_DIR = Path(__file__).parent.parent / "db"
DB_PATH = DB_DIR / "memory.sqlite"


def get_connection() -> sqlite3.Connection:
    """Get a SQLite database connection, ensuring the db directory exists."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the SQLite database schema for storing caller memory profiles and human escalation tickets."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                language_preference TEXT DEFAULT 'English',
                current_level TEXT DEFAULT 'Beginner',
                topics_covered TEXT DEFAULT '',
                common_mistakes TEXT DEFAULT '',
                consent_given INTEGER DEFAULT 1,
                last_interaction TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS escalations (
                reference_id TEXT PRIMARY KEY,
                learner_name TEXT NOT NULL,
                reason TEXT NOT NULL,
                summary TEXT NOT NULL,
                urgency TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'OPEN',
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS call_logs (
                call_id TEXT PRIMARY KEY,
                participant_name TEXT DEFAULT 'Learner',
                channel TEXT DEFAULT 'Web Browser',
                duration_seconds INTEGER DEFAULT 0,
                exercises_completed INTEGER DEFAULT 0,
                outcome TEXT NOT NULL,
                failure_reason TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def get_all_user_profiles() -> list[dict[str, Any]]:
    """Retrieve a list of all saved user memory profiles in SQLite."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY last_interaction DESC")
        rows = cursor.fetchall()
        return [
            {
                "user_id": row["user_id"],
                "name": row["name"],
                "language_preference": row["language_preference"],
                "facts": {
                    "current_level": row["current_level"],
                    "topics_covered": row["topics_covered"],
                    "common_mistakes": row["common_mistakes"],
                },
                "consent_given": bool(row["consent_given"]),
                "last_interaction": row["last_interaction"],
            }
            for row in rows
        ]


def get_user_profile(user_id: str = "default_user") -> Optional[dict[str, Any]]:
    """Retrieve a caller's stored memory profile from SQLite by user_id."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "user_id": row["user_id"],
            "name": row["name"],
            "language_preference": row["language_preference"],
            "facts": {
                "current_level": row["current_level"],
                "topics_covered": row["topics_covered"],
                "common_mistakes": row["common_mistakes"],
            },
            "consent_given": bool(row["consent_given"]),
            "last_interaction": row["last_interaction"],
        }


def get_user_profile_by_name_or_id(
    name: str = "", user_id: str = ""
) -> Optional[dict[str, Any]]:
    """Retrieve a caller's stored memory profile by name (case-insensitive) or user_id."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        if name:
            cursor.execute(
                "SELECT * FROM users WHERE LOWER(name) = LOWER(?)", (name.strip(),)
            )
        elif user_id:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        else:
            cursor.execute("SELECT * FROM users ORDER BY last_interaction DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "user_id": row["user_id"],
            "name": row["name"],
            "language_preference": row["language_preference"],
            "facts": {
                "current_level": row["current_level"],
                "topics_covered": row["topics_covered"],
                "common_mistakes": row["common_mistakes"],
            },
            "consent_given": bool(row["consent_given"]),
            "last_interaction": row["last_interaction"],
        }


def save_user_profile(
    name: str,
    user_id: str = "",
    language_preference: str = "English",
    current_level: str = "Beginner",
    topics_covered: str = "",
    common_mistakes: str = "",
    consent_given: bool = True,
) -> dict[str, Any]:
    """Save or update a caller's memory profile in SQLite."""
    init_db()
    if not user_id:
        user_id = f"user_{name.strip().lower()}"
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (
                user_id, name, language_preference, current_level,
                topics_covered, common_mistakes, consent_given, last_interaction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                language_preference = excluded.language_preference,
                current_level = excluded.current_level,
                topics_covered = excluded.topics_covered,
                common_mistakes = excluded.common_mistakes,
                consent_given = excluded.consent_given,
                last_interaction = excluded.last_interaction
            """,
            (
                user_id,
                name,
                language_preference,
                current_level,
                topics_covered,
                common_mistakes,
                1 if consent_given else 0,
                now_iso,
            ),
        )
        conn.commit()

    return {
        "user_id": user_id,
        "name": name,
        "language_preference": language_preference,
        "facts": {
            "current_level": current_level,
            "topics_covered": topics_covered,
            "common_mistakes": common_mistakes,
        },
        "consent_given": consent_given,
        "last_interaction": now_iso,
    }


def delete_user_profile(name: str = "", user_id: str = "") -> bool:
    """Delete a caller's memory profile from SQLite by name or user_id ('forget me' tool)."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        if name:
            cursor.execute(
                "SELECT user_id FROM users WHERE LOWER(name) = LOWER(?)",
                (name.strip(),),
            )
            row = cursor.fetchone()
            if row:
                user_id = row["user_id"]
        if not user_id:
            cursor.execute("DELETE FROM users")
        else:
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0


def create_escalation_ticket(
    learner_name: str,
    reason: str,
    summary: str,
    urgency: str = "medium",
) -> dict[str, Any]:
    """Create a new human escalation support ticket in SQLite with a unique reference ID."""
    init_db()
    import uuid

    ref_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()
    urgency = urgency.lower() if urgency else "medium"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO escalations (
                reference_id, learner_name, reason, summary, urgency, status, created_at
            ) VALUES (?, ?, ?, ?, ?, 'OPEN', ?)
            """,
            (ref_id, learner_name, reason, summary, urgency, now_iso),
        )
        conn.commit()

    return {
        "reference_id": ref_id,
        "learner_name": learner_name,
        "reason": reason,
        "summary": summary,
        "urgency": urgency,
        "status": "OPEN",
        "created_at": now_iso,
    }


def get_all_escalation_tickets() -> list[dict[str, Any]]:
    """Retrieve all human teacher escalation tickets from SQLite."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM escalations ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [
            {
                "reference_id": row["reference_id"],
                "learner_name": row["learner_name"],
                "reason": row["reason"],
                "summary": row["summary"],
                "urgency": row["urgency"],
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]


def update_escalation_status(reference_id: str, status: str = "RESOLVED") -> bool:
    """Update the status of an escalation ticket in SQLite (e.g., OPEN -> RESOLVED)."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE escalations SET status = ? WHERE reference_id = ?",
            (status.upper(), reference_id.strip()),
        )
        conn.commit()
        return cursor.rowcount > 0


def log_call_session(
    call_id: str = "",
    participant_name: str = "Learner",
    channel: str = "Web Browser",
    duration_seconds: int = 0,
    exercises_completed: int = 0,
    failure_reason: str = "",
) -> dict[str, Any]:
    """Log the outcome of a voice agent call session into SQLite.

    A call is considered SUCCESS if exercises_completed > 0, otherwise FAILED.
    """
    init_db()
    import uuid

    if not call_id:
        call_id = f"CALL-{uuid.uuid4().hex[:6].upper()}"

    outcome = "SUCCESS" if exercises_completed > 0 else "FAILED"
    if outcome == "FAILED" and not failure_reason:
        failure_reason = "Incomplete Session / Early Disconnect"

    now_iso = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO call_logs (
                call_id, participant_name, channel, duration_seconds,
                exercises_completed, outcome, failure_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(call_id) DO UPDATE SET
                participant_name = excluded.participant_name,
                channel = excluded.channel,
                duration_seconds = excluded.duration_seconds,
                exercises_completed = excluded.exercises_completed,
                outcome = excluded.outcome,
                failure_reason = excluded.failure_reason,
                created_at = excluded.created_at
            """,
            (
                call_id,
                participant_name,
                channel,
                duration_seconds,
                exercises_completed,
                outcome,
                failure_reason,
                now_iso,
            ),
        )
        conn.commit()

    return {
        "call_id": call_id,
        "participant_name": participant_name,
        "channel": channel,
        "duration_seconds": duration_seconds,
        "exercises_completed": exercises_completed,
        "outcome": outcome,
        "failure_reason": failure_reason,
        "created_at": now_iso,
    }


def get_call_analytics() -> dict[str, Any]:
    """Compute aggregate call analytics (total, successful, failed, success rate, avg duration) from SQLite."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM call_logs")
        total_calls = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) as successful FROM call_logs WHERE outcome = 'SUCCESS'"
        )
        successful_calls = cursor.fetchone()["successful"]

        cursor.execute(
            "SELECT COUNT(*) as failed FROM call_logs WHERE outcome = 'FAILED'"
        )
        failed_calls = cursor.fetchone()["failed"]

        cursor.execute("SELECT AVG(duration_seconds) as avg_dur FROM call_logs")
        avg_duration = round(cursor.fetchone()["avg_dur"] or 0, 1)

        cursor.execute(
            """
            SELECT failure_reason, COUNT(*) as count
            FROM call_logs
            WHERE outcome = 'FAILED' AND failure_reason != ''
            GROUP BY failure_reason
            """
        )
        failure_reasons = {
            row["failure_reason"]: row["count"] for row in cursor.fetchall()
        }

        success_rate = (
            round((successful_calls / total_calls) * 100, 1) if total_calls > 0 else 0.0
        )

        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": success_rate,
            "average_duration_seconds": avg_duration,
            "failure_reasons": failure_reasons,
        }


def get_recent_call_logs(limit: int = 20) -> list[dict[str, Any]]:
    """Retrieve recent call log entries from SQLite."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM call_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = cursor.fetchall()
        return [
            {
                "call_id": row["call_id"],
                "participant_name": row["participant_name"],
                "channel": row["channel"],
                "duration_seconds": row["duration_seconds"],
                "exercises_completed": row["exercises_completed"],
                "outcome": row["outcome"],
                "failure_reason": row["failure_reason"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]


def clear_all_call_logs() -> None:
    """Clear all call logs from SQLite (used for test cleanup and resetting database)."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM call_logs")
        conn.commit()


def clear_all_escalation_tickets() -> None:
    """Clear all escalation tickets from SQLite (used for test cleanup and resetting database)."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM escalations")
        conn.commit()


def clear_entire_database() -> None:
    """Clear all records from users, escalations, and call_logs tables."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM escalations")
        cursor.execute("DELETE FROM call_logs")
        conn.commit()
