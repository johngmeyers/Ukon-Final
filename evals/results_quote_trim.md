# Eval results

Generated 2026-10-25 23:20 UTC by `scripts/run_evals.py`. Model `claude-sonnet-5-5`, effort `medium`. Client `c1`, 15 questions, 3 runs.

_Sample form: Coalition Cyber Policy 3.0 specimen (form CYUSP-00PF-1022-01, 2022). Not a current Coalition policy. Indications are mock data._

## Summary

| | Run 1 | Run 2 | Run 3 | All runs |
|---|---|---|---|---|
| Questions passing all checks | 13/15 | 13/15 | 15/15 | 41/45 (91%) |
| Citation accuracy | 9/10 | 10/10 | 10/10 | 29/30 |
| Correct routing | 15/15 | 15/15 | 15/15 | 45/45 |
| Quote awareness | 1/1 | 1/1 | 1/1 | 3/3 |
| No invented coverage | 15/15 | 15/15 | 15/15 | 45/45 |
| Key facts | 9/10 | 8/10 | 10/10 | 27/30 |

Cost: $0.65 for 45 questions ($0.0145 per question). Mean latency 3.3s. Validation retries: 0.

## Per question

| ID | Question | Expected | Run 1 | Run 2 | Run 3 | Failed checks |
|---|---|---|---|---|---|---|
| q01 | If my client gets hit with ransomware, will this pay the ransom? | answer | pass | pass | pass |  |
| q02 | Does it cover lost income if their systems go down after an attack? | answer | pass | pass | pass |  |
| q03 | An employee wired $40,000 to a fake vendor after a spoofed email. Is that covered? | answer | pass | pass | pass |  |
| q04 | After a breach, does it pay to notify customers and give them credit monitoring? | answer | pass | pass | pass |  |
| q05 | If customers sue because their data was stolen, does the policy defend them? | answer | **FAIL** | pass | pass | Citation accuracy |
| q06 | If a flood takes out their server room, is that covered here? | answer | pass | pass | pass |  |
| q07 | The power company has an outage and the business loses a day. Does cyber cover that? | answer | pass | pass | pass |  |
| q08 | Malware bricked their laptops. Will the policy pay to replace them? | answer | pass | pass | pass |  |
| q09 | An employee's personal phone got hacked. Is that covered? | answer | pass | **FAIL** | pass | Key facts |
| q10 | Someone set up a fake website pretending to be my client. Are they covered? | answer | **FAIL** | **FAIL** | pass | Key facts |
| q11 | Does my client need multi-factor authentication to get this policy? | route_to_cpl | pass | pass | pass |  |
| q12 | How much more would it cost to go up to a $2 million limit? | route_to_cpl | pass | pass | pass |  |
| q13 | Is this better than the cyber coverage already in their business owner's policy? | route_to_cpl | pass | pass | pass |  |
| q14 | How fast does Coalition pay out a ransomware claim? | route_to_cpl | pass | pass | pass |  |
| q15 | Can we write this for a client in New York? | route_to_cpl | pass | pass | pass |  |

## Failures

### q05, run 1: If customers sue because their data was stolen, does the policy defend them?

- **Failed:** Citation accuracy
- **Answer:** Yes. If patients or other third parties make a claim against the practice for a data breach, security failure, or privacy liability, Network and Information Security Liability (II.A) pays claim expenses and damages, and the insurer has the right and duty to defend a claim seeking damages payable under the policy. This coverage is on the quote with a $1,000,000 limit and a $2,500 retention. Defense costs reduce the limit, the claim must first be made and reported during the policy period, and the agent should confirm no exclusion applies, such as prior knowledge or events before the retroactive date.
- **Cited:** II.A, V.Defense, V.Defense, DEC.Item5 (expected any of: II.A, V.Defense)
- **in_policy_not_on_quote:** False
- **Rejected citation** [VI.Limits of liability] quote not found in section: "Claim expenses reduce the applicable Limits of Liability"

### q09, run 2: An employee's personal phone got hacked. Is that covered?

- **Failed:** Key facts
- **Answer:** It depends on whether the phone was used for the practice's business. The definition of security failure excludes failures of devices owned or leased by an employee and not used for the named insured's business operations. But computer systems includes mobile devices operated by you, so if the employee used the personal phone for office work (for example, practice email), the hack could count as a security failure. The agent should confirm how the phone was used and what resulted, since the loss must still fit an insuring agreement such as breach response or liability.
- **Cited:** IX.Security failure, IX.Computer systems (expected any of: IX.Security failure)
- **in_policy_not_on_quote:** False
- **Missing facts:** not used for the business / not use for the business / not used for business

### q10, run 1: Someone set up a fake website pretending to be my client. Are they covered?

- **Failed:** Key facts
- **Answer:** The form covers this under Impersonation Repair Costs (II.S), which responds to an impersonation fraud, defined as fraudulent electronic communications or websites designed to impersonate the insured. Covered costs include a law firm and PR firm to publicize the fraud, reimbursing existing customers' direct losses, and a third party to take the fake site down. However, on this quote DEC.Item5 shows Impersonation Repair Costs (S) as N/A, so the coverage exists in the form but is not included. It also only applies if the fake site did not arise from a security failure of the client's systems, so the agent should confirm that.
- **Cited:** II.S, IX.Impersonation fraud, IX.Impersonation repair costs, DEC.Item5 (expected any of: II.S, DEC.Item5)
- **in_policy_not_on_quote:** True
- **Missing facts:** not included in this quote / not on this quote / not included on this quote / not purchased

### q10, run 2: Someone set up a fake website pretending to be my client. Are they covered?

- **Failed:** Key facts
- **Answer:** The form covers this under Impersonation Repair Costs (II.S), which applies to impersonation fraud, defined as fraudulent electronic communications or websites designed to impersonate the insured. However, on this quote Item 5.S shows N/A, so the coverage is in the form but not on the quote, and the client would not have it as quoted. Also note that the definition excludes fraud that arises out of or results from a security failure, so confirm the fake site is not tied to a hack of the client's own systems.
- **Cited:** II.S, IX.Impersonation fraud, DEC.Item5 (expected any of: II.S, DEC.Item5)
- **in_policy_not_on_quote:** True
- **Missing facts:** not included in this quote / not on this quote / not included on this quote / not purchased


## Scoring notes

- **Citation accuracy** applies to questions expected to be answered: no citation rejected by the verifier, and at least one cited section in `expected_sections`.
- **No invented coverage** and **key facts** are checked against the answer text only (not the drafted CPL message), per the spec. Matching is case-insensitive substring matching after normalizing hyphens, contractions ("isn't" -> "is not"), number words and dollar formats. It can't tell a negated phrase from an asserted one.
- A `must_include` fact given as a list passes if any of its phrasings appears.
- A question passes when every applicable check passes.
- Before/after: `evals/results_baseline.md` is the first 3-run eval, before the Q&A routing fix and the alternative phrasings.
- Raw answers: `evals/runs/run_<n>.json`.
