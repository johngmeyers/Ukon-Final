# Cyber Brief Prototype: Build Spec

Give this file to Claude Code at the start of the session. Build in the order in "Build plan". Time-box: 3 hours.

## Goal

One Streamlit screen that shows what an insurance agent would see before a renewal call: a two-minute cyber brief for one client, plus a box to ask coverage questions. Every coverage claim cites the policy specimen. Anything the specimen can't settle goes to "Ask your CPL" instead of a guess.

The point of the demo is trust: the AI is useful, and it is visibly constrained.

**Demo script (the acceptance test):**
1. Pick a client from the sidebar. The brief appears.
2. Ask a question the policy covers. The answer shows a citation with the quoted policy text.
3. Ask a question the policy doesn't settle. The app routes it to a CPL with a drafted message.
4. Show the eval results table.

## Non-goals

- No delivery channel (email, AMS). The brief appears on screen; production delivery is a slide, not code.
- No data enrichment, no carrier API calls, no proposal pack.
- No login, no database, no multi-user anything.
- No AI-generated prices, ever.

## Setup checklist (do these first)

- [ ] **Download the specimen manually** from Victor Insurance: https://www.victorinsurance.com/content/dam/victor/victor2/documents/victor-us/cyber/policy-forms/US-cyber-policy-form-coalition-cic.pdf and save it to `data/specimen.pdf`.
- [ ] **Keep only the declarations and the base policy wording.** Strip the marketing pages at the front, the panel provider notice, and all endorsements (Arizona changes, terrorism, pollution, obligations, policy changes). They muddy citations. The base wording is form `CYUSP-00PF-1022-01` (30 pages); the declarations are form `CYUSP-00DC-1022-01` (5 pages).
- [ ] **Label it as a sample form everywhere it shows:** "Sample form: Coalition Cyber Policy 3.0 specimen (form CYUSP-00PF-1022-01, 2022). Not a current Coalition policy."
- [ ] **Keep the repo private, and keep any deployed backup link private.** Do not commit the PDF or extracted text to a public repo, and do not publish the full specimen text.
- [ ] Put the Anthropic API key in `.env` (`ANTHROPIC_API_KEY`), and add `.env` to `.gitignore`.

## Stack

- Python 3.11+
- `streamlit` for the UI
- `anthropic` SDK, with **structured outputs** for schema-constrained output: `client.messages.create(output_config={"format": {"type": "json_schema", "schema": anthropic.transform_schema(<PydanticModel>)}})`, then Pydantic validation in our code. Forced tool use (`tool_choice` `any`/`tool`) returns a 400 on the current Sonnet, so don't use it. See "Structured output" below.
- `pydantic` for schemas and validation
- `pypdf` or `pdfplumber` for text extraction
- `pyyaml` for the eval set
- Model is a config value (`MODEL` in `config.py`). Default to the current Sonnet model, and make it easy to switch.

## Repo layout

```
app.py                      # Streamlit UI
config.py                   # model, prices per token, paths
brief.py                    # brief generation
qa.py                       # question answering
verify.py                   # deterministic citation checker
specimen.py                 # loads sections
llm.py                      # shared structured-output call, retry, cost logging
scripts/build_sections.py   # one-time: PDF -> data/specimen_sections.json
scripts/run_evals.py        # runs the golden set, writes results
data/specimen.pdf           # not committed if repo is ever public
data/specimen_sections.json
data/clients.json
data/indications.json
data/industries.json
evals/golden_set.yaml
evals/results.md            # generated
cache/                      # saved briefs for demo fallback
```

## Data

### Specimen sections (`scripts/build_sections.py`)

Extract text from the kept pages and split it into citable sections. One record per section:

```json
{"id": "II.I", "title": "Ransomware and Cyber Extortion", "page": 2, "text": "We will pay on your behalf cyber extortion expenses ..."}
```

Section IDs:
- Declarations: keep only `DEC.Item4` (limits), `DEC.Item5` (insuring agreements purchased, limits, retentions, including the N/A ones), `DEC.Item6` (pre-claim assistance) and `DEC.Item8` (how to report a claim). Drop every other declaration item (named insured, policy period, premium, quota share, retroactive and continuity dates, extended reporting, choice of law, breach advisor, endorsement list). They describe the sample insured, not our client.
- Insuring agreements: `II.A` through `II.T`
- Exclusions: `III.A` through `III.W`
- Obligations, claims process, limits, cancellation, other provisions: `IV`, `V`, `VI`, `VII`, `VIII`, with a sub-id per headed paragraph (for example `VIII.Territory`, `V.Defense`)
- Definitions: `IX.<term>` (for example `IX.Security failure`, `IX.Indemnity period`)

Splitting can be heuristic (regex on the lettered headings and bold definition terms), then **hand-check the output**: every A–T and A–W letter present, definitions not merged together. Keep `DEC.Item5` intact, because it shows which coverages were bought and which are "N/A"; the model needs that to tell "the policy has it" from "this quote includes it".

### Clients (`data/clients.json`)

4 real public businesses, hand-picked, one per industry. No personal data. Revenue as a band, not a figure.

```json
[
  {"id": "c1", "name": "<real dental practice>", "industry": "dental", "state": "CO", "revenue_band": "$1M-$3M", "employees": "10-25", "renewal_month": "December", "agent": "Sam Rivera"}
]
```

Industries (the `industry` value must match an `id` in `industries.json`): `dental` (dental office), `coffee` (coffee roaster and shop), `accounting` (accounting and bookkeeping firm), `preschool` (independent preschool).

### Indications (`data/indications.json`)

Mock, labeled as mock. Already provided: use the supplied `indications.json` as is. The file is an object with a `_note` string and an `indications` list (one entry per client, 2-3 options each). Entry shape:

```json
{"client_id": "c1", "carrier": "Coalition (sample form)", "mock": true, "options": [
  {"label": "Recommended", "aggregate_limit": 1000000, "retention": 2500, "annual_premium": 2827, "funds_transfer_sublimit": 250000}
]}
```

The specimen's own declarations show a $1M limit, $2,500 retention and $2,827 premium. Use that as the anchor option, and set lower and higher options around it. The monthly figure is computed in code (`annual_premium / 12`), never by the model.

### Industry exposures (`data/industries.json`)

One record per industry, already drafted (use the provided `industries.json` as is): `id`, `industry`, `data_held`, `systems_relied_on`, `exposure` (a short paragraph) and `common_incidents` (three examples). This stands in for the CPL-approved content library. The model may use it for "why it matters", the opener and talking points, but **coverage claims must still cite the specimen**. The notes deliberately contain no coverage claims.

## Structured output

Checked against the Anthropic structured-outputs docs (2026-10-25): `claude-sonnet-5-5` supports structured outputs, and it rejects forced `tool_choice` (`any`/`tool`) with a 400. Pattern for `brief.py` and `qa.py`:

1. Call `client.messages.create(...)` with `output_config.format` set to `anthropic.transform_schema(Brief | Answer)`, so the model's output is constrained to the schema. (`messages.parse()` does the same but validates inside the SDK, so a failed attempt's token usage is lost; we validate ourselves to log every attempt.) Shared code lives in `llm.py`.
2. Check `stop_reason` before using the result. On `"refusal"` or `"max_tokens"`, the output may not match the schema: treat it as a failure (for Q&A, route to a CPL; for the brief, show an error or the cached brief).
3. The schema can't express everything: array `minItems` only supports 0 or 1, and `maxItems`, `minLength`/`maxLength` and numeric bounds aren't enforced by the API. So "exactly 3 talking points", "3-5 objections" and "quote is 5-30 words" are Pydantic validators, checked after the response comes back. These limits are soft: they never fail a response. Extra talking points or objections are dropped, fewer are accepted, and a quote over 30 words is trimmed to its first 30 words (still verbatim, so the verifier still checks it). Only the price rules (no dollar amounts in the opener or why-it-matters, price token used once) fail validation.
4. On a Pydantic validation failure, retry once with the validation error appended to the user message. If the retry also fails, treat it as a failure as in step 2.
5. Log tokens and cost for every attempt, including retries.

The citation verifier (`verify.py`) runs after this, on the validated object.

## Brief generation (`brief.py`)

One call per client. Inputs: client record, industry exposure note, indication, and all specimen sections (the whole policy fits in the prompt; no vector search). Section IDs are passed in so the model can cite them.

Structured output (see "Structured output" above) with this schema:

```python
class Citation(BaseModel):
    section_id: str          # must exist in specimen_sections.json
    quote: str               # short verbatim quote from that section, 5-30 words

class Point(BaseModel):
    text: str                # plain English, one or two sentences
    citations: list[Citation]  # required for any coverage claim; may be empty only for non-coverage context

class Objection(BaseModel):
    objection: str           # what the client says
    response: str            # what the agent can say back
    citations: list[Citation]

class Brief(BaseModel):
    why_it_matters: str      # 2-3 sentences, specific to this client's industry
    opener: str              # 30-second opener tied to the renewal; mentions price only as a placeholder token {MONTHLY_PRICE}
    talking_points: list[Point]   # exactly 3
    objections: list[Objection]   # 3-5
```

Rules for the system prompt:
- Include verbatim: "The policy text is a sample form. Ignore any sample insured name, dates or state details in it; they are not this client’s."
- Audience is the licensed agent, not the client. Plain English, about an 8th-grade reading level. The whole brief should read in about two minutes (under ~400 words).
- Every statement about what the policy covers or excludes must carry at least one citation with a verbatim quote.
- Never state or estimate a price. Use the `{MONTHLY_PRICE}` token; the app fills it from the indication.
- Never answer, or suggest answers to, the client's security application questions (MFA, backups and so on).
- If a coverage is "N/A" in `DEC.Item5`, do not present it as included.
- Objections to cover first: "We're too small to be a target," "My IT person handles security," and "Isn't this already in my business policy?"

## Question answering (`qa.py`)

One call per question. Same inputs as the brief, plus the question. Structured output (see "Structured output" above) with this schema:

```python
class Answer(BaseModel):
    answerable: bool          # false if the specimen doesn't settle it
    answer: str | None        # plain English, 2-4 sentences
    citations: list[Citation]
    in_policy_not_on_quote: bool  # true if the coverage exists but DEC.Item5 shows N/A
    cpl_message: str | None   # when not answerable: a drafted message the agent can send to a CPL
    reason: str | None        # one line: why it can't be answered from the specimen
```

The system prompt includes verbatim: "The policy text is a sample form. Ignore any sample insured name, dates or state details in it; they are not this client’s."

Route to a CPL when the specimen doesn't settle the question, including pricing, underwriting requirements, claims timing, state availability, and comparisons with other policies.

## Citation verifier (`verify.py`)

Deterministic, no AI. This is the guardrail to show in the demo.

For each citation:
1. `section_id` exists in `specimen_sections.json`.
2. `quote` appears in that section's text after normalizing whitespace, case and hyphenation.
3. If not, but the quote appears verbatim in exactly one other section, the citation is relabeled to that section (logged), since it is real policy text with the wrong label.

Then:
- A point or objection whose citations all fail is **removed** from the brief, and the UI shows "1 claim removed: citation didn't match the policy."
- An answer with `answerable: true` but no passing citation is converted to a CPL route.
- Log every failure with the question, section ID and quote, for the eval write-up.

## UI (`app.py`)

One screen:
- **Sidebar:** client picker, "Use cached brief" toggle, model name, and the sample-form label.
- **Main area, in order:**
  1. Client header (name, industry, renewal month).
  2. Why it matters.
  3. The opener, with `{MONTHLY_PRICE}` filled from the recommended option.
  4. Three talking points. Each citation is an expander showing the section ID, title and quoted text.
  5. Objections and responses, with citations the same way.
  6. Indication table, copied exactly from JSON: limit, retention, annual premium, monthly (computed), and a "MOCK DATA" badge.
  7. "Ask a question" box. A cited answer, or an "Ask your CPL" card with the drafted message and a copy button.
- **Footer:** cost and latency of the last call, and the count of claims removed by the verifier.

## Cost and latency logging

Log input and output tokens per call, and compute cost from per-token prices in `config.py`. Show it in the footer and write it to `logs/calls.csv`. A real "cents per brief" number answers the CFO's AI cost-economics question.

## Demo fallback

After a good run, save each client's brief to `cache/<client_id>.json`. The "Use cached brief" toggle loads from cache instead of calling the API, in case the network or the API is slow on Tuesday. Q&A always stays live.

## Evals (`scripts/run_evals.py`)

Reads `evals/golden_set.yaml`, runs each question through `qa.py` for one client, applies the verifier, and scores:

| Metric | Pass rule |
|---|---|
| Citation accuracy | Every citation passes the verifier, and at least one cited section is in `expected_sections` |
| Correct routing | `answerable` matches `expected` (answer vs. route_to_cpl) |
| Quote awareness | For questions marked `on_quote: false`, the answer flags `in_policy_not_on_quote` |
| No invented coverage | No `must_not_claim` phrase appears in the answer |
| Key facts | Each `must_include` fact appears (case-insensitive, numbers normalized); a fact the wording misses is judged by meaning by a grader model (`JUDGE_MODEL` in `config.py`), with each decision and its evidence listed in the results |

Write `evals/results.md` with a per-question table and totals. Run it 3 times and report the pass rate, since outputs vary. Keep one honest failure, plus what fixed it, for the presentation.

## Build plan (3 hours)

| Time | Step |
|---|---|
| 0:00-0:20 | Setup checklist, repo layout, `build_sections.py`, hand-check the sections |
| 0:20-0:35 | `clients.json`, `indications.json`, `industries.json` |
| 0:35-1:15 | `brief.py` + `verify.py`, tested from the command line on one client |
| 1:15-1:35 | `qa.py`, tested on two questions (one covered, one not) |
| 1:35-2:10 | `app.py` |
| 2:10-2:40 | `run_evals.py`, run the golden set, fix the worst failure |
| 2:40-3:00 | Cache all briefs, record a screen capture of the demo script, note cost per brief |

If time runs short, cut in this order: the cost footer, then the objections section (keep the talking points), then the cache toggle. Never cut the verifier or the evals.

## Done when

- [ ] The demo script runs start to finish on all 4 clients.
- [ ] Every coverage claim on screen has a passing citation.
- [ ] No price on screen was generated by the model.
- [ ] `evals/results.md` exists with pass rates from 3 runs.
- [ ] Cost per brief and per answer is known.
- [ ] A screen recording of the demo is saved as a backup.
