import asyncio
import os
import tempfile

from app.attacks import run_redteam
from app.audit import AuditLog
from app.guard import handle_payment
from app.mandate import create_mandate
from app.verifier import PaymentRequest


def setup():
    log = AuditLog(os.path.join(tempfile.mkdtemp(), "a.jsonl"))
    m = create_mandate("Buy a keyboard", 80, ["techstore"], human_approval_above=50)
    return log, m, {}


def test_blocked_is_logged_and_not_executed():
    log, m, ap = setup()
    out = asyncio.run(handle_payment(m, PaymentRequest(500, "techstore"), log, ap, execute=False))
    assert out["status"] == "blocked"
    assert log.entries[-1]["data"]["verdict"] == "block"


def test_human_approval_creates_pending():
    log, m, ap = setup()
    out = asyncio.run(handle_payment(m, PaymentRequest(60, "techstore"), log, ap, execute=False))
    assert out["status"] == "pending_human_approval" and out["approval_id"] in ap


def test_redteam_blocks_everything_and_control_passes():
    log, m, ap = setup()
    r = asyncio.run(run_redteam(m, log, ap))
    assert r["blocked"] == r["total"] == 5
    assert r["control"]["approved"] is True
    assert log.verify()[0]
