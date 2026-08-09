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
    """Initialize the SQLite database schema for storing caller memory profiles."""
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
