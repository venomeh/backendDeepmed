"""Quick token generator for testing the medical agent."""
from livekit import api
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / "src" / ".env"
load_dotenv(env_path)

token = api.AccessToken(
    api_key=os.getenv("LIVEKIT_API_KEY"),
    api_secret=os.getenv("LIVEKIT_API_SECRET")
).with_identity("patient").with_name("Test Patient").with_grants(
    api.VideoGrants(room_join=True, room="test-room", can_publish=True, can_subscribe=True)
).to_jwt()

print("\n" + "="*70)
print("🎫 YOUR LIVEKIT TOKEN")
print("="*70)
print(f"\n{token}\n")
print("="*70)
print("\n📱 TO USE:")
print("1. Copy the token above")
print("2. Go to: https://meet.livekit.io/custom")
print(f"3. LiveKit URL: {os.getenv('LIVEKIT_URL')}")
print("4. Paste the token")
print('5. Room: test-room')
print("6. Connect & enable microphone!")
print("="*70 + "\n")
