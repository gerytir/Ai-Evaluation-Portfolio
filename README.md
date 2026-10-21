# AI Evaluation Portfolio: Projects

Projects around one question: **how do you know an AI system is reliable?** Each project has code, a labelled evaluation set, offline unit tests (no API key needed) and a README that documents its limits.

## Main projects

| Project | What it is | What it measures |
|---|---|---|
| [llm-eval-lab](llm-eval-lab) | Evaluation toolkit with two datasets: 30 prompts in Italian and 33 in English (medical, IT, safety), plus annotation guidelines | Pass rate by domain and category, critical failures, hallucination traps, over-refusal, agreement between grader and human review |
| [llm-judge-calibration](llm-judge-calibration) | Pairwise LLM judge with a fixed rubric | Agreement with human labels, Cohen's kappa, position bias |

## Other technical projects

| Project | What it is |
|---|---|
| [other-technical-projects/research-agent](other-technical-projects/research-agent) | Web research agent that cites every claim, with a claim-by-claim source check |
| [other-technical-projects/helpdesk-triage-agent](other-technical-projects/helpdesk-triage-agent) | IT ticket triage with deterministic guardrails and prompt-injection tests |

## Quick start

```bash
cd llm-eval-lab             # or any other project folder
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                      # offline tests
export ANTHROPIC_API_KEY="..."
```

Each README explains the evaluation commands.

**First run (`llm-eval-lab`, 2026-10).** The two datasets were run once and graded against their checklists. Responses under test came from Claude in independent fresh chats (one per prompt, none of which saw the checklists); grading was done by hand against each item's criteria, with no paid API. Results: `italian_core` 30/30 passed; `medical_it_expert` 32/33 passed; critical-failure rate 0% in both. Full tables, the raw responses and the gradings are in `llm-eval-lab/output/` and `llm-eval-lab/runs/`; the method and limits are written up in that project's README. The other projects' "Results" sections stay empty until they are run.
