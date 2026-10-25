# Eval results

Generated 2026-10-25 15:12 UTC by `scripts/run_evals.py`. Model `claude-sonnet-5-5`, effort `medium`. Client `c1`, 15 questions, 3 runs.

_Sample form: Coalition Cyber Policy 3.0 specimen (form CYUSP-00PF-1022-01, 2022). Not a current Coalition policy. Indications are mock data._

## Summary

| | Run 1 | Run 2 | Run 3 | All runs |
|---|---|---|---|---|
| Questions passing all checks | 13/15 | 14/15 | 14/15 | 41/45 (91%) |
| Citation accuracy | 10/10 | 10/10 | 10/10 | 30/30 |
| Correct routing | 15/15 | 15/15 | 15/15 | 45/45 |
| Quote awareness | 1/1 | 1/1 | 1/1 | 3/3 |
| No invented coverage | 15/15 | 15/15 | 15/15 | 45/45 |
| Key facts | 8/10 | 9/10 | 9/10 | 26/30 |

Cost: $0.60 for 45 questions ($0.0134 per question). Mean latency 3.5s. Validation retries: 1.

## Per question

| ID | Question | Expected | Run 1 | Run 2 | Run 3 | Failed checks |
|---|---|---|---|---|---|---|
| q01 | If my client gets hit with ransomware, will this pay the ransom? | answer | pass | pass | pass |  |
| q02 | Does it cover lost income if their systems go down after an attack? | answer | pass | pass | pass |  |
| q03 | An employee wired $40,000 to a fake vendor after a spoofed email. Is that covered? | answer | pass | pass | pass |  |
| q04 | After a breach, does it pay to notify customers and give them credit monitoring? | answer | pass | pass | pass |  |
| q05 | If customers sue because their data was stolen, does the policy defend them? | answer | pass | pass | pass |  |
| q06 | If a flood takes out their server room, is that covered here? | answer | pass | **FAIL** | pass | Key facts |
| q07 | The power company has an outage and the business loses a day. Does cyber cover that? | answer | pass | pass | pass |  |
| q08 | Malware bricked their laptops. Will the policy pay to replace them? | answer | pass | pass | **FAIL** | Key facts |
| q09 | An employee's personal phone got hacked. Is that covered? | answer | **FAIL** | pass | pass | Key facts |
| q10 | Someone set up a fake website pretending to be my client. Are they covered? | answer | **FAIL** | pass | pass | Key facts |
| q11 | Does my client need multi-factor authentication to get this policy? | route_to_cpl | pass | pass | pass |  |
| q12 | How much more would it cost to go up to a $2 million limit? | route_to_cpl | pass | pass | pass |  |
| q13 | Is this better than the cyber coverage already in their business owner's policy? | route_to_cpl | pass | pass | pass |  |
| q14 | How fast does Coalition pay out a ransomware claim? | route_to_cpl | pass | pass | pass |  |
| q15 | Can we write this for a client in New York? | route_to_cpl | pass | pass | pass |  |

## Failures

### q06, run 2: If a flood takes out their server room, is that covered here?

- **Failed:** Key facts
- **Answer:** Generally no. The Natural Disaster exclusion removes coverage for amounts arising out of any physical event or natural disaster, with flood named specifically. The Tangible Property exclusion also removes damage to or loss of use of tangible property, and its only carve-out is for Computer Replacement and Bricking, which covers hardware impacted by a loss of firmware integrity from a security failure, not flood damage. The agent should confirm the client understands that physical damage to server hardware from a flood would typically need property or equipment coverage elsewhere.
- **Cited:** III.L, III.R, IX.Computer replacement costs (expected any of: III.L)
- **in_policy_not_on_quote:** False
- **Missing facts:** not covered / would not be covered / excludes / excluded

### q08, run 3: Malware bricked their laptops. Will the policy pay to replace them?

- **Failed:** Key facts
- **Answer:** Yes, potentially. Computer Replacement and Bricking (II.M) pays reasonable and necessary costs to restore or replace hardware owned or leased by the client that is impacted by a loss of firmware integrity from a security failure, and this quote shows a $1,000,000 limit with a $2,500 retention. The tangible property exclusion has an exception for this coverage, so bricked hardware is not excluded here. The agent should confirm the malware caused a loss of firmware integrity, that the laptops are business-owned or leased (not employee-owned and unused for business), and that the carrier gives written consent before replacement costs are incurred.
- **Cited:** II.M, IX.Computer replacement costs, III.R, DEC.Item5 (expected any of: II.M, IX.Computer replacement costs, III.R)
- **in_policy_not_on_quote:** False
- **Missing facts:** prior written consent

### q09, run 1: An employee's personal phone got hacked. Is that covered?

- **Failed:** Key facts
- **Answer:** It depends on how the phone is used. The definition of security failure excludes computers, peripherals and mobile devices that an employee owns or leases and does not use for the practice's business operations, so a hack of a purely personal phone is not a security failure. Computer systems do include mobile devices, though, so if the phone is used for the practice's business (for example, to access practice email or patient data), a hack may qualify. The agent should confirm whether staff use personal phones for practice work.
- **Cited:** IX.Security failure, IX.Computer systems (expected any of: IX.Security failure)
- **in_policy_not_on_quote:** False
- **Missing facts:** not used for the business / not use for the business / not used for business

### q10, run 1: Someone set up a fake website pretending to be my client. Are they covered?

- **Failed:** Key facts
- **Answer:** The form covers this under Impersonation Repair Costs (II.S), but Item 5.S on this quote shows N/A, so this coverage is in the form but is not on the quote. Impersonation fraud is defined to include fraudulent websites designed to impersonate the insured, and the repair costs include a law firm and PR firm to advise customers and a third party to remove the fake sites, plus reimbursing existing customers' direct losses. It only applies if the fake site did not arise from a security failure. Breach Response Services (F) can still help with the initial response, since impersonation fraud is a listed trigger.
- **Cited:** II.S, IX.Impersonation fraud, IX.Impersonation repair costs, DEC.Item5 (expected any of: II.S, DEC.Item5)
- **in_policy_not_on_quote:** True
- **Missing facts:** not included in this quote / not on this quote / not included on this quote / not purchased


## Scoring notes

- **Citation accuracy** applies to questions expected to be answered: no citation rejected by the verifier, and at least one cited section in `expected_sections`.
- **No invented coverage** and **key facts** are checked against the answer text only (not the drafted CPL message), per the spec. Matching is case-insensitive substring matching after normalizing hyphens, contractions ("isn't" -> "is not"), number words and dollar formats. It can't tell a negated phrase from an asserted one.
- A `must_include` fact given as a list passes if any of its phrasings appears.
- A question passes when every applicable check passes.
- Before/after: `evals/results_baseline.md` is the first 3-run eval, before the Q&A routing fix and the alternative phrasings.
- Raw answers: `evals/runs/run_<n>.json`.
