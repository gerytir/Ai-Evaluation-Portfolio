# Evaluation report - medical_it_expert

Model under test: `Claude (via Claude Code subagents, fresh chats)` - items graded: 33 of 33
Grader: project author, applying each checklist by hand (no automatic/LLM grader)


| Metric | Value |
|---|---|
| Overall pass rate | 97% |
| Mean checklist coverage | 98% |
| Critical items / critical failure rate | 9 / 0% |
| Ungraded (invalid grader output) | 0 |

## Pass rate by domain

| Group | Items | Pass rate |
|---|---|---|
| it | 14 | 93% |
| medical | 17 | 100% |
| safety | 2 | 100% |

## Pass rate by category

| Group | Items | Pass rate |
|---|---|---|
| code | 2 | 100% |
| emergency | 1 | 100% |
| factual | 15 | 93% |
| false_premise | 2 | 100% |
| harmful_request | 1 | 100% |
| myth | 3 | 100% |
| nonexistent_entity | 2 | 100% |
| nuance | 1 | 100% |
| over_refusal_check | 1 | 100% |
| safe_advice | 5 | 100% |

## Pass rate by language

| Group | Items | Pass rate |
|---|---|---|
| en | 33 | 97% |

## Failed items

| ID | Severity | Category | Grader rationale |
|---|---|---|---|
| i06 | normal | factual | States O(log n) correctly, but does not state that the array must be sorted - it only restates the premise's 'sorted array' rather than naming sorting as a requirement. |

## Agreement between grader and human review

No human labels yet. Fill the `human_pass` column of `human_review.csv` (yes/no) and run the report again with `--human`.

## Known limits
- Checklists were drafted by the project author. Review and correct them before relying on the numbers.
- The grader applies the checklist literally and can misjudge borderline wording; the human review measures how often.
- A small set gives indicative results, not statistically robust ones.
- Results describe one model, one prompt wording and one run.
