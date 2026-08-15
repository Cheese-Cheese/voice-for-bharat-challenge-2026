import asyncio
import json
import logging
import time
import uuid

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

import db
import tools

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# System prompt for Day 5 — Learning & Literacy track (Shiksha AI with Strict Tool Mandates)
SYSTEM_PROMPT = """IDENTITY:
You are "Shiksha AI", a patient, warm, and encouraging voice tutor for learners in India under the Learning & Literacy track.

OBJECTIVES:
- Help learners practice spoken English through interactive everyday conversation.
- Gently model correct grammar and vocabulary without shaming or interrupting flow.
- Build speaking confidence for learners in India.

KNOWLEDGE:
- Expert in spoken English, conversational vocabulary, and daily topics (family, school, work, hobbies).
- Out of scope: Medical advice, legal guidance, financial transactions, or exam answers.

LANGUAGE & SCRIPT:
- Speak in clear, warm Indian English.
- Always write every language in its own native script.
  * Hindi → Devanagari (नमस्ते), never romanized (never "namaste").
  * Same rule for all non-English languages.
- Code-mixed / Hinglish support: If the user mixes Hindi and English (Hinglish), understand them seamlessly and reply in matching warm Indian English with proper native script for non-English words.

GUARDRAILS:
1. NEVER SHAME: Never criticize, judge, or embarrass a learner for wrong answers or pronunciation mistakes. Always praise effort enthusiastically.
2. NEVER DIAGNOSE: Never claim, imply, or diagnose that a learner or child has a learning disability, cognitive deficit, or medical condition.
3. HARD REFUSALS & ESCALATION SCRIPT: If asked for medical advice, legal guidance, financial transactions, or exam cheating, refuse politely using this escalation script: "I am your spoken English learning buddy. For medical, legal, or exam questions, please consult your doctor, teacher, or family. Shall we get back to practicing your English?"

STRICT LIVE TOOL MANDATES (DAY 5):
1. WORD DEFINITION MANDATE:
   - WHENEVER or HOWEVER the learner asks for the definition, meaning, synonym, or example usage of ANY word (e.g. "What does X mean?", "Define X", "What is the meaning of X?", "Explain X"), YOU MUST IMMEDIATELY CALL `lookup_word_definition(word=X)`.
   - YOU ARE ABSOLUTELY FORBIDDEN FROM DEFINING OR EXPLAINING WORDS USING YOUR OWN GENERAL KNOWLEDGE WITHOUT CALLING THIS TOOL FIRST!
   - Always report the definition returned by the tool.

2. GRAMMAR CHECK MANDATE:
   - WHENEVER or HOWEVER the learner asks to check grammar, evaluate a sentence, or verify if a phrase is correct (e.g. "Is X correct?", "Check my sentence X", "Did I say X right?"), YOU MUST IMMEDIATELY CALL `check_sentence_grammar(sentence=X)`.
   - YOU ARE ABSOLUTELY FORBIDDEN FROM EVALUATING OR SCORING SENTENCE GRAMMAR WITHOUT CALLING THIS TOOL FIRST!
   - Always report the rule analysis returned by the tool.

3. GRACEFUL FALLBACK (CRITICAL): If a tool returns an offline or error status, NEVER go silent or output JSON error tracebacks! Reply warmly and explain the word or rule simply in your own words.

RETURNING CALLER SELECTION & MEMORY LOOKUP:
- When saved memory records exist in DB, ask who is learning at the start of call.
- As soon as the user tells their name (e.g. "I am Ramesh" or "It's Ramesh"), IMMEDIATELY call `lookup_caller(name=name)` to retrieve their profile.
- If found, welcome them back personally: "Welcome back Ramesh! Last time we practiced [topics]. Would you like to continue or try something new today?"
- If the DB is empty or user is new, DO NOT ask for their name upfront! Let them practice freely and ask for consent to save their details later.

PROACTIVE MEMORY & CONSENT (MANDATORY):
- You have persistent memory functions: `lookup_caller`, `save_caller_profile`, `forget_caller_profile`.
- POST-ACTIVITY CONSENT & NAME MANDATE:
  * AS SOON AS ANY LEARNING ACTIVITY (word lookup, grammar check, or practice exercise) IS COMPLETED, IF THE LEARNER'S NAME IS NOT YET KNOWN, YOU MUST IMMEDIATELY ASK FOR THEIR NAME AND CONSENT TO SAVE:
    "Great effort! May I ask your name, and may I save your name and practice progress so I remember you next time?"
  * As soon as the learner provides their name and agrees (says yes, sure, okay) -> IMMEDIATELY call `save_caller_profile(name=name, ...)`!
  * If the learner declines -> DO NOT call `save_caller_profile`. Reassure them warmly that no data will be stored.
- FORGET ME TOOL: If the learner asks you to "forget me", "delete my data", or "clear my memory" -> call `forget_caller_profile` immediately and confirm that all stored memory records have been wiped.

HUMAN TEACHER ESCALATION MANDATE (DAY 7):
1. TRIGGERS FOR HUMAN HELP:
   - LEARNER FRUSTRATION / GIVING UP: If the learner expresses discouragement, frustration, or distress (e.g. "I'm stupid", "English is too hard", "I can't do this", "I give up").
   - HUMAN TEACHER REQUEST: If the learner explicitly asks for a human teacher, tutor, or expert review (e.g. "Can a real teacher help me?", "I need a human tutor").
2. MANDATORY CONSENT GUARDRAIL:
   - Before logging a ticket, YOU MUST ASK for permission:
     "I hear that you are feeling frustrated. Would you like me to send your practice notes to a human English teacher so they can help you?"
   - If the learner agrees (says yes, sure, okay) -> Call `escalate_to_human_teacher` with consent_given=True.
   - If the learner declines (says no, don't) -> DO NOT call `escalate_to_human_teacher`. Reassure them warmly.
3. REFERENCE ID & NEXT STEP:
   - When a ticket is created, report the reference ID returned by the tool (e.g. ESC-XXXXXX) to the learner and reassure them warmly that a human teacher will review their practice notes within 24 hours.

SPECIALIST HANDOFF MANDATE (DAY 9):
- If the learner asks to practice a real-life scenario or roleplay a situation (e.g. fast food restaurant, ordering pizza, cafe, asking for directions, buying groceries, doctor appointment), or asks for the scenario tutor (e.g. "Let's roleplay", "Practice ordering food", "Connect me to the scenario tutor"), IMMEDIATELY CALL `transfer_to_scenario_specialist(scenario_type=X)`. Do NOT speak any introductory text yourself as the tool will announce the transition out loud automatically.
- HANDBACK RULE: When returning from a specialist handoff, do NOT repeat any welcome back greeting yourself, as your return check-in question will be asked automatically. Listen and respond to the user's answer.

CONVERSATION FLOW & DURATION:
- Keep the practice conversation short and focused (about 3 turns of practice).
- At the end of 3 turns, check in with the user: "We've completed a quick practice round! Would you like to continue practicing or wrap up for today?"

STYLE FOR SPEECH:
- Keep responses short, concise, and natural (1 to 2 short sentences per turn, maximum 20 words per sentence).
- Do NOT use markdown, bullet points, numbered lists, emojis, brackets, or special formatting."""


MITRA_SPECIALIST_PROMPT = """IDENTITY:
You are "Mitra AI", a warm, energetic, and encouraging Real-Life Scenario Roleplay Specialist for Indian English learners under the Learning & Literacy track.

OBJECTIVES:
- Play interactive, turn-by-turn real-life scenario roles based on EXACTLY what the learner requested (e.g. Fast Food Restaurant, Ordering Pizza, Metro Directions, Grocery Store, Doctor Visit, Hotel Booking).
- Help learners practice practical everyday English in real situations.
- Stay strictly in character during the scenario roleplay!

DYNAMIC SCENARIO MATCHING:
- Look at CURRENT SCENARIO and adapt IMMEDIATELY to that exact setting.
- NEVER default to "cafe" or "coffee shop" unless the user explicitly asked for a cafe!

OPENING RULE:
- On your very first sentence, introduce yourself as Mitra AI and immediately step into character for the EXACT scenario requested.
  * Fast Food / Restaurant: "Namaste! I am Mitra AI. Welcome to our fast food restaurant! What would you like to order today?"
  * Metro / Street Directions: "Namaste! I am Mitra AI. Where are you trying to travel today?"
  * Grocery / Shopping: "Namaste! I am Mitra AI. Welcome to the store! What items can I help you find today?"
- Do NOT ask "what would you like to say first". Always take the initiative and open the dialogue in character!

RULES & STYLE:
- Speak in clear, warm Indian English.
- Always write non-English words in native script (Hindi → Devanagari नमस्ते).
- Keep responses short and conversational (1 to 2 short sentences per turn).
- Do NOT use markdown, bullet points, or emojis in spoken speech.
- When scenario practice is completed or the learner asks to return to main practice, call `return_to_main_tutor()`."""


class Assistant(Agent):
    def __init__(self, room: rtc.Room | None = None, call_id: str = "") -> None:
        main_tts = murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        )
        super().__init__(instructions=SYSTEM_PROMPT, tts=main_tts)
        self.room = room
        self.call_id = call_id or f"CALL-{uuid.uuid4().hex[:6].upper()}"
        self.participant_name = "Learner"
        self.exercises_completed = 0
        self.user_speech_turns = 0
        self.start_time = time.time()
        self.logged = False
        self.is_returned_from_handback = False

    async def on_enter(self) -> None:
        """Trigger proactive check-in question ONLY when returned from specialist handback."""
        if self.is_returned_from_handback and hasattr(self, "session") and self.session:
            logger.info(
                "🎓 Shiksha AI re-entered session after handback — asking check-in question..."
            )
            self.is_returned_from_handback = False
            try:
                await self.session.say(
                    "Welcome back! How did your practice conversation go with Mitra AI?"
                )
            except Exception as e:
                logger.warning(f"Failed to speak Shiksha AI handback check-in: {e}")

    @function_tool
    async def escalate_to_human_teacher(
        self,
        context: RunContext,
        learner_name: str,
        reason: str,
        summary: str,
        urgency: str = "medium",
        consent_given: bool = True,
    ) -> str:
        """Create a human teacher escalation support ticket when a learner is frustrated, overwhelmed, or requests human teacher help.

        Args:
            learner_name: Name of the learner needing human teacher assistance.
            reason: Specific reason for escalation (e.g. 'Learner Frustration / Giving Up' or 'Human Teacher Guidance Requested').
            summary: Short 2-3 sentence summary of what was practiced, what the issue is, and learner's preferred language.
            urgency: Priority level ('low', 'medium', 'high', or 'emergency').
            consent_given: True ONLY if the learner explicitly gave permission to send their info to a human teacher.
        """
        if not consent_given:
            return "Consent not granted by the learner. Human escalation ticket was NOT created."

        self.exercises_completed += 1
        if learner_name and learner_name.strip() and learner_name.lower() != "learner":
            self.participant_name = learner_name.strip().title()

        ticket = db.create_escalation_ticket(
            learner_name=self.participant_name,
            reason=reason,
            summary=summary,
            urgency=urgency,
        )

        try:
            payload = json.dumps(
                {
                    "type": "tool_result",
                    "tool": "escalate_to_human_teacher",
                    "reference_id": ticket["reference_id"],
                    "learner_name": ticket["learner_name"],
                    "reason": ticket["reason"],
                    "summary": ticket["summary"],
                    "urgency": ticket["urgency"],
                    "status": ticket["status"],
                    "created_at": ticket["created_at"],
                }
            ).encode("utf-8")
            if self.room and self.room.local_participant:
                await self.room.local_participant.publish_data(
                    payload, topic="tool_results"
                )
        except Exception as e:
            logger.warning(
                f"Could not publish escalation tool_result data payload: {e}"
            )

        return (
            f"Successfully created human teacher ticket {ticket['reference_id']} with urgency {ticket['urgency']}. "
            f"Inform the learner that their ticket reference ID is {ticket['reference_id']} and a human teacher will review their practice notes within 24 hours."
        )

    @function_tool
    async def lookup_word_definition(self, context: RunContext, word: str) -> str:
        """Fetch real-time word definition, part of speech, and example sentence from live Free Dictionary API.

        Args:
            word: The English word to define or explain.
        """
        self.exercises_completed += 1
        res = await tools.fetch_word_definition(word)
        try:
            payload = json.dumps(
                {
                    "type": "tool_result",
                    "tool": "lookup_word_definition",
                    "word": res.get("word", word),
                    "definition": res.get("definition", ""),
                    "part_of_speech": res.get("part_of_speech", ""),
                    "example": res.get("example", ""),
                    "phonetics": res.get("phonetics", ""),
                    "status": res.get("status", "error"),
                    "message": res.get("message", ""),
                    "source": res.get("source", "Live Free Dictionary API"),
                }
            ).encode("utf-8")
            if self.room and self.room.local_participant:
                await self.room.local_participant.publish_data(
                    payload, topic="tool_results"
                )
                logger.info(f"Published tool_result payload for word: {word}")
        except Exception as e:
            logger.warning(f"Could not publish tool_result data payload: {e}")

        if res["status"] == "success":
            def_text = f"Definition of '{res['word']}' ({res['part_of_speech']}): {res['definition']}."
            if res.get("example"):
                def_text += f" Example: '{res['example']}'."
            def_text += " (Data from Live Free Dictionary API)"
            return def_text
        elif res["status"] == "not_found":
            return f"The word '{word}' was not found in the live dictionary. Reassure the learner and explain it simply in your own words."
        else:
            return f"Live dictionary service is currently unreachable ({res.get('message', 'offline')}). Provide a helpful simple definition directly to the learner."

    @function_tool
    async def check_sentence_grammar(self, context: RunContext, sentence: str) -> str:
        """Check a spoken sentence for real-time grammar rules and error corrections using LanguageTool API.

        Args:
            sentence: The spoken sentence or phrase to check for grammar.
        """
        self.exercises_completed += 1
        res = await tools.check_grammar_rules(sentence)
        try:
            payload = json.dumps(
                {
                    "type": "tool_result",
                    "tool": "check_sentence_grammar",
                    "sentence": res.get("sentence", sentence),
                    "is_correct": res.get("is_correct", False),
                    "error_count": res.get("error_count", 0),
                    "rules": res.get("rules", []),
                    "status": res.get("status", "error"),
                    "source": res.get("source", "LanguageTool Grammar Engine"),
                }
            ).encode("utf-8")
            if self.room and self.room.local_participant:
                await self.room.local_participant.publish_data(
                    payload, topic="tool_results"
                )
                logger.info(f"Published tool_result payload for sentence: {sentence}")
        except Exception as e:
            logger.warning(f"Could not publish tool_result data payload: {e}")

        if res["status"] == "success":
            if res["is_correct"]:
                return (
                    f"LanguageTool found 0 rule violations for '{sentence}'. "
                    f"Praise the learner warmly! If you notice any subtle conversational tense or phrasing issues, mention them encouragingly."
                )
            rules_summary = "; ".join(
                [
                    f"{r['issue_type']}: {r['message']} (Suggestions: {', '.join(r['replacements'])})"
                    for r in res["rules"]
                ]
            )
            return f"Grammar analysis found {res['error_count']} potential issue(s): {rules_summary}. Model the correction gently for the learner."
        else:
            return "Live grammar check API is currently offline. Model any correction directly and encouragingly without stalling."

    @function_tool
    async def lookup_caller(
        self, context: RunContext, name: str = "", user_id: str = ""
    ) -> str:
        """Lookup stored memory profile and learning history by name or user_id from SQLite database.

        Args:
            name: Learner's name (e.g. Ramesh, Priya).
            user_id: Unique identifier for caller.
        """
        profile = db.get_user_profile_by_name_or_id(name=name, user_id=user_id)
        if profile and profile.get("name"):
            self.participant_name = profile["name"].strip().title()
        elif name and name.strip():
            self.participant_name = name.strip().title()

        if not profile:
            return f"No previous memory profile found for '{name or user_id}'. This is a new learner."
        return (
            f"Found learner profile for {profile['name']}: "
            f"Current Level: {profile['facts']['current_level']}, "
            f"Topics Covered: {profile['facts']['topics_covered']}, "
            f"Common Mistakes: {profile['facts']['common_mistakes']}."
        )

    @function_tool
    async def save_caller_profile(
        self,
        context: RunContext,
        name: str,
        current_level: str = "Beginner",
        topics_covered: str = "",
        common_mistakes: str = "",
        consent_given: bool = True,
        user_id: str = "",
    ) -> str:
        """Save or update caller's profile and learning facts in SQLite database ONLY after obtaining explicit caller consent.

        Args:
            name: The caller's name.
            current_level: Spoken English level (e.g. Beginner, Intermediate).
            topics_covered: Topics practiced (e.g. Greetings, Ordering Food).
            common_mistakes: Language or grammar mistakes identified during practice.
            consent_given: Must be True if caller explicitly agreed to save their data.
            user_id: Caller's identifier.
        """
        if not consent_given:
            return "Consent was not granted. No caller profile saved."

        self.exercises_completed += 1
        if name and name.strip():
            self.participant_name = name.strip().title()

        db.save_user_profile(
            user_id=user_id,
            name=self.participant_name,
            current_level=current_level,
            topics_covered=topics_covered,
            common_mistakes=common_mistakes,
            consent_given=consent_given,
        )
        return f"Successfully saved profile for {name} to persistent memory database."

    @function_tool
    async def forget_caller_profile(
        self, context: RunContext, name: str = "", user_id: str = ""
    ) -> str:
        """Delete and wipe caller's stored memory profile from SQLite database when requested ('forget me').

        Args:
            name: Learner's name to delete.
            user_id: Unique identifier for the caller.
        """
        deleted = db.delete_user_profile(name=name, user_id=user_id)
        self.participant_name = "Learner"
        if deleted:
            return "Successfully deleted and wiped stored memory records. I have cleared your profile."
        return "No memory records found to delete."

    @function_tool
    async def transfer_to_scenario_specialist(
        self, context: RunContext, scenario_type: str = "Real-Life Practice"
    ) -> Agent:
        """Hand off the conversation to Mitra AI (Real-Life Scenario Roleplay Specialist) when the learner wants to practice real-life scenario roleplay (e.g. fast food restaurant, ordering food, asking directions, shopping, clinic visits).

        Args:
            scenario_type: Exact type of real-life scenario requested by learner (e.g. Fast Food Restaurant, Ordering Pizza, Asking Directions, Grocery Shopping, Doctor Appointment).
        """
        logger.info(
            f"🎭 Handoff triggered to Mitra AI (Scenario Specialist) for scenario: {scenario_type}"
        )
        self.exercises_completed += 1

        # Speak transition phrase out loud using Shiksha AI's voice (Anisha) and wait for audio playout
        if context and hasattr(context, "session") and context.session:
            try:
                speech_handle = await context.session.say(
                    "Sounds fun! I will connect you to Mitra AI, our real-life scenario roleplay specialist."
                )
                if hasattr(context, "wait_for_playout"):
                    await context.wait_for_playout(speech_handle)
            except Exception as err:
                logger.warning(f"Error during handoff speech playout: {err}")

        try:
            if self.room and self.room.local_participant:
                payload = json.dumps(
                    {
                        "type": "tool_result",
                        "tool": "transfer_to_scenario_specialist",
                        "data": {
                            "agent_name": "Mitra AI",
                            "agent_role": "Real-Life Scenario Roleplay Specialist",
                            "scenario_type": scenario_type,
                            "status": "HANDOFF_ACTIVE",
                        },
                    }
                )
                await self.room.local_participant.publish_data(
                    payload.encode("utf-8"),
                    topic="agent_tool_results",
                )
        except Exception as e:
            logger.warning(f"Could not publish handoff UI payload: {e}")

        return ScenarioSpecialist(
            room=self.room,
            call_id=self.call_id,
            participant_name=self.participant_name,
            scenario_type=scenario_type,
            parent_assistant=self,
        )


class ScenarioSpecialist(Agent):
    """Specialist Agent (Mitra AI) for interactive real-life scenario roleplays."""

    def __init__(
        self,
        room: rtc.Room | None = None,
        call_id: str = "",
        participant_name: str = "Learner",
        scenario_type: str = "Real-Life Practice",
        parent_assistant: Assistant | None = None,
    ) -> None:
        instructions = (
            f"{MITRA_SPECIALIST_PROMPT}\n\n"
            f"CURRENT SCENARIO: You are roleplaying a '{scenario_type}' scenario with {participant_name}. "
            f"Start immediately by introducing yourself as Mitra AI and opening the scenario!"
        )
        specialist_tts = murf.TTS(
            voice="Samar",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        )
        super().__init__(instructions=instructions, tts=specialist_tts)
        self.room = room
        self.call_id = call_id
        self.participant_name = participant_name
        self.scenario_type = scenario_type
        self.parent_assistant = parent_assistant

    async def on_enter(self) -> None:
        """Trigger one single proactive opening reply in character when Mitra AI takes over."""
        logger.info(
            "🎭 Mitra AI entered session — generating proactive in-character opening..."
        )
        if hasattr(self, "session") and self.session:
            try:
                await self.session.generate_reply()
            except Exception as e:
                logger.warning(f"Failed to generate proactive Mitra AI greeting: {e}")

    @function_tool
    async def return_to_main_tutor(self, context: RunContext) -> Agent:
        """Hand back the conversation to Shiksha AI (Main Tutor) when the scenario roleplay is complete or when the learner asks to return to main English practice."""
        logger.info("↩️ Handback triggered from Mitra AI to Shiksha AI (Main Tutor)")

        try:
            if self.room and self.room.local_participant:
                payload = json.dumps(
                    {
                        "type": "tool_result",
                        "tool": "return_to_main_tutor",
                        "data": {
                            "agent_name": "Shiksha AI",
                            "agent_role": "Main Voice Tutor",
                            "status": "RETURNED_TO_MAIN",
                        },
                    }
                )
                await self.room.local_participant.publish_data(
                    payload.encode("utf-8"),
                    topic="agent_tool_results",
                )
        except Exception as e:
            logger.warning(f"Could not publish handback UI payload: {e}")

        target_agent = self.parent_assistant or Assistant(
            room=self.room, call_id=self.call_id
        )
        target_agent.is_returned_from_handback = True
        return target_agent


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    try:
        from src.scheduler import start_outbound_scheduler_loop

        proc.userdata["scheduler_task"] = asyncio.create_task(
            start_outbound_scheduler_loop()
        )
        logger.info("🚀 Outbound call scheduler background task spawned successfully.")
    except Exception as e:
        logger.warning(f"Could not start outbound call scheduler background task: {e}")


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    assistant = Assistant(room=ctx.room)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=assistant,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()

    @ctx.room.on("data_received")
    def on_data_received(data_packet: rtc.DataPacket):
        try:
            payload_str = data_packet.data.decode("utf-8")
            logger.info(f"[DataChannel] Data received from room: {payload_str}")
            parsed = json.loads(payload_str)
            if parsed.get("type") == "toggle_offline_mode":
                enabled = bool(parsed.get("enabled", False))
                tools.set_simulate_offline(enabled)
                logger.info(f"⚡ SIMULATED OFFLINE MODE UPDATED TO: {enabled}")
        except Exception as err:
            logger.warning(f"Data packet parse error: {err}")

    @session.on("user_speech_committed")
    def on_user_speech(msg):
        assistant.user_speech_turns += 1

    def _finalize_call_log(reason: str = "Participant Disconnected"):
        if not assistant.logged:
            duration = int(time.time() - assistant.start_time)
            is_success = (
                assistant.exercises_completed > 0
                or assistant.user_speech_turns >= 2
                or (
                    assistant.participant_name
                    and assistant.participant_name.lower() != "learner"
                )
            )
            total_exercises = max(
                assistant.exercises_completed, assistant.user_speech_turns
            )
            db.log_call_session(
                call_id=assistant.call_id,
                participant_name=assistant.participant_name,
                channel="Web Browser",
                duration_seconds=duration,
                exercises_completed=total_exercises,
                failure_reason="" if is_success else reason,
            )
            assistant.logged = True
            logger.info(
                f"📊 Finalized call log for {assistant.call_id}: exercises={total_exercises}, success={is_success}, duration={duration}s"
            )

    @ctx.room.on("disconnected")
    def on_disconnected():
        _finalize_call_log("Participant Disconnected")

    ctx.add_shutdown_callback(lambda: _finalize_call_log("Session Terminated"))

    # Dynamic Conditional Memory Greeting: Check SQLite for existing memory profiles
    profiles = db.get_all_user_profiles()
    if len(profiles) >= 1:
        names = [p["name"] for p in profiles if p.get("name")]
        if len(names) == 1:
            assistant.participant_name = names[0]
            greeting = (
                f"Namaste! Welcome back to Shiksha AI. "
                f"Are you {names[0]}, or is someone new practicing today?"
            )
        else:
            names_str = ", ".join(names[:-1]) + " or " + names[-1]
            greeting = (
                f"Namaste! Welcome back to Shiksha AI. "
                f"Who is practicing today? ({names_str}, or someone new?)"
            )
    else:
        # Default greeting when DB has no saved profiles (never ask for name upfront!)
        greeting = (
            "Namaste! I am Shiksha AI, your spoken English buddy. "
            "What would you like to practice speaking today?"
        )

    await session.say(greeting)


if __name__ == "__main__":
    cli.run_app(server)
