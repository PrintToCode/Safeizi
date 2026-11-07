"""Single choke point: every payment goes through handle_payment()."""
import uuid
from dataclasses import asdict

from app.verifier import verify, PaymentRequest, BLOCK, NEEDS_HUMAN


async def handle_payment(mandate, req: PaymentRequest, audit, approvals: dict,
                         execute: bool = True, source: str = "agent") -> dict:
    d = verify(mandate, req)
    audit.append("payment_request", {
        "source": source,
        "mandate_id": mandate.id,
        "request": asdict(req),
        "verdict": d.verdict,
        "reasons": d.reasons,
    })

    if d.verdict == BLOCK:
        return {"status": "blocked", "reasons": d.reasons}

    if d.verdict == NEEDS_HUMAN:
        aid = str(uuid.uuid4())[:8]
        approvals[aid] = {"id": aid, "request": asdict(req), "status": "pending",
                          "reasons": d.reasons}
        return {"status": "pending_human_approval", "approval_id": aid,
                "reasons": d.reasons}

    if not execute:
        return {"status": "approved", "dry_run": True, "reasons": d.reasons}

    from app import paypal  # lazy import: only needed for real payments
    order = await paypal.create_order(req.amount, req.currency,
                                      req.description or f"Safeizi payment to {req.merchant}")
    audit.append("order_created", {"source": source, "order": order})
    return {"status": "approved", "order": order, "reasons": d.reasons}
