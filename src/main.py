"""Main entrypoint for the LiveKit medical agent worker (explicit dispatch + SIP + MongoDB)."""
from __future__ import annotations

import logging
import uuid

from livekit import agents
from livekit.agents import AgentSession, CloseEvent, JobContext, WorkerOptions
from livekit.plugins import cartesia, openai, silero
from openai import AsyncOpenAI

from config import (
    AGENT_DISPATCH_NAME,
    CEREBRAS_API_KEY,
    CEREBRAS_BASE_URL,
    EXPECTED_SIP_RULE_ID,
    INBOUND_TRUNK_PHONE,
    LLM_MODEL,
    USE_EXPLICIT_DISPATCH,
)
from medical_agent import MedicalSymptomAgent, RegistrationGateAgent
from patient_store import PatientStore, build_call_record, resolve_patient_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("pymongo").setLevel(logging.WARNING)


def _job_metadata(ctx: JobContext) -> str | None:
    job = getattr(ctx, "job", None)
    if job is None:
        return None
    md = getattr(job, "metadata", None)
    if md is None:
        return None
    return str(md) if md else None


async def _generate_call_summary(conversation_history: list[dict[str, str]]) -> str:
    """Provider-facing paragraph: symptoms + possible differentials (not for patient display)."""
    if not conversation_history:
        return ""

    if not CEREBRAS_API_KEY:
        logger.warning("CEREBRAS_API_KEY missing; using truncated fallback summary")
        return _fallback_summary(conversation_history)

    transcript = "\n".join(
        f'{m["role"]}: {m["content"]}' for m in conversation_history
    )
    client = AsyncOpenAI(api_key=CEREBRAS_API_KEY, base_url=CEREBRAS_BASE_URL)
    try:
        resp = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write concise internal clinical call summaries for healthcare staff. "
                        "Output a single short paragraph. Include: main symptoms, relevant timing, "
                        "and possible differential diagnoses only as hypotheses for clinician review "
                        "(never as a definitive patient diagnosis). "
                        'Begin with: "Internal summary — not a diagnosis:"'
                    ),
                },
                {"role": "user", "content": f"Voice intake transcript:\n{transcript}"},
            ],
            temperature=0.3,
            max_tokens=450,
        )
        out = (resp.choices[0].message.content or "").strip()
        return out if out else _fallback_summary(conversation_history)
    except Exception:
        logger.exception("LLM call for call summary failed; using fallback")
        return _fallback_summary(conversation_history)


def _fallback_summary(conversation_history: list[dict[str, str]]) -> str:
    tail = conversation_history[-10:]
    body = " | ".join(f'{m["role"]}: {m["content"]}' for m in tail)
    return f"Internal summary — not a diagnosis: {body}"


def _messages_from_session_history(session: AgentSession) -> list[dict[str, str]]:
    """Use SDK chat history (final messages only; avoids duplicate streaming lines)."""
    out: list[dict[str, str]] = []
    for msg in session.history.messages():
        text = (msg.text_content or "").strip()
        if not text:
            continue
        if msg.role == "user":
            out.append({"role": "user", "content": text})
        elif msg.role == "assistant":
            out.append({"role": "agent", "content": text})
    return out


async def _persist_registered_call_record(
    patient_id: str,
    call_id: str,
    conversation_history: list[dict[str, str]],
) -> None:
    store = PatientStore()
    summary = await _generate_call_summary(conversation_history)
    if not summary:
        return

    record = build_call_record(
        call_id=call_id,
        patient_id=patient_id,
        transcript=conversation_history,
        summary=summary,
    )
    logger.info(
        "Persisting structured call record to Mongo (patient_id=%s, call_id=%s, %d messages)",
        patient_id,
        call_id,
        len(conversation_history),
    )
    ok = store.append_call_record(patient_id, record)
    if ok:
        logger.info("MongoDB: appended call record for patient_id=%s", patient_id)
    else:
        logger.warning(
            "MongoDB: no document matched patient_id=%r — seed this id in patients collection",
            patient_id,
        )


async def medical_agent_session(ctx: JobContext):
    """Runs per dispatched job (SIP inbound uses explicit agent name, e.g. alexa)."""
    await ctx.connect()

    session_id = str(uuid.uuid4())
    logger.info("Session started: %s", session_id)
    logger.info(
        "Inbound trunk DID (reference): %s — DB patient key uses sip.phoneNumber of the caller",
        INBOUND_TRUNK_PHONE,
    )

    participant = await ctx.wait_for_participant()
    attrs = getattr(participant, "attributes", None) or {}
    sip_phone = attrs.get("sip.phoneNumber")
    rule_id = attrs.get("sip.ruleID")
    if EXPECTED_SIP_RULE_ID and rule_id and rule_id != EXPECTED_SIP_RULE_ID:
        logger.warning(
            "sip.ruleID %s does not match EXPECTED_SIP_RULE_ID %s",
            rule_id,
            EXPECTED_SIP_RULE_ID,
        )

    part_meta = getattr(participant, "metadata", None) or None
    patient_id = resolve_patient_id(
        sip_phone=sip_phone,
        participant_identity=getattr(participant, "identity", "") or "",
        job_metadata=_job_metadata(ctx),
        participant_metadata=str(part_meta) if part_meta else None,
    )
    logger.info(
        "Resolved patient_id=%s (sip=%s, participant.metadata present=%s)",
        patient_id,
        sip_phone,
        bool(part_meta and str(part_meta).strip()),
    )

    store = PatientStore()
    registered = store.is_registered(patient_id)

    if registered:
        agent: MedicalSymptomAgent | RegistrationGateAgent = MedicalSymptomAgent(
            session_id=session_id
        )
        should_persist = True
    else:
        agent = RegistrationGateAgent(session_id=session_id)
        should_persist = False

    session = AgentSession(
        stt=cartesia.STT(),
        llm=openai.LLM.with_cerebras(model=LLM_MODEL),
        tts=cartesia.TTS(),
        vad=silero.VAD.load(),
    )

    state: dict = {
        "should_persist": should_persist,
        "patient_id": patient_id,
        "call_id": session_id,
        "messages_snapshot": None,
    }

    async def _persist_on_job_shutdown(_reason: str) -> None:
        """Runs in the job runner's awaited shutdown phase so Mongo writes finish."""
        if not state["should_persist"]:
            return
        messages: list[dict[str, str]] = state["messages_snapshot"] or []
        if not messages:
            messages = _messages_from_session_history(session)
        if not any(m.get("role") == "user" for m in messages):
            logger.info("No user messages in session history; skipping Mongo append")
            return
        agent.conversation_history = messages
        await _persist_registered_call_record(state["patient_id"], state["call_id"], messages)

    ctx.add_shutdown_callback(_persist_on_job_shutdown)

    @session.on("close")
    def on_session_close(event: CloseEvent) -> None:
        msgs = _messages_from_session_history(session)
        state["messages_snapshot"] = msgs
        agent.conversation_history = msgs
        agent.save_transcript()
        if event.error:
            logger.warning("Session closed with error: %s", event.error)

    await session.start(room=ctx.room, agent=agent)

    if registered:
        await session.generate_reply(
            instructions=(
                "Greet the registered patient warmly. Say you are ready to take their intake "
                "and ask what symptoms or concerns they are calling about today."
            )
        )
    else:
        await session.generate_reply(
            instructions=(
                "Tell the caller they are not registered in the system yet. They must complete "
                "registration before using this line. Be brief and polite. "
                "Then call end_call immediately."
            )
        )


if __name__ == "__main__":
    agent_name = AGENT_DISPATCH_NAME if USE_EXPLICIT_DISPATCH else ""
    logger.info(
        "Dispatch mode: %s | agent_name=%r | Use 'python main.py start' to keep the worker alive.",
        "EXPLICIT" if USE_EXPLICIT_DISPATCH else "AUTO",
        agent_name,
    )
    opts = WorkerOptions(
        entrypoint_fnc=medical_agent_session,
        agent_name=agent_name,
    )
    agents.cli.run_app(opts)
