from app.mandate import create_mandate
from app.verifier import verify, PaymentRequest, APPROVE, BLOCK, NEEDS_HUMAN

S = "test-secret"


def mk():
    return create_mandate("Buy a keyboard", 80, ["techstore"], human_approval_above=50, secret=S)


def test_approve():
    assert verify(mk(), PaymentRequest(30, "TechStore"), S).verdict == APPROVE


def test_needs_human():
    assert verify(mk(), PaymentRequest(60, "techstore"), S).verdict == NEEDS_HUMAN


def test_block_amount():
    assert verify(mk(), PaymentRequest(500, "techstore"), S).verdict == BLOCK


def test_block_merchant():
    assert verify(mk(), PaymentRequest(30, "evil-shop"), S).verdict == BLOCK


def test_block_currency():
    assert verify(mk(), PaymentRequest(30, "techstore", "EUR"), S).verdict == BLOCK


def test_tampered_mandate_blocked():
    m = mk()
    m.max_amount = 99999
    d = verify(m, PaymentRequest(5000, "techstore"), S)
    assert d.verdict == BLOCK and "tampering" in d.reasons[0]
