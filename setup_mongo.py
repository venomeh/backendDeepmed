#!/usr/bin/env python3
"""Initialize MongoDB: database, `patients` collection, unique index on `patient_id`.

Run from the `backend-ai` folder:
  python setup_mongo.py
  python setup_mongo.py --seed-patient +15555550100

Requires `MONGODB_URI` or `mongodb_connection_string` in `src/.env`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from config import MONGODB_DB_NAME, MONGODB_PATIENTS_COLLECTION, MONGODB_URI  # noqa: E402
from pymongo import MongoClient  # noqa: E402


def _normalize_e164(phone: str) -> str:
    s = phone.strip()
    if s.startswith("+"):
        rest = "".join(c for c in s[1:] if c.isdigit())
        return f"+{rest}" if rest else s
    rest = "".join(c for c in s if c.isdigit())
    return f"+{rest}" if rest else s


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create DeepMed MongoDB collection and index for the LiveKit agent.",
    )
    parser.add_argument(
        "--seed-patient",
        metavar="PHONE",
        help="Optional E.164 phone to register as a patient with empty call_summaries (for testing)",
    )
    args = parser.parse_args()

    if not MONGODB_URI:
        print(
            "Error: Set MONGODB_URI or mongodb_connection_string in src/.env",
            file=sys.stderr,
        )
        sys.exit(1)

    client = MongoClient(MONGODB_URI)
    coll = client[MONGODB_DB_NAME][MONGODB_PATIENTS_COLLECTION]

    coll.create_index("patient_id", unique=True, name="patient_id_unique")
    print(
        f"OK: unique index 'patient_id_unique' on "
        f"{MONGODB_DB_NAME}.{MONGODB_PATIENTS_COLLECTION}"
    )

    if args.seed_patient:
        phone = _normalize_e164(args.seed_patient)
        r = coll.update_one(
            {"patient_id": phone},
            {"$setOnInsert": {"patient_id": phone, "call_summaries": []}},
            upsert=True,
        )
        if r.upserted_id is not None:
            print(f"OK: seeded patient patient_id={phone!r} (empty call_summaries)")
        else:
            print(f"OK: patient {phone!r} already exists; unchanged")

    client.close()


if __name__ == "__main__":
    main()
