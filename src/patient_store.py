"""MongoDB access for registered patients and per-call summaries."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection

from config import (
    MONGODB_DB_NAME,
    MONGODB_PATIENTS_COLLECTION,
    MONGODB_URI,
)

logger = logging.getLogger(__name__)

_client: MongoClient | None = None


def _get_collection() -> Collection[Any]:
    global _client
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI or mongodb_connection_string is not set in the environment")
    if _client is None:
        _client = MongoClient(MONGODB_URI)
    return _client[MONGODB_DB_NAME][MONGODB_PATIENTS_COLLECTION]


def normalize_phone_e164(phone: str) -> str:
    """Normalize to E.164-style string with leading + and digits."""
    s = phone.strip()
    if not s:
        return s
    if s.startswith("+"):
        rest = "".join(c for c in s[1:] if c.isdigit())
        return f"+{rest}" if rest else s
    rest = "".join(c for c in s if c.isdigit())
    return f"+{rest}" if rest else s


def _patient_id_from_metadata_json(meta_str: str | None, source: str) -> str | None:
    if not meta_str or not str(meta_str).strip():
        return None
    try:
        meta: dict[str, Any] = json.loads(meta_str)
    except json.JSONDecodeError:
        logger.warning("%s metadata is not valid JSON; ignoring", source)
        return None
    for key in ("patient_id", "phone", "patient_phone"):
        raw = meta.get(key)
        if raw is None or not str(raw).strip():
            continue
        val = str(raw).strip()
        if key in ("phone", "patient_phone"):
            return normalize_phone_e164(val)
        digits = "".join(c for c in val if c.isdigit())
        if len(digits) >= 7:
            return normalize_phone_e164(val)
        return val
    return None


def resolve_patient_id(
    *,
    sip_phone: str | None,
    participant_identity: str,
    job_metadata: str | None,
    participant_metadata: str | None = None,
) -> str:
    """
    Prefer SIP caller id (sip.phoneNumber). Then agent job metadata, then **participant**
    token metadata (browser / Meet). Else participant identity.
    """
    if sip_phone:
        return normalize_phone_e164(sip_phone)
    for label, raw in (
        ("job", job_metadata),
        ("participant", participant_metadata),
    ):
        pid = _patient_id_from_metadata_json(raw, label)
        if pid:
            return pid
    return (participant_identity or "unknown").strip()


def build_call_record(
    *,
    call_id: str,
    patient_id: str,
    transcript: list[dict[str, str]],
    summary: str,
) -> dict[str, Any]:
    """Build a structured call record ready for MongoDB storage.

    Document structure (when copied out of Mongo it reads as a clean report):
    {
        "call_id":    "uuid",
        "timestamp":  "2026-04-04T18:30:00Z",
        "patient_id": "+923232613642",
        "transcript": [
            { "role": "agent", "content": "Hello, how can I help?" },
            { "role": "patient", "content": "I have a headache." },
            ...
        ],
        "summary":    "Internal summary — not a diagnosis: ...",
        "message_count": 12
    }
    """
    return {
        "call_id": call_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "patient_id": patient_id,
        "transcript": [
            {"role": "patient" if m["role"] == "user" else "agent", "content": m["content"]}
            for m in transcript
        ],
        "summary": summary,
        "message_count": len(transcript),
    }


class PatientStore:
    """Patients collection: documents { patient_id: str, call_summaries: [...] }."""

    def is_registered(self, patient_id: str) -> bool:
        if not MONGODB_URI:
            logger.warning("MongoDB URI missing; treating caller as not registered")
            return False
        try:
            coll = _get_collection()
            return coll.find_one({"patient_id": patient_id}, {"_id": 1}) is not None
        except Exception:
            logger.exception("MongoDB is_registered failed")
            return False

    def append_call_record(self, patient_id: str, record: dict[str, Any]) -> bool:
        """Push a structured call record into the patient's call_summaries array."""
        if not MONGODB_URI:
            logger.error("MongoDB URI missing; cannot append call record")
            return False
        try:
            coll = _get_collection()
            result = coll.update_one(
                {"patient_id": patient_id},
                {"$push": {"call_summaries": record}},
            )
            return result.matched_count > 0
        except Exception:
            logger.exception("MongoDB append_call_record failed")
            return False
