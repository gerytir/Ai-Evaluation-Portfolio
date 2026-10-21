# Evaluation report - italian_core

Model under test: `Claude (via Claude Code subagents, fresh chats)` - items graded: 30 of 30
Grader: project author, applying each checklist by hand (no automatic/LLM grader)


| Metric | Value |
|---|---|
| Overall pass rate | 100% |
| Mean checklist coverage | 100% |
| Critical items / critical failure rate | 4 / 0% |
| Ungraded (invalid grader output) | 0 |

## Pass rate by domain

| Group | Items | Pass rate |
|---|---|---|
| culture | 8 | 100% |
| language | 19 | 100% |
| safety | 3 | 100% |

## Pass rate by category

| Group | Items | Pass rate |
|---|---|---|
| factual | 3 | 100% |
| false_friend | 1 | 100% |
| false_premise | 2 | 100% |
| grammar | 6 | 100% |
| harmful_request | 2 | 100% |
| idioms | 1 | 100% |
| instruction_following | 1 | 100% |
| nonexistent_entity | 2 | 100% |
| nuance | 1 | 100% |
| numbers_dates | 1 | 100% |
| over_refusal_check | 1 | 100% |
| register | 1 | 100% |
| spelling | 3 | 100% |
| summarization | 1 | 100% |
| tone | 1 | 100% |
| translation | 1 | 100% |
| usage | 2 | 100% |

## Pass rate by language

| Group | Items | Pass rate |
|---|---|---|
| it | 30 | 100% |

## Failed items

| ID | Severity | Category | Grader rationale |
|---|---|---|---|
| - | - | - | none |

## Agreement between grader and independent blind grader (a separate model pass that never saw the author's verdicts)

| Metric | Value |
|---|---|
| Items compared | 30 |
| Agreement | 100% |
| Cohen's kappa | 1.0 |
| Grader passed, reviewer failed | 0 |
| Grader failed, reviewer passed | 0 |

## Known limits
- Checklists were drafted by the project author. Review and correct them before relying on the numbers.
- The grader applies the checklist literally and can misjudge borderline wording; the independent blind grader (a separate model pass that never saw the author's verdicts) measures how often.
- A small set gives indicative results, not statistically robust ones.
- Results describe one model, one prompt wording and one run.
