import pytest

from agent import Assistant, ScenarioSpecialist


@pytest.mark.asyncio
async def test_specialist_instantiation():
    """Verify ScenarioSpecialist (Mitra AI) initializes with scenario context."""
    specialist = ScenarioSpecialist(
        call_id="CALL-TEST99",
        participant_name="Ramesh",
        scenario_type="Cafe Ordering",
    )
    assert specialist.participant_name == "Ramesh"
    assert specialist.scenario_type == "Cafe Ordering"
    assert "Mitra AI" in specialist.instructions
    assert "Cafe Ordering" in specialist.instructions


@pytest.mark.asyncio
async def test_assistant_transfer_to_scenario_specialist():
    """Verify Assistant.transfer_to_scenario_specialist returns a ScenarioSpecialist instance."""
    assistant = Assistant(call_id="CALL-TEST88")
    assistant.participant_name = "Priya"

    # Invoke tool logic
    specialist = await assistant.transfer_to_scenario_specialist(
        context=None, scenario_type="Asking Directions"
    )

    assert isinstance(specialist, ScenarioSpecialist)
    assert specialist.participant_name == "Priya"
    assert specialist.scenario_type == "Asking Directions"
    assert assistant.exercises_completed == 1


@pytest.mark.asyncio
async def test_specialist_return_to_main_tutor():
    """Verify ScenarioSpecialist.return_to_main_tutor returns the parent Assistant instance."""
    assistant = Assistant(call_id="CALL-TEST77")
    assistant.participant_name = "Priya"
    specialist = ScenarioSpecialist(
        call_id="CALL-TEST77",
        participant_name="Priya",
        scenario_type="Grocery Shopping",
        parent_assistant=assistant,
    )

    returned_agent = await specialist.return_to_main_tutor(context=None)
    assert returned_agent is assistant
    assert returned_agent.participant_name == "Priya"
