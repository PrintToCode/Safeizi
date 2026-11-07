from app.audit import AuditLog
from app.mandate import create_mandate

audit = AuditLog()
approvals = {}


def default_mandate():
    return create_mandate("Buy a mechanical keyboard", 80, ["techstore"],
                          human_approval_above=50)


class Holder:
    mandate = default_mandate()


holder = Holder()
