import copy
import os
import tempfile

from app.audit import AuditLog, verify_entries


def mk():
    return AuditLog(os.path.join(tempfile.mkdtemp(), "a.jsonl"))


def test_chain_valid():
    log = mk()
    for i in range(5):
        log.append("evt", {"i": i})
    assert log.verify() == (True, None)


def test_tamper_detected():
    log = mk()
    for i in range(5):
        log.append("evt", {"amount": i})
    entries = copy.deepcopy(log.entries)
    entries[2]["data"]["amount"] = 9999
    ok, bad = verify_entries(entries)
    assert not ok and bad == 2


def test_persistence():
    log = mk()
    log.append("a", {"x": 1})
    log.append("b", {"x": 2})
    again = AuditLog(log.path)
    assert len(again.entries) == 2 and again.verify()[0]
