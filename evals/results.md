# Eval results

Generated 2026-10-25 23:38 UTC by `scripts/run_evals.py`. Model `claude-sonnet-5-5`, effort `medium`. Client `c1`, 15 questions, 3 runs.

_Sample form: Coalition Cyber Policy 3.0 specimen (form CYUSP-00PF-1022-01, 2022). Not a current Coalition policy. Indications are mock data._

## Summary

| | Run 1 | Run 2 | Run 3 | All runs |
|---|---|---|---|---|
| Questions passing all checks | 15/15 | 15/15 | 15/15 | 45/45 (100%) |
| Citation accuracy | 10/10 | 10/10 | 10/10 | 30/30 |
| Correct routing | 15/15 | 15/15 | 15/15 | 45/45 |
| Quote awareness | 1/1 | 1/1 | 1/1 | 3/3 |
| No invented coverage | 15/15 | 15/15 | 15/15 | 45/45 |
| Key facts | 10/10 | 10/10 | 10/10 | 30/30 |

Cost: $0.66 for 45 questions ($0.0146 per question). Mean latency 3.3s. Validation retries: 0.

Key facts: 36 fact checks, 33 matched by wording, 3 sent to the grader model (`claude-haiku-5-5`, $0.0003 total). Citations relabeled by the verifier: 0.

## Per question

| ID | Question | Expected | Run 1 | Run 2 | Run 3 | Failed checks |
|---|---|---|---|---|---|---|
| q01 | If my client gets hit with ransomware, will this pay the ransom? | answer | pass | pass | pass |  |
| q02 | Does it cover lost income if their systems go down after an attack? | answer | pass | pass | pass |  |
| q03 | An employee wired $40,000 to a fake vendor after a spoofed email. Is that covered? | answer | pass | pass | pass |  |
| q04 | After a breach, does it pay to notify customers and give them credit monitoring? | answer | pass | pass | pass |  |
| q05 | If customers sue because their data was stolen, does the policy defend them? | answer | pass | pass | pass |  |
| q06 | If a flood takes out their server room, is that covered here? | answer | pass | pass | pass |  |
| q07 | The power company has an outage and the business loses a day. Does cyber cover that? | answer | pass | pass | pass |  |
| q08 | Malware bricked their laptops. Will the policy pay to replace them? | answer | pass | pass | pass |  |
| q09 | An employee's personal phone got hacked. Is that covered? | answer | pass | pass | pass |  |
| q10 | Someone set up a fake website pretending to be my client. Are they covered? | answer | pass | pass | pass |  |
| q11 | Does my client need multi-factor authentication to get this policy? | route_to_cpl | pass | pass | pass |  |
| q12 | How much more would it cost to go up to a $2 million limit? | route_to_cpl | pass | pass | pass |  |
| q13 | Is this better than the cyber coverage already in their business owner's policy? | route_to_cpl | pass | pass | pass |  |
| q14 | How fast does Coalition pay out a ransomware claim? | route_to_cpl | pass | pass | pass |  |
| q15 | Can we write this for a client in New York? | route_to_cpl | pass | pass | pass |  |

## Failures

None.

## Grader-model decisions on key facts

Facts the wording check missed, judged by the grader model. Listed in full so they can be audited.

| Question | Run | Fact | Stated? | Evidence from the answer |
|---|---|---|---|---|
| q06 | 3 | not covered / would not be covered / excludes / excluded | yes | Generally no. The Natural Disaster exclusion removes anything arising out of a physical event such as fire, flood or earthquake |
| q08 | 1 | prior written consent | yes | The agent should confirm ... that written consent is obtained from the carrier before spending. |
| q09 | 3 | not used for the business / not use for the business / not used for business | yes | does not use for the named insured's business operations |

## Citations relabeled by the verifier

Quotes that are real policy text but were labeled with the wrong section. The verifier moved each to the one section that contains it, so the agent sees a correct citation.

None.

## Scoring notes

- **Citation accuracy** applies to questions expected to be answered: no citation rejected by the verifier, and at least one cited section in `expected_sections`. A citation the verifier relabeled counts as passing, because the agent sees the corrected section.
- **No invented coverage** is checked against the answer text only (not the drafted CPL message), per the spec, by case-insensitive substring matching after normalizing hyphens, contractions, number words and dollar formats. It can't tell a negated phrase from an asserted one.
- **Key facts** are matched the same way first. A fact the wording misses goes to a grader model (`claude-haiku-5-5`), which judges whether the answer states it in meaning. A `must_include` fact given as a list passes if any of its phrasings appears.
- A question passes when every applicable check passes.
- Earlier runs: `evals/results_baseline.md` (first eval), `evals/results_routing_fix.md` (after the Q&A routing fix), `evals/results_quote_trim.md` (after quote trimming, before relabeling and the grader model).
- Raw answers: `evals/runs/run_<n>.json`.
