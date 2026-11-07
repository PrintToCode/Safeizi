"""Signed spending mandate: what the human authorized the agent to do."""
import hashlib
import hmac
import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone

SECRET = os.getenv("MANDATE_SECRET", "dev-secret-change-me")


@dataclass
class Mandate:
    description: str
    max_amount: float                      # max per payment
    currency: str = "USD"
    allowed_merchants: list = field(default_factory=list)
    human_approval_above: float = None     # above this -> ask the human
    expires_at: str = ""                   # ISO 8601, UTC
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signature: str = ""


def _canonical(m: Mandate) -> bytes:
    data = asdict(m)
    data.pop("signature", None)
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def sign(m: Mandate, secret: str = None) -> Mandate:
    key = (secret or SECRET).encode()
    m.signature = hmac.new(key, _canonical(m), hashlib.sha256).hexdigest()
    return m


def is_signature_valid(m: Mandate, secret: str = None) -> bool:
    key = (secret or SECRET).encode()
    expected = hmac.new(key, _canonical(m), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, m.signature or "")


def create_mandate(description: str, max_amount: float, allowed_merchants: list,
                   currency: str = "USD", human_approval_above: float = None,
                   hours_valid: int = 24, secret: str = None) -> Mandate:
    expires = datetime.now(timezone.utc) + timedelta(hours=hours_valid)
    m = Mandate(
        description=description,
        max_amount=max_amount,
        currency=currency,
        allowed_merchants=[x.lower() for x in allowed_merchants],
        human_approval_above=human_approval_above,
        expires_at=expires.isoformat(),
    )
    return sign(m, secret)
