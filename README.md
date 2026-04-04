# DEEPMED Voice Agent — LiveKit + MongoDB

AI-powered medical intake agent that handles phone calls and browser sessions. Checks if the caller is a registered patient; if yes, collects symptoms and stores a structured call record in MongoDB; if not, tells them to register and hangs up.

---

## Fresh Device Setup (from scratch)

### 1. Prerequisites

- **Python 3.11+** — https://www.python.org/downloads/
- **Git** — https://git-scm.com/downloads
- **MongoDB Atlas account** (free tier works) — https://www.mongodb.com/cloud/atlas
- **API keys** you'll need:
  - **LiveKit Cloud** — https://cloud.livekit.io (project URL, API key, API secret)
  - **Cartesia** (STT/TTS) — https://play.cartesia.ai
  - **Cerebras** (LLM) — https://cloud.cerebras.ai

### 2. Clone and install

```bash
git clone <your-repo-url>
cd DEEPMED-abdullah/backend-ai

# Create a virtual environment
python -m venv venv

# Activate it
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure environment

Create / edit `src/.env` with your keys:

```env
CARTESIA_API_KEY=sk_car_XXXXX
CEREBRAS_API_KEY=csk-XXXXX

LIVEKIT_URL=wss://YOUR-PROJECT.livekit.cloud
LIVEKIT_API_KEY=APIXXXXX
LIVEKIT_API_SECRET=XXXXX

LLM_MODEL=qwen-3-235b-a22b-instruct-2507

mongodb_connection_string=mongodb+srv://USER:PASS@cluster.mongodb.net/

USE_EXPLICIT_DISPATCH=true
TEST_PATIENT_ID=+15555550100
```

| Variable | Purpose |
|----------|---------|
| `CARTESIA_API_KEY` | Speech-to-text and text-to-speech |
| `CEREBRAS_API_KEY` | LLM for conversation and summary generation |
| `LIVEKIT_URL` | Your LiveKit Cloud project WebSocket URL |
| `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` | LiveKit authentication |
| `LLM_MODEL` | Cerebras model name (check their dashboard for available models) |
| `mongodb_connection_string` | MongoDB Atlas connection string |
| `USE_EXPLICIT_DISPATCH` | `true` for SIP/phone calls; both token and worker must match |
| `TEST_PATIENT_ID` | Phone number used by `get_token.py` for browser tests |

### 4. Download model files

```bash
cd src
python main.py download-files
```

This downloads Silero VAD weights (one-time).

### 5. Set up MongoDB

```bash
cd backend-ai
python setup_mongo.py --seed-patient +15555550100
```

This creates the `deepmed.patients` collection with a unique index on `patient_id` and seeds a test patient.

To register real phone numbers:

```bash
python setup_mongo.py --seed-patient +923232613642
python setup_mongo.py --seed-patient +923219668571
```

### 6. Run the agent

```bash
cd backend-ai/src
python main.py start
```

Wait for `registered worker` in the logs. The worker stays alive until you close the terminal.

---

## Testing

### Browser test

Terminal 1 (generate token):
```bash
cd backend-ai
python get_token.py
```

Terminal 2 (start worker):
```bash
cd backend-ai/src
python main.py start
```

Then go to https://meet.livekit.io/custom, paste the LiveKit URL and token, set room to `test-room`, connect with microphone.

### Phone test

Make sure `USE_EXPLICIT_DISPATCH=true` in `src/.env` and the worker is running. Call the phone number configured on your LiveKit SIP trunk. Registered callers get the full intake; unregistered callers are told to register and the call ends.

---

## What gets stored in MongoDB

Each patient document:

```json
{
  "patient_id": "+923232613642",
  "call_summaries": [
    {
      "call_id": "a1b2c3d4-e5f6-...",
      "timestamp": "2026-04-04T18:30:00+00:00",
      "patient_id": "+923232613642",
      "transcript": [
        { "role": "agent", "content": "Hello, I'm your medical intake assistant. What symptoms are you experiencing today?" },
        { "role": "patient", "content": "I've been having a severe headache for the past three days." },
        { "role": "agent", "content": "I'm sorry to hear that. Can you describe the location of the headache?" },
        { "role": "patient", "content": "It's mostly on the right side, behind my eye." }
      ],
      "summary": "Internal summary — not a diagnosis: Patient reports a 3-day history of severe right-sided headache localized behind the eye...",
      "message_count": 12
    }
  ]
}
```

You can copy-paste any call record from MongoDB and it reads as a clean, structured clinical document with the full transcript and an AI-generated summary.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Address already in use` on port 8081 | Kill the old process: `netstat -ano \| Select-String ":8081"` then `taskkill /F /PID <pid>` |
| Worker exits immediately | Check `.env` — API keys, LLM model name, MongoDB URI |
| Agent joins but doesn't speak | LLM model in `.env` may be invalid. Check Cerebras dashboard. |
| Patient treated as unregistered | Caller's E.164 phone number must match MongoDB exactly. Seed it: `python setup_mongo.py --seed-patient +theNumber` |
| Worker shuts down after 60 seconds | Use `python main.py start`, **not** `python main.py dev` |

## Project structure

```
backend-ai/
├── src/
│   ├── .env              # API keys and configuration
│   ├── main.py           # Worker entrypoint — session lifecycle, persistence
│   ├── medical_agent.py  # Agent classes (RegistrationGateAgent, MedicalSymptomAgent)
│   ├── patient_store.py  # MongoDB operations — registration check, call record storage
│   └── config.py         # Loads .env, exports all configuration constants
├── get_token.py          # Generates LiveKit access tokens for browser testing
├── setup_mongo.py        # Initializes MongoDB collection, indexes, seeds patients
└── requirements.txt      # Python dependencies
```
