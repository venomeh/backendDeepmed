### DONOT TOUCH THIS FILE OR ANY CODE IT CONTAINS UNLESS YOU KNOW WHAT YOU ARE DOING ###



import os
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions
from livekit.plugins import openai, silero, cartesia
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()



CARTESIA_API_KEY = "sk_car_hufGcdqra7rFLwfnWjRY4F"
CEREBRAS_API_KEY = "csk-c5npx6w2j4y39pkc63vjfn396ccdp5vcwr3hywd22re6twh5"


os.environ["CARTESIA_API_KEY"] = CARTESIA_API_KEY
os.environ["CEREBRAS_API_KEY"] = CEREBRAS_API_KEY

print("✅ Libraries imported and API keys configured")
print("🔑 Make sure to replace 'your_cartesia_api_key_here' and 'your_cerebras_api_key_here' with your actual API keys!")

# !mkdir -p /content/context

# # Download sample Product JSON Data
# !wget -nc -P /content/context \
#      https://gist.githubusercontent.com/ShayneP/f373c26c5166d90446f2bc08baf9bf46/raw/products.json

def load_context():
    """Load all files from context directory"""
    context_dir = Path("context")
    context_dir.mkdir(exist_ok=True)

    all_content = ""
    for file_path in context_dir.glob("*"):
        if file_path.is_file():
            try:
                content = file_path.read_text(encoding='utf-8')
                all_content += f"\n=== {file_path.name} ===\n{content}\n"
            except:
                pass

    return all_content.strip() or "No files found"

print(load_context())
print("✅ Context loading function ready")

class SalesAgent(Agent):
    def __init__(self):
        # Load context once at startup
        context = load_context()
        print(f"📄 Loaded context: {len(context)} characters")

        llm = openai.LLM.with_cerebras(model="llama-3.3-70b")
        stt = cartesia.STT()
        tts = cartesia.TTS()
        vad = silero.VAD.load()

        # Put ALL context in system instructions
        instructions = f"""
        You are a sales agent communicating by voice. All text that you return
        will be spoken aloud, so don't use things like bullets, slashes, or any
        other non-pronouncable punctuation.

        You have access to the following company information:

        {context}

        CRITICAL RULES:
        - ONLY use information from the context above
        - If asked about something not in the context, say "I don't have that information"
        - DO NOT make up prices, features, or any other details
        - Quote directly from the context when possible
        - Be a sales agent but only use the provided information
        """
 
        super().__init__(
            instructions=instructions,
            stt=stt, llm=llm, tts=tts, vad=vad
        )

    # This tells the Agent to greet the user as soon as they join, with some context about the greeting.
    async def on_enter(self):
        self.session.generate_reply(user_input="Give a short, 1 sentence greeting. Offer to answer any questions.")

print("✅ Sales Agent class ready")

from livekit.agents import jupyter

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    agent = SalesAgent()
    session = AgentSession()
    await session.start(room=ctx.room, agent=agent)

jupyter.run_app(
    WorkerOptions(entrypoint_fnc=entrypoint),
    jupyter_url="https://jupyter-api-livekit.vercel.app/api/join-token"
)

