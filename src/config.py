"""Configuration management for the medical agent."""
import os
from pathlib import Path

from dotenv import load_dotenv

_env_dir = Path(__file__).resolve().parent
load_dotenv(_env_dir / ".env")
load_dotenv()

# API Keys
CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")

# LiveKit Configuration
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")

# LLM Configuration
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b")
CEREBRAS_BASE_URL = os.environ.get("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")

# MongoDB (patient_id + call_summaries list)
MONGODB_URI = os.environ.get("MONGODB_URI") or os.environ.get("mongodb_connection_string", "")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "deepmed")
MONGODB_PATIENTS_COLLECTION = os.environ.get("MONGODB_PATIENTS_COLLECTION", "patients")

# Inbound telephony: DID on your LiveKit SIP trunk (for docs / logging). Caller identity for DB is sip.phoneNumber.
INBOUND_TRUNK_PHONE = os.environ.get("INBOUND_TRUNK_PHONE", "+12402314006")

# Optional: set to SDR_... to log a warning when inbound rule id does not match
EXPECTED_SIP_RULE_ID = os.environ.get("EXPECTED_SIP_RULE_ID", "")

# Explicit SIP / token dispatch agent name (must match LiveKit dispatch rule agentName)
AGENT_DISPATCH_NAME = os.environ.get("AGENT_DISPATCH_NAME", "alexa")

# True: worker only joins rooms that explicitly dispatch this agent (SIP + tokens with RoomAgentDispatch).
# False: automatic dispatch — agent joins every new room (simple Meet tokens work; set True for production SIP).
def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


USE_EXPLICIT_DISPATCH = _env_bool("USE_EXPLICIT_DISPATCH", True)

# Set API keys in environment for plugins
if CARTESIA_API_KEY:
    os.environ["CARTESIA_API_KEY"] = CARTESIA_API_KEY
if CEREBRAS_API_KEY:
    os.environ["CEREBRAS_API_KEY"] = CEREBRAS_API_KEY

 