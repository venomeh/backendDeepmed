"""Main entrypoint for the LiveKit medical agent worker."""
import uuid
import asyncio
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, WorkerOptions, CloseEvent, JobContext
from livekit.plugins import openai, silero, cartesia
from config import LLM_MODEL
from medical_agent import MedicalSymptomAgent
from datetime import datetime
from pathlib import Path
import json

load_dotenv()


async def medical_agent_session(ctx: JobContext):
    """Entrypoint function for LiveKit agent worker.
    
    This function is called for each new job/room connection.
    """
    await ctx.connect()
    
    session_id = str(uuid.uuid4())
    print(f"🔗 New session started: {session_id}")
    
    # Create the medical agent instance
    agent = MedicalSymptomAgent(session_id=session_id)
    
    # Create agent session with STT, LLM, TTS, and VAD configuration
    session = AgentSession(
        stt=cartesia.STT(),
        llm=openai.LLM.with_cerebras(model=LLM_MODEL),
        tts=cartesia.TTS(),
        vad=silero.VAD.load(),
    )
    
    # Set up session close event handler to save transcript
    @session.on("close")
    def on_session_close(event: CloseEvent):
        # Save transcript
        agent.save_transcript()
        
        if event.error:
            print(f"⚠️ Session closed with error: {event.error}")
        else:
            print(f"✅ Session {session_id} completed")
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=agent,
    )
    
    # Generate initial greeting
    await session.generate_reply(
        instructions="Greet the patient warmly and professionally. Introduce yourself as a medical intake assistant and ask how you can help them today."
    )


if __name__ == "__main__":
    # Start the LiveKit agent worker
    agents.cli.run_app(WorkerOptions(entrypoint_fnc=medical_agent_session))
