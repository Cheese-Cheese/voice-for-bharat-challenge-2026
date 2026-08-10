import pytest

from tools import check_grammar_rules, fetch_word_definition


@pytest.mark.asyncio
async def test_live_dictionary_fetch_success():
    """Test fetching live word definition from Free Dictionary API."""
    result = await fetch_word_definition("courage")
    assert result["status"] in ["success", "offline_fallback"]

    if result["status"] == "success":
        assert result["word"] == "courage"
        assert len(result["definition"]) > 0
        assert "source" in result


@pytest.mark.asyncio
async def test_live_dictionary_fetch_not_found():
    """Test lookup for non-existent word returns not_found or error status cleanly."""
    result = await fetch_word_definition("xyzabc123nonexistent")
    assert result["status"] in ["not_found", "error", "offline_fallback"]
    if result["status"] == "not_found":
        assert "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_live_grammar_check():
    """Test sentence grammar checking via LanguageTool API."""
    result = await check_grammar_rules("I goes to school yesterday.")
    assert result["status"] in ["success", "offline_fallback"]

    if result["status"] == "success":
        assert result["is_correct"] is False
        assert result["error_count"] > 0
        assert len(result["rules"]) > 0
