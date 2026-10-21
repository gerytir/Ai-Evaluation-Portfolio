# Research Agent with Verifiable Citations

An agent that answers questions by searching the web and **cites every claim**. A second pass checks, claim by claim, whether the passage cited by the source really supports what the agent wrote.

The goal is not "make an LLM answer". It is to **measure how verifiable its answers are**.

## Problem

AI assistants produce fluent answers even when the source does not say what they claim. A research agent is only useful if a reader can check every statement.

## How it works

```
question
   |
   v
agent.py  --- web search (built-in API tool) ---> answer in blocks
   |                                               with citations
   v
parse_content()  splits: cited claims | text without a source
   |
   v
verify.py  LLM judge: "does the cited passage support the claim?"
   |            -> supported / partial / unsupported
   v
evaluate.py  metrics on 10 questions + files for human review
```

| File | Role |
|---|---|
| `agent.py` | Research agent, claim and source extraction, numbered-notes output |
| `verify.py` | Judge that sees only the claim and the cited passage (no outside knowledge) |
| `metrics.py` | Pure metric functions, tested offline |
| `evaluate.py` | Runs the evaluation set and writes the reports |
| `eval_set.json` | 8 answerable questions + 2 trap questions (non-existent or future information) |
| `tests/` | Unit tests that need neither network nor API key |

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="..."        # your key
python agent.py "What is the GDPR?"
python evaluate.py --limit 3          # quick trial
python evaluate.py                    # full evaluation
pytest                                # offline tests
```

Optional variables: `MODEL`, `JUDGE_MODEL`, `MAX_SEARCHES`.

Prerequisite: web search must be enabled for your organization in the Claude Console. If the first call fails with a tool-type error, check the current name of the web search tool in the official API documentation.

## How it is evaluated

| Metric | What it measures |
|---|---|
| Citation rate | Share of statements that have a source |
| Supported / partial / unsupported | Judge verdict on the cited passage |
| Keyword coverage | Did the agent touch the essential points of the question? |
| Traps handled | Faced with a question that has no findable answer, does the agent say so instead of inventing? |
| Average searches | Operating cost per question |

The two trap questions (an invented company and a future figure) measure the most important behaviour: **refusing when the sources are not enough**.

## Results

> To be filled in after running `python evaluate.py`. Paste the table from `output/REPORT.md`, with model and run date. Do not enter numbers that were not measured.

## Human review

`output/manual_review.csv` lists every claim with its source and the judge's verdict. Fill the `human_verdict` column (supported / partial / unsupported) for at least 20 claims and compute the agreement with the judge. That figure says how far the measurement itself can be trusted, and it is the bridge to the `llm-judge-calibration` project.

## Known limits

- The judge is an LLM and can be wrong, which is why human review exists.
- Refusal on traps is detected with keywords, so it is approximate.
- It checks that the source says what the agent claims, not that the source is correct.
- Web results change over time: two runs can differ.
- 10 questions is a small sample: indicative, not statistically robust.

## Possible improvements

- Extend the set to 50+ questions across more categories (numbers, dates, definitions, conflicting sources)
- Run each question several times and measure variability
- Add a source reliability check (institutional domain vs blog)
- Compare two models on the same set
