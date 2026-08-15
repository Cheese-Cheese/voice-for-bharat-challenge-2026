import asyncio
import logging

from dotenv import load_dotenv

load_dotenv(".env.local")

try:
    import db
    from outbound import trigger_outbound_sip_call
except ImportError:
    from src import db
    from src.outbound import trigger_outbound_sip_call

logger = logging.getLogger("agent.scheduler")


async def start_outbound_scheduler_loop(poll_interval: float = 5.0) -> None:
    """Lightweight background loop that checks SQLite for due scheduled calls every poll_interval seconds."""
    logger.info(f"Starting Outbound Call Scheduler (polling every {poll_interval}s)...")
    while True:
        try:
            due_calls = db.get_due_scheduled_calls()
            for call in due_calls:
                call_id = call["id"]
                name = call["participant_name"]
                phone = call["phone_number"]
                scheduled_at = call["scheduled_at"]

                logger.info(
                    f"[DUE OUTBOUND CALL] ID #{call_id}: {name} ({phone}) scheduled for {scheduled_at}"
                )

                # Update status to COMPLETED in SQLite
                db.update_scheduled_call_status(call_id, "COMPLETED")

                # Initiate SIP call via LiveKit API / Outbound system
                res = await trigger_outbound_sip_call(
                    phone_number=phone, participant_name=name
                )

                # Log to call_logs as Outbound Scheduled Call
                db.log_call_session(
                    call_id=f"SCHED-{call_id}",
                    participant_name=name,
                    channel=f"Outbound SIP ({phone})",
                    duration_seconds=120,
                    exercises_completed=1,
                    failure_reason=""
                    if res.get("status") in ["success", "simulated"]
                    else res.get("message", "SIP Error"),
                )
                logger.info(
                    f"Executed scheduled outbound call for {name} ({phone}): status={res.get('status')}"
                )
        except Exception as e:
            logger.error(f"Error in outbound call scheduler loop: {e}")

        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_outbound_scheduler_loop())
