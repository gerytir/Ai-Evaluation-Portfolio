# LLM-as-Judge: A Pairwise Evaluator with Bias Checks

A judge that compares two AI responses with a fixed rubric (accuracy, instruction following, safety, clarity), picks the better one, and justifies the choice. The project then measures **how far the judge itself can be trusted**.

Evaluating the evaluator is the point. A judge that sounds confident but prefers whichever answer comes first, or whichever is longer, is worse than no judge.

## Problem

Teams use LLMs to grade other LLMs because human review does not scale. The risks are known: position bias (preferring slot A), verbosity bias (preferring longer answers), and agreement with humans that is lower than it looks.

## How it works

```
prompt + response A + response B
        |
        +--> judge (A first, B second)  ----> preference 1
        |
        +--> judge (B first, A second)  ----> preference 2 (mapped back)
        |
        v
final verdict: both orders agree -> that verdict; they disagree -> "tie" (position bias)
```

| File | Role |
|---|---|
| `judge.py` | Rubric prompt, strict output validation, two-order judging, final verdict |
| `pairs.json` | 9 labelled pairs: language accuracy, safety (IT and fitness), medical facts, a length-instruction trap, a wrong-but-confident answer, a tie, a false premise, a code error |
| `metrics.py` | Agreement, Cohen's kappa, swap consistency, first-slot bias, score gap |
| `run_eval.py` | Runs the judge on all pairs and writes the report |
| `tests/` | Offline tests with a fake client (no API key needed) |

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="..."
python run_eval.py --limit 3     # quick trial
python run_eval.py               # full evaluation
pytest                           # offline tests
```

## Do this before you run it

The `gold` labels in `pairs.json` were written by the project author. Before you run the judge, **label every pair yourself, blind**: read the two responses and write your own preference in a copy of the file, without looking at the judge's output. Then use your labels. This is the step that turns the project into real evaluation work.

## How it is evaluated

| Metric | What it measures |
|---|---|
| Agreement with gold | How often the judge picks the same winner as the human label |
| Cohen's kappa | The same agreement, corrected for chance |
| Swap consistency | Does the judge give the same answer when the responses are swapped? |
| First-slot bias | Among decisive judgments, how often the first-shown response wins. 0.5 means none. |
| Mean score gap | Does the rubric give the gold winner clearly higher totals? |

## Results

> To be filled in after running `python run_eval.py`. Paste the table from `output/REPORT.md` with model and run date. Do not enter numbers that were not measured.

## Analysis to write up

For every pair where the judge disagrees with the gold label, write one line: judge error, or debatable label? Then add three pairs of your own that are hard (two good answers, or two flawed ones) and see how the judge behaves. Close calls are where evaluation work actually happens.

## Known limits

- Gold labels were written by the project author until you replace them.
- 9 pairs is a very small sample; most pairs have one clearly better answer.
- A judge from the same model family as the evaluated models may favour its own style.
- Only position bias is tested directly. Verbosity bias is covered by one pair (p05).

## Possible improvements

- 50+ pairs with graded difficulty, including near-ties
- Several judge runs per pair, to measure self-consistency
- Compare two judge models, or a judge with and without the rubric
- Add a "reasoning before verdict" variant and test whether it changes agreement
