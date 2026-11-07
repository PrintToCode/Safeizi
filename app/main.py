import os
from dataclasses import asdict

from dotenv import load_dotenv

load_dotenv()  # must run before importing modules that read env vars

from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from app import paypal
from app.agent import run_agent
from app.attacks import run_redteam
from app.mandate import create_mandate
from app.state import audit, approvals, holder

app = FastAPI(title="Safeizi", description="Safety layer for AI agent payments", docs_url=None)

DOCS_CSS = """<style>
body{background:#f1f2f4;font-family:Inter,"Helvetica Neue",Arial,sans-serif}
.swagger-ui,.swagger-ui .opblock-summary-description,.swagger-ui .info p,.swagger-ui label,.swagger-ui .tab li{font-family:Inter,"Helvetica Neue",Arial,sans-serif!important;color:#001435}
.swagger-ui .wrapper{max-width:980px}
.swagger-ui .info{margin:32px 0 16px}.swagger-ui .info .title{font-size:30px;font-weight:700;color:#001435}
.swagger-ui .info .title small{background:#0551b5;border-radius:999px;padding:2px 10px}
.swagger-ui .scheme-container{background:transparent;box-shadow:none;padding:0}
.swagger-ui .opblock{border-radius:16px;border:1px solid #e1e4e8;background:#fff;box-shadow:none;margin:0 0 14px}
.swagger-ui .opblock .opblock-summary{border:0;padding:10px 14px}
.swagger-ui .opblock .opblock-summary-method{border-radius:999px;min-width:72px;font-weight:600}
.swagger-ui .opblock.opblock-post{background:#fff;border-color:#e1e4e8}.swagger-ui .opblock.opblock-post .opblock-summary-method{background:#0551b5}
.swagger-ui .opblock.opblock-get{background:#fff;border-color:#e1e4e8}.swagger-ui .opblock.opblock-get .opblock-summary-method{background:#0a7a45}
.swagger-ui .opblock-section-header{background:#f7f8fa;box-shadow:none}
.swagger-ui input[type=text],.swagger-ui textarea,.swagger-ui select{border:1px solid #9da3ae;border-radius:8px;background:#fff}
.swagger-ui .btn{border-radius:999px;font-weight:600;box-shadow:none;padding:8px 22px}
.swagger-ui .btn.execute{background:#0551b5;border-color:#0551b5;color:#fff}
.swagger-ui .btn.execute:hover{background:#003a9e}
.swagger-ui .btn.try-out__btn{border-color:#0551b5;color:#0551b5}
.swagger-ui .btn.cancel{border-color:#c1243b;color:#c1243b}
.swagger-ui .responses-inner h4,.swagger-ui .opblock-tag{font-weight:600;color:#001435}
.swagger-ui .opblock-tag{border-bottom:1px solid #e1e4e8}
.swagger-ui section.models{border-radius:16px;border:1px solid #e1e4e8;background:#fff}
.swagger-ui .highlight-code>.microlight,.swagger-ui .microlight{border-radius:8px}
</style>"""
WEB = os.path.join(os.path.dirname(__file__), "..", "web", "index.html")


class OrderIn(BaseModel):
    amount: float = Field(gt=0)
    currency: str = "USD"
    description: str = "Safeizi payment"


class MandateIn(BaseModel):
    description: str
    max_amount: float = Field(gt=0)
    allowed_merchants: list[str]
    currency: str = "USD"
    human_approval_above: float | None = None


class AgentIn(BaseModel):
    task: str
    page: str = ""


@app.get("/docs", include_in_schema=False)
def docs():
    page = get_swagger_ui_html(openapi_url="/openapi.json", title="Safeizi API")
    html = page.body.decode("utf-8").replace("</head>", DOCS_CSS + "</head>", 1)
    return HTMLResponse(html)


@app.get("/")
def index():
    return FileResponse(WEB)


@app.get("/health")
def health():
    return {"status": "ok"}


# --- raw PayPal sandbox helpers (day 1 smoke test) ---
@app.post("/orders")
async def create(order: OrderIn):
    try:
        return await paypal.create_order(order.amount, order.currency, order.description)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/orders/{order_id}/capture")
async def capture(order_id: str):
    try:
        return await paypal.capture_order(order_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# --- Safeizi API ---
@app.get("/api/mandate")
def get_mandate():
    return asdict(holder.mandate)


@app.post("/api/mandate")
def set_mandate(body: MandateIn):
    holder.mandate = create_mandate(body.description, body.max_amount,
                                    body.allowed_merchants, body.currency,
                                    body.human_approval_above)
    audit.append("mandate_created", {"mandate_id": holder.mandate.id,
                                     "max_amount": body.max_amount,
                                     "merchants": holder.mandate.allowed_merchants})
    return asdict(holder.mandate)


@app.post("/api/agent/run")
async def agent_run(body: AgentIn):
    try:
        return await run_agent(body.task, body.page, holder.mandate, audit, approvals)
    except Exception as e:
        raise HTTPException(502, str(e))


@app.post("/api/redteam")
async def redteam():
    return await run_redteam(holder.mandate, audit, approvals)


@app.get("/api/approvals")
def list_approvals():
    return list(approvals.values())


@app.post("/api/approvals/{aid}/approve")
async def approve(aid: str):
    a = approvals.get(aid)
    if not a or a["status"] != "pending":
        raise HTTPException(404, "No pending approval with that id")
    r = a["request"]
    try:
        order = await paypal.create_order(r["amount"], r["currency"],
                                          r.get("description") or f"Safeizi payment to {r['merchant']}")
    except Exception as e:
        raise HTTPException(502, str(e))
    a["status"] = "approved"
    a["order"] = order
    audit.append("human_approved", {"approval_id": aid, "order": order})
    return a


@app.post("/api/approvals/{aid}/reject")
def reject(aid: str):
    a = approvals.get(aid)
    if not a or a["status"] != "pending":
        raise HTTPException(404, "No pending approval with that id")
    a["status"] = "rejected"
    audit.append("human_rejected", {"approval_id": aid})
    return a


@app.get("/api/audit")
def get_audit():
    ok, bad = audit.verify()
    return {"valid": ok, "first_bad_index": bad, "entries": audit.entries[-100:][::-1]}
