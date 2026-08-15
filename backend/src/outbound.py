import asyncio
import json
import logging
import os
import time
import uuid

import aiohttp
from dotenv import load_dotenv
from livekit import api, rtc
from livekit.agents import (
    Agent,
    AgentSession,
    RunContext,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import (
    deepgram,
    google,
    murf,
    noise_cancellation,
    silero,
)

try:
    from livekit.plugins import openai
except ImportError:
    openai = None

import db
import tools

logger = logging.getLogger("outbound")
_background_tasks = set()

load_dotenv(".env.local")

# FULL SHIKSHA AI OUTBOUND SYSTEM PROMPT WITH LEARNER NAME PERSONALIZATION & STRICT GUARDRAILS
OUTBOUND_SYSTEM_PROMPT = """IDENTITY:
You are "Shiksha AI", a patient, warm, and encouraging spoken English voice tutor for learners in India under the Learning & Literacy track.

OBJECTIVES:
- Help learners practice spoken English through interactive everyday conversation in a scheduled daily english practice call.
- If the learner does not want to receive these daily practice calls, inform them they can say stop or unsubscribe at any time.
- Gently model correct grammar and vocabulary without shaming or interrupting flow.
- Build speaking confidence for learners in India.

LEARNER KNOWLEDGE:
- You are calling a scheduled learner. Address them warmly by their name whenever appropriate.

KNOWLEDGE & GUARDRAILS:
- Expert in spoken English, conversational vocabulary, and daily topics (family, school, work, hobbies).
- Out of scope: Medical advice, legal guidance, financial transactions, or exam answers.
- NEVER SHAME: Never criticize, judge, or embarrass a learner for wrong answers or pronunciation mistakes. Always praise effort enthusiastically.
- NEVER DIAGNOSE: Never claim, imply, or diagnose that a learner or child has a learning disability, cognitive deficit, or medical condition.
- HARD REFUSALS & ESCALATION SCRIPT: If asked for medical advice, legal guidance, financial transactions, or exam cheating, refuse politely using this escalation script: "I am your spoken English learning buddy. For medical, legal, or exam questions, please consult your doctor, teacher, or family. Shall we get back to practicing your English?"

LANGUAGE & SCRIPT:
- Speak in clear, warm Indian English.
- Always write every language in its own native script:
  * Hindi → Devanagari (नमस्ते), never romanized (never "namaste").
  * Same rule for all non-English languages.
- Code-mixed / Hinglish support: If the user mixes Hindi and English (Hinglish), understand them seamlessly and reply in matching warm Indian English with proper native script for non-English words.

STRICT LIVE TOOL MANDATES:
1. WORD DEFINITION MANDATE:
   - WHENEVER or HOWEVER the learner asks for the definition, meaning, synonym, or example usage of ANY word (e.g. "What does X mean?", "Define X", "What is the meaning of X?"), YOU MUST IMMEDIATELY CALL `lookup_word_definition(word=X)`.
   - YOU ARE ABSOLUTELY FORBIDDEN FROM DEFINING OR EXPLAINING WORDS USING YOUR OWN GENERAL KNOWLEDGE WITHOUT CALLING THIS TOOL FIRST!
   - Always report the definition returned by the tool.

2. GRAMMAR CHECK MANDATE:
   - WHENEVER the learner asks you to check, evaluate, or correct a spoken sentence (e.g. "Is my sentence correct?", "Check my grammar", "Did I say that right?"), YOU MUST IMMEDIATELY CALL `check_sentence_grammar(sentence=X)`.
   - Always report the rule analysis returned by the tool.

3. GRACEFUL FALLBACK (CRITICAL): If a tool returns an offline or error status, NEVER go silent or output JSON error tracebacks! Reply warmly and explain the word or rule simply in your own words.

4. PERSISTENT MEMORY & CONSENT:
   - You have persistent memory functions: `lookup_caller`, `save_caller_profile`, `forget_caller_profile`.
   - POST-ACTIVITY CONSENT & NAME MANDATE:
     * AS SOON AS ANY LEARNING ACTIVITY (word lookup, grammar check, or practice exercise) IS COMPLETED, IF CONSENT IS NOT YET SAVED, ASK:
       "Great effort! May I save your practice progress so I remember your level next time?"
     * If the learner agrees -> call `save_caller_profile`.
     * If the learner declines -> reassure them warmly that no data will be stored.
   - FORGET ME TOOL: If told to "forget me" or "delete my data" -> call `forget_caller_profile` immediately.

5. HUMAN TEACHER ESCALATION MANDATE:
   - If the learner expresses discouragement, frustration, or asks for a human teacher, ask: "Would you like me to send your practice notes to a human English teacher so they can help you?"
   - If agreed -> call `escalate_to_human_teacher` with consent_given=True and report the reference ID (ESC-XXXXXX).

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


class OutboundAssistant(Agent):
    def __init__(
        self,
        room: rtc.Room | None = None,
        call_id: str = "",
        participant_name: str = "Learner",
        http_session: aiohttp.ClientSession | None = None,
    ) -> None:
        custom_instructions = (
            f"{OUTBOUND_SYSTEM_PROMPT}\n\n"
            f"CURRENT CALLER/LEARNER NAME: {participant_name}. "
            f"Address the learner warmly as '{participant_name}'."
        )
        super().__init__(instructions=custom_instructions)
        self.room = room
        self.call_id = call_id or f"SIP-{uuid.uuid4().hex[:6].upper()}"
        self.participant_name = participant_name
        self.http_session = http_session
        self.exercises_completed = 0
        self.user_speech_turns = 0
        self.start_time = time.time()
        self.logged = False
        self.is_returned_from_handback = False

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
        name = (
            learner_name
            if (
                learner_name
                and learner_name.strip()
                and learner_name.lower() != "learner"
            )
            else self.participant_name
        )
        self.participant_name = name.strip().title()

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
        except Exception as e:
            logger.warning(f"Could not publish tool_result data payload: {e}")

        if res["status"] == "success":
            def_text = f"Definition of '{res['word']}' ({res['part_of_speech']}): {res['definition']}."
            if res.get("example"):
                def_text += f" Example: '{res['example']}'."
            def_text += " (Data from Live Free Dictionary API)"
            return def_text
        elif res["status"] == "not_found":
            return f"The word '{word}' was not found in the live dictionary. Explain it simply in your own words."
        else:
            return f"Live dictionary service is currently unreachable ({res.get('message', 'offline')}). Provide a simple definition directly."

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
        except Exception as e:
            logger.warning(f"Could not publish tool_result data payload: {e}")

        if res["status"] == "success":
            if res["is_correct"]:
                return (
                    f"LanguageTool found 0 rule violations for '{sentence}'. "
                    f"Praise the learner warmly! If you notice any subtle conversational tense or phrasing issues, mention them encouragingly."
                )
            rules_summary = "; ".join(
                [f"{r['issue_type']}: {r['message']}" for r in res["rules"]]
            )
            return f"Grammar analysis found issues: {rules_summary}. Model correction gently."
        else:
            return "Live grammar check API is offline. Model correction directly."

    @function_tool
    async def lookup_caller(
        self, context: RunContext, name: str = "", user_id: str = ""
    ) -> str:
        """Lookup stored learner profile from SQLite database."""
        search_name = name or self.participant_name
        profile = db.get_user_profile_by_name_or_id(name=search_name, user_id=user_id)
        if profile and profile.get("name"):
            self.participant_name = profile["name"].strip().title()

        if not profile:
            return f"No memory profile found for '{search_name}'."
        return (
            f"Profile for {profile['name']}: Level {profile['facts']['current_level']}."
        )

    @function_tool
    async def save_caller_profile(
        self,
        context: RunContext,
        name: str = "",
        current_level: str = "Beginner",
        topics_covered: str = "",
        common_mistakes: str = "",
        consent_given: bool = True,
        user_id: str = "",
    ) -> str:
        """Save learner facts in SQLite database after obtaining explicit consent."""
        if not consent_given:
            return "Consent not granted. Profile not saved."
        self.exercises_completed += 1
        save_name = name if (name and name.strip()) else self.participant_name
        self.participant_name = save_name.strip().title()

        db.save_user_profile(
            user_id=user_id,
            name=self.participant_name,
            current_level=current_level,
            topics_covered=topics_covered,
            common_mistakes=common_mistakes,
            consent_given=consent_given,
        )
        return f"Successfully saved profile for {self.participant_name}."

    async def on_enter(self) -> None:
        """Trigger proactive check-in question ONLY when returned from specialist handback."""
        if self.is_returned_from_handback and hasattr(self, "session") and self.session:
            logger.info(
                "Shiksha AI re-entered session after handback — asking check-in question..."
            )
            self.is_returned_from_handback = False
            try:
                await self.session.say(
                    "Welcome back! How did your practice conversation go with Mitra AI?"
                )
            except Exception as e:
                logger.warning(f"Failed to speak Shiksha AI handback check-in: {e}")

    @function_tool
    async def forget_caller_profile(
        self, context: RunContext, name: str = "", user_id: str = ""
    ) -> str:
        """Delete stored memory profile from SQLite database on 'forget me' request."""
        search_name = name or self.participant_name
        deleted = db.delete_user_profile(name=search_name, user_id=user_id)
        if deleted:
            return f"Successfully deleted stored memory records for {search_name}."
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
            f"Handoff triggered to Mitra AI (Scenario Specialist) for scenario: {scenario_type}"
        )
        self.exercises_completed += 1

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
            http_session=self.http_session,
        )


class ScenarioSpecialist(Agent):
    """Specialist Agent (Mitra AI) for interactive real-life scenario roleplays."""

    def __init__(
        self,
        room: rtc.Room | None = None,
        call_id: str = "",
        participant_name: str = "Learner",
        scenario_type: str = "Real-Life Practice",
        parent_assistant: OutboundAssistant | None = None,
        http_session: aiohttp.ClientSession | None = None,
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
            http_session=http_session,
        )
        super().__init__(instructions=instructions, tts=specialist_tts)
        self.room = room
        self.call_id = call_id
        self.participant_name = participant_name
        self.scenario_type = scenario_type
        self.parent_assistant = parent_assistant
        self.http_session = http_session

    async def on_enter(self) -> None:
        """Trigger one single proactive opening reply in character when Mitra AI takes over."""
        logger.info(
            "Mitra AI entered session — generating proactive in-character opening..."
        )
        if hasattr(self, "session") and self.session:
            try:
                await self.session.generate_reply()
            except Exception as e:
                logger.warning(f"Failed to generate proactive Mitra AI greeting: {e}")

    @function_tool
    async def return_to_main_tutor(self, context: RunContext) -> Agent:
        """Hand back the conversation to Shiksha AI (Main Tutor) when the scenario roleplay is complete or when the learner asks to return to main English practice."""
        logger.info("Handback triggered from Mitra AI to Shiksha AI (Main Tutor)")

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

        target_agent = self.parent_assistant or OutboundAssistant(
            room=self.room,
            call_id=self.call_id,
            participant_name=self.participant_name,
            http_session=self.http_session,
        )
        target_agent.is_returned_from_handback = True
        return target_agent


async def _run_outbound_call_session(
    url: str,
    api_key: str,
    api_secret: str,
    sip_trunk_id: str,
    target: str,
    participant_name: str,
    room_name: str,
) -> None:
    """Run full voice agent pipeline session for an outbound SIP call."""
    lkapi = api.LiveKitAPI(url, api_key, api_secret)
    http_session = aiohttp.ClientSession()
    room = rtc.Room()

    try:
        token = (
            api.AccessToken(api_key, api_secret)
            .with_identity(f"agent-{uuid.uuid4().hex[:4]}")
            .with_name("Shiksha AI")
            .with_grants(api.VideoGrants(room_join=True, room=room_name))
            .to_jwt()
        )

        await room.connect(url, token)
        logger.info(
            f"Agent connected to room '{room_name}' for outbound SIP call to {participant_name}."
        )

        # Data received listener for simulated offline mode toggle
        @room.on("data_received")
        def on_data_received(dp: rtc.DataPacket):
            try:
                payload_str = dp.data.decode("utf-8")
                parsed = json.loads(payload_str)
                if parsed.get("type") == "toggle_offline_mode":
                    enabled = bool(parsed.get("enabled", False))
                    tools.set_simulate_offline(enabled)
                    logger.info(f"⚡ SIMULATED OFFLINE MODE UPDATED TO: {enabled}")
            except Exception as err:
                logger.warning(f"Data packet parse error: {err}")

        vad = silero.VAD.load()
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key and openai is not None:
            llm_instance = openai.LLM(
                model="llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key,
            )
        else:
            llm_instance = google.LLM(model="gemini-3.5-flash-lite")

        session = AgentSession(
            stt=deepgram.STT(
                model="nova-3", language="multi", http_session=http_session
            ),
            llm=llm_instance,
            tts=murf.TTS(
                voice="Anisha",
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True,
                http_session=http_session,
            ),
            vad=vad,
            preemptive_generation=True,
        )

        assistant = OutboundAssistant(
            room=room, participant_name=participant_name, http_session=http_session
        )

        @session.on("user_speech_committed")
        def on_user_speech(msg):
            assistant.user_speech_turns += 1

        await session.start(
            agent=assistant,
            room=room,
            room_options=room_io.RoomOptions(
                close_on_disconnect=False,
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

        background_tasks = set()

        @room.on("track_subscribed")
        def on_track_subscribed(track, publication, participant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                logger.info(
                    f"SIP audio track connected for {participant_name}! Triggering personalized opening speech..."
                )

                async def _say_opening():
                    greeting = (
                        f"Namaste {participant_name}! I am Shiksha AI, your spoken English learning buddy. "
                        f"I am calling for your scheduled daily English speaking practice session."
                    )
                    await session.say(greeting)

                t = asyncio.create_task(_say_opening())
                background_tasks.add(t)
                t.add_done_callback(background_tasks.discard)

        # Create SIP participant to ring Linphone
        caller_number = os.environ.get("MY_SIP_NUMBER", "+18885550199")
        req = api.CreateSIPParticipantRequest(
            sip_trunk_id=sip_trunk_id,
            sip_call_to=target,
            sip_number=caller_number,
            room_name=room_name,
            participant_identity=f"sip-{uuid.uuid4().hex[:4]}",
            participant_name=participant_name,
        )
        res = await lkapi.sip.create_sip_participant(req)
        logger.info(
            f"SIP Outbound Call Dialing '{target}': participant_id={res.participant_id}"
        )

        def _finalize_call_log(reason: str = "Participant Disconnected"):
            if not assistant.logged:
                duration = int(time.time() - assistant.start_time)
                is_success = (
                    assistant.exercises_completed > 0
                    or assistant.user_speech_turns >= 1
                )
                total_exercises = max(
                    assistant.exercises_completed, assistant.user_speech_turns
                )
                db.log_call_session(
                    call_id=assistant.call_id,
                    participant_name=assistant.participant_name,
                    channel=f"Outbound SIP ({target})",
                    duration_seconds=duration,
                    exercises_completed=total_exercises,
                    failure_reason="" if is_success else reason,
                )
                assistant.logged = True
                logger.info(
                    f"📊 Finalized call log for {assistant.call_id}: exercises={total_exercises}, success={is_success}, duration={duration}s"
                )

        @room.on("disconnected")
        def on_disconnected():
            _finalize_call_log("Participant Disconnected")

        # Keep session active for up to 180 seconds or until room disconnects
        for _ in range(180):
            if not room.isconnected():
                break
            await asyncio.sleep(1)

        _finalize_call_log("Call Session Timeout")

    except Exception as e:
        logger.error(f"Error during outbound SIP call session to '{target}': {e}")
    finally:
        logger.info(f"Cleaning up outbound room '{room_name}'...")
        await room.disconnect()
        await lkapi.aclose()
        await http_session.close()


async def trigger_outbound_sip_call(
    phone_number: str, participant_name: str = "Learner"
) -> dict:
    """Initiate an outbound SIP call via LiveKit API and SIP Trunk."""
    url = os.environ.get("LIVEKIT_URL")
    api_key = os.environ.get("LIVEKIT_API_KEY")
    api_secret = os.environ.get("LIVEKIT_API_SECRET")
    sip_trunk_id = os.environ.get("SIP_TRUNK_ID")

    if not all([url, api_key, api_secret]):
        logger.warning("LiveKit API credentials missing for outbound call.")
        return {"status": "error", "message": "Missing LiveKit API credentials"}

    target = (
        phone_number.replace("sip:", "").split("@")[0].strip()
        if "@" in phone_number
        else phone_number.strip()
    )
    room_name = f"outbound-{uuid.uuid4().hex[:6]}"

    if not sip_trunk_id:
        logger.warning(
            f"SIP_TRUNK_ID not set in .env.local. Simulating outbound call to '{target}' in room {room_name}..."
        )
        return {"status": "simulated", "room": room_name, "target": target}

    # Spawn background call session task so it stays connected while user answers
    task = asyncio.create_task(
        _run_outbound_call_session(
            url=url,
            api_key=api_key,
            api_secret=api_secret,
            sip_trunk_id=sip_trunk_id,
            target=target,
            participant_name=participant_name,
            room_name=room_name,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {
        "status": "success",
        "room": room_name,
        "target": target,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Outbound SIP Call module ready.")
