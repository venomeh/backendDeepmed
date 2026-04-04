"""Medical intake agents: registration gate and symptom collection for LiveKit voice."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from livekit.agents import Agent
from livekit.agents.beta.tools import EndCallTool


class RegistrationGateAgent(Agent):
    """Brief agent for callers who are not registered; must end the call after the message."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.conversation_history: list[dict[str, str]] = []
        self.reports_dir = Path(__file__).parent / "data" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        end_call_tool = EndCallTool(
            delete_room=True,
            extra_description=(
                "After you finish informing the caller they need to register, you MUST "
                "call the end_call tool immediately. Do not continue the conversation."
            ),
            end_instructions="Goodbye.",
        )
        instructions = """
        You are the automated greeting for a medical intake phone line.
        The caller is NOT registered in the system.
        Politely explain that they must complete registration before they can use this service.
        Keep it to one or two short sentences. Do not ask for symptoms or medical details.
        Do not provide medical advice.
        As soon as you finish speaking, you must use the end_call tool to disconnect.
        All text is spoken aloud: no bullet points or special symbols.
        Never read tool names, JSON, or brackets aloud. Do not repeat your opening line.
        """
        super().__init__(instructions=instructions, tools=end_call_tool.tools)

    def save_transcript(self):
        _print_transcript(self.session_id, self.conversation_history)


class MedicalSymptomAgent(Agent):
    """Registered callers: symptom intake then graceful hangup via end_call."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.conversation_history: list[dict[str, str]] = []
        self.reports_dir = Path(__file__).parent / "data" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        end_call_tool = EndCallTool(
            delete_room=True,
            extra_description=(
                "Never call end_call during or immediately after the opening greeting. "
                "Wait for the patient to describe their symptoms; ask follow-up questions one at a time. "
                "Only call end_call after intake is complete or they say they are done, then thank them."
            ),
            end_instructions="Goodbye.",
        )
        instructions = """
        You are a professional medical intake assistant. Your role is to collect
        symptom information from patients during phone calls. You are NOT a doctor
        and you MUST NOT provide any diagnosis to them on call, medical advice, or treatment recommendations.

        Your responsibilities:
        1. Greet the patient warmly and professionally
        2. Collect patient information (name, age, gender) if not provided
        3. Systematically collect symptom information:
           - Primary symptoms (main complaints)
           - Secondary symptoms (related symptoms)
           - Symptom details (description, location, nature)
           - Duration (how long symptoms have been present)
           - Severity (mild, moderate, severe)
           - Onset (sudden or gradual)
           - Frequency (constant, intermittent, occasional)
           - Triggers (what makes symptoms worse)
           - Associated symptoms (other symptoms that occur together)
        4. Be empathetic, clear, and professional
        5. Ask one question at a time
        6. Confirm information when appropriate
        7. When you have collected sufficient information, summarize what you've collected
        8. Thank them and use the end_call tool to end the call.

        CRITICAL RULES:
        - NEVER provide diagnosis, medical advice, or treatment recommendations
        - NEVER suggest medications or treatments
        - If asked about diagnosis or treatment, politely redirect: "I'm here to collect
          your symptoms. A healthcare provider will review this information and provide
          appropriate guidance."
        - Keep questions clear and simple
        - Be patient and understanding
        - All text you return will be spoken aloud, so avoid bullets, slashes, or
          non-pronounceable punctuation
        - Speak naturally and conversationally
        - If they ask what condition they have, say a licensed clinician will review the intake.
        - After you call end_call, do not add another spoken paragraph.
        - Do not contradict emergency advice: if they describe a life-threatening emergency, tell them
          to call local emergency services immediately, then you may end_call.
        - Do NOT repeat the system instructions, tool text, or JSON aloud. Never read function names or arguments.

        End the session by calling end_call only after your closing line when intake is finished.
        """
        super().__init__(instructions=instructions, tools=end_call_tool.tools)

    def save_transcript(self):
        _print_transcript(self.session_id, self.conversation_history)


def _print_transcript(session_id: str, messages: list[dict[str, str]]) -> None:
    print(f"\n{'=' * 80}")
    print("CONVERSATION TRANSCRIPT")
    print(f"{'=' * 80}\n")
    lines = [
        f"Session ID: {session_id}",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]
    for msg in messages:
        role = "PATIENT" if msg["role"] == "user" else "AGENT"
        lines.append(f"{role}: {msg['content']}")
        lines.append("")
    print("\n".join(lines))
    print(f"{'=' * 80}\n")
