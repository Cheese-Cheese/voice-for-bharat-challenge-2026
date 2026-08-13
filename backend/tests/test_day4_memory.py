import pytest

from db import (
    delete_user_profile,
    get_all_user_profiles,
    get_user_profile_by_name_or_id,
    init_db,
    save_user_profile,
)


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure clean test state before each test."""
    init_db()
    delete_user_profile()
    yield
    delete_user_profile()


def test_sqlite_save_and_retrieve():
    """Test saving a new user profile and retrieving it from SQLite."""
    saved = save_user_profile(
        name="Ramesh",
        language_preference="English",
        current_level="Beginner",
        topics_covered="Everyday Conversation, Greetings",
        common_mistakes="Confusing has vs have",
        consent_given=True,
    )
    assert saved["name"] == "Ramesh"
    assert saved["facts"]["current_level"] == "Beginner"

    retrieved = get_user_profile_by_name_or_id(name="Ramesh")
    assert retrieved is not None
    assert retrieved["name"] == "Ramesh"
    assert retrieved["facts"]["topics_covered"] == "Everyday Conversation, Greetings"
    assert retrieved["facts"]["common_mistakes"] == "Confusing has vs have"
    assert retrieved["consent_given"] is True


def test_sqlite_get_all_profiles_conditional():
    """Test conditional lookup when multiple memory profiles exist."""
    assert len(get_all_user_profiles()) == 0

    save_user_profile(name="Ramesh", topics_covered="Greetings")
    save_user_profile(name="Priya", topics_covered="Ordering Food")

    profiles = get_all_user_profiles()
    assert len(profiles) == 2
    names = [p["name"] for p in profiles]
    assert "Ramesh" in names
    assert "Priya" in names


def test_sqlite_forget_me_by_name():
    """Test the 'forget me' tool deleting stored records by name from SQLite."""
    save_user_profile(name="Priya", current_level="Intermediate", consent_given=True)

    # Verify saved
    assert get_user_profile_by_name_or_id(name="Priya") is not None

    # Execute forget me
    deleted = delete_user_profile(name="Priya")
    assert deleted is True

    # Verify completely wiped
    assert get_user_profile_by_name_or_id(name="Priya") is None
