import os

from outbound import OUTBOUND_SYSTEM_PROMPT


def test_outbound_env_vars_configured():
    """Verify Day 6 SIP environment variables are set."""
    sip_trunk_id = os.environ.get("SIP_TRUNK_ID")
    my_sip_uri = os.environ.get("MY_SIP_URI")

    assert sip_trunk_id == "ST_7Bgf2f6Cm5Bs"
    assert my_sip_uri == "sip:cheese-cheese@sip.linphone.org"


def test_outbound_system_prompt_mandate():
    """Verify Day 6 mandatory opening script elements in prompt."""
    prompt_lower = OUTBOUND_SYSTEM_PROMPT.lower()

    # Step 4 mandates: who is calling, why, and how to opt out
    assert "shiksha ai" in prompt_lower
    assert "scheduled daily english" in prompt_lower or "daily practice" in prompt_lower
    assert "stop" in prompt_lower or "unsubscribe" in prompt_lower


def test_outbound_native_script_mandate():
    """Verify native script mandate for Hindi in Day 6 prompt."""
    assert "Hindi → Devanagari" in OUTBOUND_SYSTEM_PROMPT
    assert "नमस्ते" in OUTBOUND_SYSTEM_PROMPT
