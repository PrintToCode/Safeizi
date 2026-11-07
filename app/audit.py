"""Tamper-evident audit log: each entry includes the hash of the previous one."""
import hashlib
import json
import os
import threading
from datetime import datetime, timezone

GENESIS = "0" * 64
FIELDS = ("index", "ts", "event", "data", "prev_hash")


def _hash(entry: dict) -> str:
    payload = {k: entry[k] for k in FIELDS}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def verify_entries(entries: list):
    """Returns (ok, first_bad_index)."""
    prev = GENESIS
    for i, e in enumerate(entries):
        if e.get("prev_hash") != prev or _hash(e) != e.get("hash"):
            return False, i
        prev = e["hash"]
    return True, None


class AuditLog:
    def __init__(self, path: str = "data/audit.jsonl"):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.entries = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.entries = [json.loads(line) for line in f if line.strip()]

    def append(self, event: str, data: dict) -> dict:
        with self._lock:
            prev = self.entries[-1]["hash"] if self.entries else GENESIS
            e = {
                "index": len(self.entries),
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "data": data,
                "prev_hash": prev,
            }
            e["hash"] = _hash(e)
            self.entries.append(e)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(e) + "\n")
            return e

    def verify(self):
        return verify_entries(self.entries)
