"""Generate a LiveKit access token for browser testing.

Reads USE_EXPLICIT_DISPATCH from src/.env:
  true  -> token includes RoomAgentDispatch(agent_name) so the named worker is dispatched
  false -> plain token, any auto-dispatch worker will join the room
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from livekit import api

env_path = Path(__file__).parent / "src" / ".env"
load_dotenv(env_path)

ROOM_NAME = os.getenv("LIVEKIT_TEST_ROOM", "test-room")
AGENT_NAME = os.getenv("AGENT_DISPATCH_NAME", "alexa")
TEST_PATIENT_ID = os.getenv("TEST_PATIENT_ID", "+15555550100")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")

_explicit_raw = os.getenv("USE_EXPLICIT_DISPATCH", "true").strip().lower()
USE_EXPLICIT_DISPATCH = _explicit_raw in ("1", "true", "yes", "on")

patient_lookup_json = json.dumps({"patient_id": TEST_PATIENT_ID})

builder = (
    api.AccessToken(
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    )
    .with_identity("patient")
    .with_name("Test Patient")
    .with_metadata(patient_lookup_json)
    .with_grants(
        api.VideoGrants(
            room_join=True,
            room=ROOM_NAME,
            can_publish=True,
            can_subscribe=True,
        )
    )
)

if USE_EXPLICIT_DISPATCH:
    builder = builder.with_room_config(
        api.RoomConfiguration(
            agents=[
                api.RoomAgentDispatch(
                    agent_name=AGENT_NAME,
                    metadata=patient_lookup_json,
                )
            ],
        ),
    )

token = builder.to_jwt()

mode = "EXPLICIT dispatch" if USE_EXPLICIT_DISPATCH else "AUTO dispatch"

print(f"\n{'=' * 70}")
print(f"YOUR LIVEKIT TOKEN  ({mode})")
print("=" * 70)
print(f"\n{token}\n")
print("=" * 70)
print("\nSTEPS:")
print("  1. Copy the token above")
print(f"  2. Run the worker:  cd src && python main.py start")
print(f"  3. Go to: https://meet.livekit.io/custom")
print(f"  4. LiveKit URL:  {LIVEKIT_URL}")
print("  5. Paste the token")
print(f"  6. Room:  {ROOM_NAME}")
print("  7. Connect and enable microphone")
if USE_EXPLICIT_DISPATCH:
    print(f"\n  Dispatch target: agent_name={AGENT_NAME!r}")
else:
    print("\n  Auto-dispatch: agent joins any new room (no agent_name filter)")
print(f"  Patient ID in token: {TEST_PATIENT_ID}")
print(f"\n  Make sure this patient_id exists in MongoDB (run setup_mongo.py --seed-patient {TEST_PATIENT_ID})")
print("=" * 70 + "\n")
