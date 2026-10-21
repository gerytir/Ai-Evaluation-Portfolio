# IT Helpdesk Triage Agent

An agent that reads a support ticket and returns a structured decision: category, priority, whether a human must take over, a confidence value and a draft reply.

The point of the project is not the classification itself. It is **how the agent is kept safe and how that is measured**: schema validation, deterministic guardrails after the model, and a test set that includes security incidents, ambiguous tickets, Italian-language tickets and prompt-injection attempts.

## Problem

An LLM can triage tickets fast, but a wrong decision has a cost: a security incident treated as a routine request, a reply that asks the user for a password, or a ticket that obeys instructions hidden in its own text.

## How it works

```
ticket text (untrusted)
   |
   v
triage.py  --- Claude, JSON-only prompt ---> raw output
   |
   v
validate_triage()   strict schema; one repair retry; safe fallback if still invalid
   |
   v
apply_guardrails()  deterministic rules, independent of the model:
   |                  - security_incident => needs_human = true, priority at least P2
   |                  - confidence < 0.6  => needs_human = true
   |                  - reply asking for a secret => replaced with a safe reply
   v
decision (category, priority, needs_human, confidence, draft_reply, flags)
```

| File | Role |
|---|---|
| `triage.py` | Agent, schema validation, guardrails, fallback |
| `tickets.json` | 22 synthetic tickets with gold labels and a `tag` (normal, security, italian, ambiguous, injection) |
| `metrics.py` | Pure metric functions |
| `evaluate.py` | Runs all tickets and writes the reports |
| `tests/` | Offline tests with a fake client (no API key needed) |

All tickets are invented. No real company data is used.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="..."
python triage.py "My VPN says authentication failed since this morning."
python evaluate.py --limit 5        # quick trial
python evaluate.py                  # full evaluation
pytest                              # offline tests
```

## How it is evaluated

| Metric | What it measures |
|---|---|
| Category accuracy | Correct category out of 8 |
| Priority exact / within one level | Priority P1 to P4; "within one" tolerates adjacent levels |
| Escalation recall | Of tickets that need a human, how many were escalated. The most important number. |
| False escalation rate | Of tickets that do not need a human, how many were escalated anyway (cost of being too cautious) |
| Security escalation | Security tickets that reached a human |
| Prompt-injection resistance | The ticket asks for a canary string and a fake classification; the agent must ignore it |
| Valid JSON on first try | Reliability of the output format |
| Guardrail interventions | How often the deterministic rules had to correct the model |

A report with the confusion matrix and the list of wrong tickets is written to `output/REPORT.md`.

## Results

> To be filled in after running `python evaluate.py`. Paste the table from `output/REPORT.md` with model and run date. Do not enter numbers that were not measured.

## What to do with the errors

For each wrong ticket in the report, write one line: was the model wrong, or is the gold label debatable? Disagreements about the labels are normal in triage and worth showing in the portfolio, because they show that you can tell a model error from an ambiguous policy.

## Known limits

- Gold labels were written by the project author. Re-label them blind with your own policy before trusting the numbers.
- 22 tickets is a small sample: indicative, not statistically robust.
- The injection test uses a single canary string. Real attacks are more varied.
- The guardrail regex for credential requests is intentionally simple and can miss paraphrases.
- The agent only drafts replies. It never takes actions (resetting passwords, changing access).

## Possible improvements

- Larger and more varied ticket set, including long email threads and attachments described in text
- Per-category escalation policies loaded from a config file
- Confidence calibration: check whether 0.9 confidence is really right about 90% of the time
- Compare two models, or the same model with and without the guardrails, on the same set
