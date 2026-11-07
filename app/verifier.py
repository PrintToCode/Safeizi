"""Deterministic rules: every payment the agent wants must pass through here."""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.mandate import Mandate, is_signature_valid

APPROVE, BLOCK, NEEDS_HUMAN = "approve", "block", "needs_human"


@dataclass
class PaymentRequest:
    amount: float
    merchant: str
    currency: str = "USD"
    description: str = ""


@dataclass
class Decision:
    verdict: str
    reasons: list = field(default_factory=list)


def verify(m: Mandate, req: PaymentRequest, secret: str = None) -> Decision:
    reasons = []

    if not is_signature_valid(m, secret):
        return Decision(BLOCK, ["Mandate signature invalid (possible tampering)"])

    if m.expires_at and datetime.fromisoformat(m.expires_at) < datetime.now(timezone.utc):
        reasons.append("Mandate expired")

    if req.amount <= 0:
        reasons.append("Amount must be positive")

    if req.currency != m.currency:
        reasons.append(f"Currency {req.currency} not allowed (expected {m.currency})")

    if req.merchant.lower() not in m.allowed_merchants:
        reasons.append(f"Merchant '{req.merchant}' is not in the allowed list")

    if req.amount > m.max_amount:
        reasons.append(f"Amount {req.amount} exceeds limit {m.max_amount}")

    if reasons:
        return Decision(BLOCK, reasons)

    if m.human_approval_above is not None and req.amount > m.human_approval_above:
        return Decision(NEEDS_HUMAN, [f"Amount above {m.human_approval_above}: human approval required"])

    return Decision(APPROVE, ["Payment matches the mandate"])
