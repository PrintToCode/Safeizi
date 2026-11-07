"""Safeizi demo agent. It can only act by asking the guard to approve a payment."""
from dataclasses import asdict

from app.guard import handle_payment
from app.verifier import PaymentRequest


async def run_agent(task, page_text, mandate, audit, approvals) -> dict:
    """Safeizi demo agent: free, offline and repeatable. It naively obeys whatever the
    merchant page says (like a prompt-injected agent would). The guard still decides
    every payment, so the result does not depend on which agent is used."""
    import re
    text = page_text or ""
    m = re.search(r'merchant\s+["\']([\w\-]+)["\']', text, re.I) \
        or re.search(r'pay to:\s*([\w\-]+)', text, re.I)
    a = re.search(r'pay\s+(\d+(?:\.\d+)?)\s*(?:USD|EUR)', text, re.I) \
        or re.search(r'price:\s*(\d+(?:\.\d+)?)', text, re.I) \
        or re.search(r'(\d+(?:\.\d+)?)\s*USD', text, re.I)
    if not (m and a):
        return {"reply": "(simulated) Could not find a merchant and price on the page.",
                "steps": [], "simulated": True}
    req = PaymentRequest(amount=float(a.group(1)), merchant=m.group(1),
                         currency="USD", description="Simulated agent purchase")
    out = await handle_payment(mandate, req, audit, approvals, source="agent-simulated")
    return {"reply": f"(simulated agent) Attempted to pay {req.amount} USD to {req.merchant}.",
            "steps": [{"request": asdict(req), "result": out}], "simulated": True}
