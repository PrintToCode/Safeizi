# Safeizi - the safety layer for AI agent payments

AI agents are starting to buy things for us, but nobody wants to hand them a credit card.
**Safeizi sits between the agent and PayPal and guarantees that only what the human authorized gets paid.**

```
 user ──signs──▶ Mandate (limits, merchants, currency, expiry)
                    │
 AI agent ──pay()──▶ Guard ──▶ Verifier (deterministic rules + HMAC check)
                       │            │
                       │            ├─ block ───────────▶ audit log (hash-chained)
                       │            ├─ needs human ─────▶ approval queue ─▶ PayPal
                       │            └─ approve ─────────▶ PayPal sandbox order
                       └──────────▶ every decision is written to the audit log
```

## Features
- **Signed mandate:** HMAC-SHA256 over the user's spending rules; any edit invalidates it.
- **Verifier:** signature, expiry, currency, merchant allow-list, amount cap, human-approval threshold.
- **Tamper-evident audit log:** each entry embeds the previous hash; the UI shows chain integrity.
- **Demo agent:** a free, offline agent that naively obeys whatever the merchant page says (like a prompt-injected agent). Its only capability is asking the guard to pay, so every payment goes through the guard.
- **Red Team mode:** simulates a fully compromised agent (recipient redirection, amount inflation,
  currency swap, mandate tampering, expired-mandate replay) and reports how many get blocked,
  plus a control payment to prove legitimate payments are not blocked.
- **PayPal sandbox:** orders are created via the Orders v2 API; buyer approval happens in PayPal.

## Run it
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # fill in PayPal sandbox keys
uvicorn app.main:app --reload
# open http://localhost:8000
python -m pytest -q
```

## Honest limitations
- Sandbox only; no real money moves.
- Red Team attacks go straight to the guard on purpose: they test the firewall itself, not whether
  a given LLM falls for a prompt injection. The agent panel runs a deliberately naive simulated agent, so the demo is free and repeatable; the guard's decision does not depend on which agent is used.
- The mandate is stored in memory and the signing key is a server-side secret (a production version
  would use per-user keys and a database).

Built for the PayPal AI Hackathon.
