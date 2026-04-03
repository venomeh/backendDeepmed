"""Configuration management for the medical agent."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API Keys
CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")

# Database Configuration
DATABASE_PATH = os.environ.get("DATABASE_PATH", "data/medical_reports.db")
DATABASE_DIR = Path(DATABASE_PATH).parent
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# LiveKit Configuration
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")

# LLM Configuration
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b")

# Set API keys in environment for plugins
if CARTESIA_API_KEY:
    os.environ["CARTESIA_API_KEY"] = CARTESIA_API_KEY
if CEREBRAS_API_KEY:
    os.environ["CEREBRAS_API_KEY"] = CEREBRAS_API_KEY

 