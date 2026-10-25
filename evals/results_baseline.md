# Eval results

Generated 2026-10-25 15:06 UTC by `scripts/run_evals.py`. Model `claude-sonnet-5-5`, effort `medium`. Client `c1`, 15 questions, 3 runs.

_Sample form: Coalition Cyber Policy 3.0 specimen (form CYUSP-00PF-1022-01, 2022). Not a current Coalition policy. Indications are mock data._

## Summary

| | Run 1 | Run 2 | Run 3 | All runs |
|---|---|---|---|---|
| Questions passing all checks | 11/15 | 11/15 | 11/15 | 33/45 (73%) |
| Citation accuracy | 9/10 | 9/10 | 9/10 | 27/30 |
| Correct routing | 14/15 | 14/15 | 14/15 | 42/45 |
| Quote awareness | 1/1 | 1/1 | 1/1 | 3/3 |
| No invented coverage | 15/15 | 15/15 | 15/15 | 45/45 |
| Key facts | 6/10 | 6/10 | 6/10 | 18/30 |

Cost: $0.68 for 45 questions ($0.0151 per question). Mean latency 4.3s. Validation retries: 3.

## Per question

| ID | Question | Expected | Run 1 | Run 2 | Run 3 | Failed checks |
|---|---|---|---|---|---|---|
| q01 | If my client gets hit with ransomware, will this pay the ransom? | answer | pass | pass | pass |  |
| q02 | Does it cover lost income if their systems go down after an attack? | answer | pass | pass | pass |  |
| q03 | An employee wired $40,000 to a fake vendor after a spoofed email. Is that covered? | answer | pass | pass | pass |  |
| q04 | After a breach, does it pay to notify customers and give them credit monitoring? | answer | pass | pass | pass |  |
| q05 | If customers sue because their data was stolen, does the policy defend them? | answer | pass | **FAIL** | pass | Key facts |
| q06 | If a flood takes out their server room, is that covered here? | answer | **FAIL** | **FAIL** | **FAIL** | Key facts |
| q07 | The power company has an outage and the business loses a day. Does cyber cover that? | answer | **FAIL** | pass | **FAIL** | Key facts |
| q08 | Malware bricked their laptops. Will the policy pay to replace them? | answer | pass | pass | pass |  |
| q09 | An employee's personal phone got hacked. Is that covered? | answer | **FAIL** | **FAIL** | **FAIL** | Citation accuracy, Correct routing, Key facts |
| q10 | Someone set up a fake website pretending to be my client. Are they covered? | answer | **FAIL** | **FAIL** | **FAIL** | Key facts |
| q11 | Does my client need multi-factor authentication to get this policy? | route_to_cpl | pass | pass | pass |  |
| q12 | How much more would it cost to go up to a $2 million limit? | route_to_cpl | pass | pass | pass |  |
| q13 | Is this better than the cyber coverage already in their business owner's policy? | route_to_cpl | pass | pass | pass |  |
| q14 | How fast does Coalition pay out a ransomware claim? | route_to_cpl | pass | pass | pass |  |
| q15 | Can we write this for a client in New York? | route_to_cpl | pass | pass | pass |  |

## Failures

### q05, run 2: If customers sue because their data was stolen, does the policy defend them?

- **Failed:** Key facts
- **Answer:** Yes. Under Network and Information Security Liability, the policy pays claim expenses and damages when someone makes a claim against the practice for a security failure, data breach, or privacy liability. The insurer has the right and duty to defend a claim seeking damages payable under the policy, and the practice can choose defense counsel from the panel. Defense costs reduce the limit, are subject to the $2,500 retention, and the claim must be first made and reported during the policy period. Exclusions such as Prior Knowledge or the Retroactive Date could still limit coverage.
- **Cited:** II.A, V.Defense, V.Defense (expected any of: II.A, V.Defense)
- **in_policy_not_on_quote:** False
- **Missing facts:** claims made

### q06, run 1: If a flood takes out their server room, is that covered here?

- **Failed:** Key facts
- **Answer:** Generally no. The policy excludes losses arising from any physical event or natural disaster, and flood is named specifically, so a flood destroying the server room would not be paid under this form. The cyber coverages here also respond to a security failure or systems failure, and a systems failure excludes loss of or damage to physical equipment or property, so flood damage to equipment falls outside that trigger as well.
- **Cited:** III.L, IX.Systems failure (expected any of: III.L)
- **in_policy_not_on_quote:** False
- **Missing facts:** not covered

### q06, run 2: If a flood takes out their server room, is that covered here?

- **Failed:** Key facts
- **Answer:** No. The policy excludes losses arising from a physical event or natural disaster, and flood is named specifically, so a flood destroying the server room would not be covered. Coverage here is built around security failures and systems failures, and the systems failure definition also excludes loss of or damage to physical equipment or property. The tangible property exclusion would also apply to damaged hardware, apart from the narrow computer replacement and bricking coverage, which is tied to a security failure.
- **Cited:** III.L, IX.Systems failure, III.R (expected any of: III.L)
- **in_policy_not_on_quote:** False
- **Missing facts:** not covered

### q06, run 3: If a flood takes out their server room, is that covered here?

- **Failed:** Key facts
- **Answer:** No. The policy excludes anything arising from a physical event or natural disaster, and flood is named specifically, so a flood destroying the server room would not be covered. Related coverages such as business interruption and digital asset restoration are triggered only by a security failure or systems failure, and systems failure excludes loss of or damage to physical equipment or property, so they would not respond either. Hardware damage is also excluded as tangible property, except for the narrow bricking coverage, which applies only to a security failure.
- **Cited:** III.L, IX.Systems failure, III.R (expected any of: III.L)
- **in_policy_not_on_quote:** False
- **Missing facts:** not covered

### q07, run 1: The power company has an outage and the business loses a day. Does cyber cover that?

- **Failed:** Key facts
- **Answer:** Generally no. The policy excludes electrical or mechanical failure or interruption of a utility, including blackouts, brownouts and outages, and the business interruption coverage (II.J) only responds to a security failure or systems failure. The only exception is where the loss arises directly from a service provider experiencing its own security failure, which a plain power outage is not. Also, any interruption would have to exceed the 8-hour waiting period (1 hour for the enhanced period) before business interruption loss applies.
- **Cited:** III.S, III.S, II.J (expected any of: III.S)
- **in_policy_not_on_quote:** False
- **Missing facts:** not covered

### q07, run 3: The power company has an outage and the business loses a day. Does cyber cover that?

- **Failed:** Key facts
- **Answer:** Generally no. The policy excludes electrical or mechanical failure or interruption of a utility or other third party, including blackouts, brownouts, power surges and outages. The only carve-out is for business interruption coverage where the loss arises directly from a service provider experiencing its own security failure, which a plain power company outage is not. Business interruption (Item 5.J) is on this quote, but it also requires a security failure or systems failure and an interruption longer than the waiting period.
- **Cited:** III.S, III.S, II.J (expected any of: III.S)
- **in_policy_not_on_quote:** False
- **Missing facts:** not covered

### q09, run 1: An employee's personal phone got hacked. Is that covered?

- **Failed:** Citation accuracy, Correct routing, Key facts
- **Routed to CPL.** Reason: The policy excludes personally owned or leased employee devices from security failure only if not used for business operations, so whether this hack is covered depends on how the phone was used, which the policy text and client details don't show.
- **Missing facts:** not used for the business

### q09, run 2: An employee's personal phone got hacked. Is that covered?

- **Failed:** Citation accuracy, Correct routing, Key facts
- **Routed to CPL.** Reason: The form excludes employee-owned devices not used for business from 'security failure', but whether this phone is used for business operations is a fact the policy text doesn't give.
- **Missing facts:** not used for the business

### q09, run 3: An employee's personal phone got hacked. Is that covered?

- **Failed:** Citation accuracy, Correct routing, Key facts
- **Routed to CPL.** Reason: The policy excludes employee-owned devices from security failure only if they are not used for the business operations, so coverage depends on facts about how this phone was used that the policy text does not contain.
- **Missing facts:** not used for the business

### q10, run 1: Someone set up a fake website pretending to be my client. Are they covered?

- **Failed:** Key facts
- **Answer:** The form has an Impersonation Repair Costs coverage (II.S) for fraudulent websites designed to impersonate the insured, which pays for a law firm and PR firm to publish a notice, reimbursing customers' direct losses, and removal of the fake website. However, DEC.Item5 shows Limit N/A for this coverage on this quote, so it exists in the form but is not purchased. Also, impersonation fraud only counts if it does not arise from a security failure. Breach response services (II.F) can still help with initial response to impersonation fraud for 72 hours.
- **Cited:** II.S, IX.Impersonation repair costs, DEC.Item5, IX.Impersonation fraud, II.F (expected any of: II.S, DEC.Item5)
- **in_policy_not_on_quote:** True
- **Missing facts:** not included in this quote

### q10, run 2: Someone set up a fake website pretending to be my client. Are they covered?

- **Failed:** Key facts
- **Answer:** The form has an Impersonation Repair Costs coverage (II.S) for fraudulent websites designed to impersonate the insured, and it pays for a third party to remove such websites plus related law firm and PR costs. However, DEC.Item5 shows Impersonation Repair Costs (S) as N/A, so it is in the policy form but not on this quote. The client would not have this coverage unless it is added. Impersonation fraud also only counts if it does not arise from a security failure.
- **Cited:** II.S, IX.Impersonation fraud, IX.Impersonation repair costs, DEC.Item5 (expected any of: II.S, DEC.Item5)
- **in_policy_not_on_quote:** True
- **Missing facts:** not included in this quote

### q10, run 3: Someone set up a fake website pretending to be my client. Are they covered?

- **Failed:** Key facts
- **Answer:** The form has an Impersonation Repair Costs coverage (II.S) for fraudulent websites designed to impersonate the insured, including the cost of having a third party remove them. However, DEC.Item5 shows S. Impersonation Repair Costs as N/A, so this coverage is in the form but is not on this quote and Icon Dental would not have it as quoted. Also, it only applies if the fake site does not arise out of a security failure.
- **Cited:** II.S, IX.Impersonation repair costs, DEC.Item5 (expected any of: II.S, DEC.Item5)
- **in_policy_not_on_quote:** True
- **Missing facts:** not included in this quote


## Scoring notes

- **Citation accuracy** applies to questions expected to be answered: no citation rejected by the verifier, and at least one cited section in `expected_sections`.
- **No invented coverage** and **key facts** are checked against the answer text only (not the drafted CPL message), per the spec. Matching is case-insensitive substring matching after normalizing hyphens, contractions ("isn't" -> "is not"), number words and dollar formats. It can't tell a negated phrase from an asserted one.
- A question passes when every applicable check passes.
- Raw answers: `evals/runs/run_<n>.json`.
