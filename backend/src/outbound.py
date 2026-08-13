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

load_dotenv(".env.local")

# DAY 6 OUTBOUND SYSTEM PROMPT — Learning & Literacy Track (Shiksha AI)
OUTBOUND_SYSTEM_PROMPT = """IDENTITY:
You are "Shiksha AI", a patient, warm, and encouraging spoken English tutor for learners in India under the Learning & Literacy track.

OBJECTIVES:
Act as an outbound daily English practice call assistant. Help the learner practice spoken English in a quick 2-minute call.

STRICT OPENING SCRIPT (MANDATORY STEP 4):
In an outbound call, you speak first. You MUST immediately say the following exact points in your first two sentences as soon as the call connects:
1. "Namaste! I am Shiksha AI, your spoken English learning buddy."
2. "I am calling for your scheduled daily English speaking practice session."
3. "If you do not want to receive these daily practice calls, just tell me to stop or unsubscribe."

STRICT LANGUAGE & SCRIPT RULES:
1. Speak in clear, warm Indian English.
2. Always write non-English words in their native script:
   - Hindi → Devanagari (नमस्ते), never romanized (never "namaste").
   - Same rule for all non-English languages.
3. Keep responses short and conversational (1 to 2 short sentences per turn, max 20 words per sentence). Do NOT use markdown or emojis in spoken speech.

STRICT LIVE TOOL MANDATES:
1. WORD DEFINITION LOOKUP: When a learner asks for word meanings or definitions, call `lookup_word_definition(word=X)`.
2. GRAMMAR CHECK MANDATE: When evaluating a sentence or checking grammar, call `check_sentence_grammar(sentence=X)`.
3. POST-ACTIVITY CONSENT & NAME MANDATE: At the end of an activity, if the learner's name is not yet known, ASK: "Great job! What is your name, and may I save your name and progress so I remember you next time?" If they agree, call `save_caller_profile`.
4. FORGET ME: If told to "forget me", call `forget_caller_profile`.
"""


class OutboundAssistant(Agent):
    def __init__(self, room: rtc.Room | None = None, call_id: str = "") -> None:
        super().__init__(instructions=OUTBOUND_SYSTEM_PROMPT)
        self.room = room
        self.call_id = call_id or f"SIP-{uuid.uuid4().hex[:6].upper()}"
        self.participant_name = "SIP Caller"
        self.exercises_completed = 0
        self.start_time = time.time()
        self.logged = False

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
        """Create a human teacher escalation support ticket when a learner is frustrated or requests human teacher help.

        Args:
            learner_name: Name of the learner needing human teacher assistance.
            reason: Specific reason for escalation (e.g. 'Learner Frustration' or 'Teacher Review Requested').
            summary: Short summary of what was practiced, the issue, and learner's language.
            urgency: Priority level ('low', 'medium', 'high', or 'emergency').
            consent_given: True ONLY if the learner explicitly gave permission.
        """
        if not consent_given:
            return "Consent not granted. Escalation ticket NOT created."

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
            logger.warning(f"Could not publish escalation tool_result payload: {e}")

        return (
            f"Successfully created human teacher ticket {ticket['reference_id']} with urgency {ticket['urgency']}. "
            f"Inform the learner that reference ID is {ticket['reference_id']} and a teacher will review within 24 hours."
        )

    @function_tool
    async def lookup_word_definition(self, context: RunContext, word: str) -> str:
        """Fetch real-time word definition from live Free Dictionary API."""
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
            return def_text
        elif res["status"] == "not_found":
            return f"The word '{word}' was not found in the live dictionary. Explain it simply in your own words."
        else:
            return f"Live dictionary service is unreachable ({res.get('message', 'offline')}). Explain it simply."

    @function_tool
    async def check_sentence_grammar(self, context: RunContext, sentence: str) -> str:
        """Check spoken sentence for grammar using LanguageTool API."""
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
        profile = db.get_user_profile_by_name_or_id(name=name, user_id=user_id)
        if profile and profile.get("name"):
            self.participant_name = profile["name"].strip().title()
        elif name and name.strip():
            self.participant_name = name.strip().title()

        if not profile:
            return f"No memory profile found for '{name or user_id}'."
        return (
            f"Profile for {profile['name']}: Level {profile['facts']['current_level']}."
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
        """Save learner facts in SQLite database after obtaining explicit consent."""
        if not consent_given:
            return "Consent not granted. Profile not saved."
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
        return f"Successfully saved profile for {self.participant_name}."

    @function_tool
    async def forget_caller_profile(
        self, context: RunContext, name: str = "", user_id: str = ""
    ) -> str:
        """Delete stored memory profile from SQLite database on 'forget me' request."""
        deleted = db.delete_user_profile(name=name, user_id=user_id)
        if deleted:
            return "Successfully deleted stored memory records."
        return "No memory records found to delete."


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    url = os.environ.get("LIVEKIT_URL")
    api_key = os.environ.get("LIVEKIT_API_KEY")
    api_secret = os.environ.get("LIVEKIT_API_SECRET")

    sip_trunk_id = os.environ.get("SIP_TRUNK_ID")
    my_sip_uri = os.environ.get("MY_SIP_URI")

    if not all([url, api_key, api_secret]):
        logger.error("Missing required LiveKit environment variables.")
        return

    if not sip_trunk_id or not my_sip_uri:
        logger.error("Missing SIP_TRUNK_ID or MY_SIP_URI in environment.")
        return

    # Generate a unique room name for this outbound call
    room_name = f"outbound-call-{uuid.uuid4().hex[:8]}"
    room = rtc.Room()

    # Create a token for the agent to join the room
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity("agent-shiksha")
        .with_name("Shiksha AI")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )

    logger.info(f"Connecting Agent to room: {room_name}")
    await room.connect(url, token)

    # Prewarm VAD
    logger.info("Pre-loading VAD model...")
    vad = silero.VAD.load()

    http_session = aiohttp.ClientSession()
    lkapi = None

    try:
        # Choose LLM: Groq if GROQ_API_KEY present, else Google Gemini (default)
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key and openai is not None:
            logger.info("Using Groq LLM (llama-3.3-70b-versatile)")
            llm_instance = openai.LLM(
                model="llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key,
            )
        else:
            logger.info("Using Google Gemini LLM (gemini-3.5-flash-lite)")
            llm_instance = google.LLM(model="gemini-3.5-flash-lite")

        # Initialize Agent Session
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
            turn_detection=None,
            vad=vad,
            preemptive_generation=True,
        )

        assistant = OutboundAssistant(room=room)

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

        logger.info("Agent connected and started.")

        background_tasks = set()

        @room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(
                f"Participant connected: {participant.identity} (kind: {participant.kind})"
            )

        @room.on("track_subscribed")
        def on_track_subscribed(
            track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ):
            logger.info(
                f"Subscribed to track {track.sid} from {participant.identity} (kind: {track.kind})"
            )
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                logger.info(
                    "SIP audio track subscribed! Triggering mandatory opening speech..."
                )

                async def _say_opening():
                    await session.say(
                        "Namaste! I am Shiksha AI, your spoken English learning buddy. "
                        "I am calling for your scheduled daily English speaking practice session. "
                        "If you do not want to receive these daily practice calls, just tell me to stop or unsubscribe."
                    )

                t = asyncio.create_task(_say_opening())
                background_tasks.add(t)
                t.add_done_callback(background_tasks.discard)

        @room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            logger.info(
                f"Participant disconnected: {participant.identity} (kind: {participant.kind})"
            )

        # Parse SIP target username (LiveKit expects SIP user e.g. "cheese-cheese", not full URI)
        sip_target = my_sip_uri.replace("sip:", "").split("@")[0].strip()
        logger.info(
            f"Initiating SIP call to username '{sip_target}' via trunk {sip_trunk_id}..."
        )
        lkapi = api.LiveKitAPI(url, api_key, api_secret)

        try:
            participant = await lkapi.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    sip_trunk_id=sip_trunk_id,
                    sip_call_to=sip_target,
                    sip_number=sip_target,  # MUST BE SIP USERNAME OR PHONE NUMBER
                    room_name=room_name,
                    participant_identity="sip-caller",
                    participant_name="Outbound Learner Call",
                )
            )
            logger.info(
                f"SIP call initiated! Participant ID: {participant.participant_id}"
            )
        except Exception as e:
            logger.error(f"Failed to create SIP participant: {e}")

        logger.info("Waiting for the call to finish. Press Ctrl+C to exit.")

        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Exiting outbound script...")
    finally:
        logger.info("Cleaning up...")
        await room.disconnect()
        if lkapi:
            await lkapi.aclose()
        await http_session.close()


if __name__ == "__main__":
    asyncio.run(main())
