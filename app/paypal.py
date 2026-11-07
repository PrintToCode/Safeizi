import os
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api-m.sandbox.paypal.com"
CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
SECRET = os.getenv("PAYPAL_SECRET", "")


async def get_token() -> str:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"{BASE}/v1/oauth2/token",
            auth=(CLIENT_ID, SECRET),
            data={"grant_type": "client_credentials"},
        )
        r.raise_for_status()
        return r.json()["access_token"]


async def create_order(amount: float, currency: str = "USD",
                       description: str = "Safeizi payment") -> dict:
    """Creates an order. Returns order id, status and the buyer approval link."""
    token = await get_token()
    body = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "description": description,
            "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
        }],
    }
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"{BASE}/v2/checkout/orders",
            json=body,
            headers={
                "Authorization": f"Bearer {token}",
                "PayPal-Request-Id": str(uuid.uuid4()),
            },
        )
        r.raise_for_status()
        data = r.json()
    approve = next(
        (l["href"] for l in data.get("links", [])
         if l["rel"] in ("approve", "payer-action")),
        None,
    )
    return {"id": data["id"], "status": data["status"], "approve_url": approve}


async def capture_order(order_id: str) -> dict:
    """Captures an order. Only works AFTER the buyer approved it."""
    token = await get_token()
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"{BASE}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "PayPal-Request-Id": str(uuid.uuid4()),
            },
        )
        r.raise_for_status()
        return r.json()
