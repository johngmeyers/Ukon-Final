"""Brief generation: one call per client.

CLI:  .venv/bin/python brief.py c1
"""
import json
import re
import sys

from pydantic import BaseModel, Field, field_validator

import config
from llm import StructuredOutputError, call_structured
from verify import Citation, verify_brief

PRICE_TOKEN = "{MONTHLY_PRICE}"
DOLLAR_AMOUNT = re.compile(r"\$\s?\d")

SAMPLE_FORM_RULE = (
    "The policy text is a sample form. Ignore any sample insured name, dates or state details "
    "in it; they are not this client’s."
)

INSTRUCTIONS = f"""You write a pre-call cyber insurance brief for a licensed insurance agent who is about to call a small-business client about their renewal. The policy is in the <policy> block above; the client, industry note and quote options are in the user message.

{SAMPLE_FORM_RULE}

Audience and length
- Write for the agent, not the client. Plain English, about an 8th-grade reading level.
- The whole brief should read in about two minutes: under 400 words in total.

Citations
- Every statement about what the policy covers or excludes must carry at least one citation: the section id exactly as shown, and a quote of 5-30 words copied character for character from that one section. No ellipses, no paraphrase, no joining text from different places.
- Cite the section that actually says it: an insuring agreement (II.x) for what is covered, an exclusion (III.x) for what isn't, a definition (IX.x) for what a term includes, DEC.Item5 for limits, retentions and what this quote includes.
- Industry context comes from the industry note and needs no citation, but don't present it as coverage.

What this quote includes
- DEC.Item5 shows which insuring agreements are included. If a coverage shows "N/A" there, don't present it as included. You may say the form offers it but this quote doesn't include it.
- You don't know what the client's other policies cover. Don't claim what they include or exclude.

Price
- Never state, estimate or compare a price or premium. Refer to the price only with the exact token {PRICE_TOKEN}; the app fills it in.

Security application
- Never answer, or suggest answers to, the client's security application questions (MFA, backups and so on).

Fields
- why_it_matters: 2-3 sentences specific to this client's industry.
- opener: a 30-second opener the agent can say, tied to the renewal, using {PRICE_TOKEN} once.
- talking_points: exactly 3.
- objections: 3 to 5. Cover these first, in this order: "We're too small to be a target," "My IT person handles security," and "Isn't this already in my business policy?"
"""


class Point(BaseModel):
    text: str = Field(description="Plain English, one or two sentences")
    citations: list[Citation] = Field(description="Required for any coverage claim; empty only for non-coverage context")


class Objection(BaseModel):
    objection: str = Field(description="What the client says")
    response: str = Field(description="What the agent can say back")
    citations: list[Citation]


class Brief(BaseModel):
    why_it_matters: str = Field(description="2-3 sentences, specific to this client's industry")
    opener: str = Field(description=f"30-second opener tied to the renewal; price only as {PRICE_TOKEN}")
    talking_points: list[Point] = Field(description="Exactly 3")
    objections: list[Objection] = Field(description="3 to 5")

    @field_validator("talking_points")
    @classmethod
    def three_points(cls, v):
        if len(v) != 3:
            raise ValueError(f"need exactly 3 talking points, got {len(v)}")
        return v

    @field_validator("objections")
    @classmethod
    def three_to_five_objections(cls, v):
        if not 3 <= len(v) <= 5:
            raise ValueError(f"need 3-5 objections, got {len(v)}")
        return v

    @field_validator("opener")
    @classmethod
    def opener_price_token(cls, v):
        if v.count(PRICE_TOKEN) != 1:
            raise ValueError(f"opener must use {PRICE_TOKEN} exactly once")
        if DOLLAR_AMOUNT.search(v):
            raise ValueError("opener must not contain dollar amounts; use the price token")
        return v

    @field_validator("why_it_matters")
    @classmethod
    def no_dollar_amounts(cls, v):
        if DOLLAR_AMOUNT.search(v):
            raise ValueError("why_it_matters must not contain dollar amounts")
        return v


# ---------------------------------------------------------------- data

def _load(path):
    return json.loads(path.read_text())


def client_record(client_id: str) -> dict:
    return next(c for c in _load(config.CLIENTS_JSON) if c["id"] == client_id)


def industry_note(industry_id: str) -> dict:
    return next(i for i in _load(config.INDUSTRIES_JSON) if i["id"] == industry_id)


def indication(client_id: str) -> dict:
    return next(i for i in _load(config.INDICATIONS_JSON)["indications"] if i["client_id"] == client_id)


def monthly_price(ind: dict) -> str:
    """Computed in code from the recommended option, never by the model."""
    option = next(o for o in ind["options"] if o["label"] == "Recommended")
    return f"${option['annual_premium'] / 12:,.2f}"


def fill_price(text: str, ind: dict) -> str:
    return text.replace(PRICE_TOKEN, monthly_price(ind))


def context_block(client: dict, industry: dict, ind: dict) -> str:
    """Client, industry note and quote options for the user message (shared with qa.py)."""
    # Premiums are withheld: the model never sees a price, so it can't repeat one.
    options = [{k: v for k, v in o.items() if k != "annual_premium"} for o in ind["options"]]
    quote = {"carrier": ind["carrier"], "mock": ind["mock"], "options": options}
    return (
        f"<client>\n{json.dumps(client, indent=2)}\n</client>\n\n"
        f"<industry_note>\n{json.dumps(industry, indent=2)}\n</industry_note>\n\n"
        f"<quote_options>\n{json.dumps(quote, indent=2)}\n</quote_options>"
    )


# ---------------------------------------------------------------- generation

def generate(client_id: str):
    """Return (verified brief, verifier report, call stats). Raises StructuredOutputError."""
    client = client_record(client_id)
    ind = indication(client_id)
    brief, stats = call_structured(
        kind="brief",
        client_id=client_id,
        instructions=INSTRUCTIONS,
        user_content=context_block(client, industry_note(client["industry"]), ind) + "\n\nWrite the brief.",
        output_model=Brief,
    )
    verified, report = verify_brief(brief, client_id)
    return verified, report, stats


def _print_citations(citations):
    for c in citations:
        print(f'     [{c.section_id}] "{c.quote}"')


def main(client_id: str):
    client = client_record(client_id)
    ind = indication(client_id)
    try:
        brief, report, stats = generate(client_id)
    except StructuredOutputError as e:
        sys.exit(f"Brief failed: {e}")

    print(f"=== {client['name']} | {client['industry']} | renewal {client['renewal_month']} ===")
    print(f"({config.SAMPLE_FORM_LABEL})\n")
    print("WHY IT MATTERS\n" + brief.why_it_matters + "\n")
    print("OPENER\n" + fill_price(brief.opener, ind) + "\n")
    print("TALKING POINTS")
    for i, p in enumerate(brief.talking_points, 1):
        print(f"{i}. {p.text}")
        _print_citations(p.citations)
    print("\nOBJECTIONS")
    for i, o in enumerate(brief.objections, 1):
        print(f'{i}. "{o.objection}"\n   {o.response}')
        _print_citations(o.citations)

    print("\n=== VERIFIER ===")
    print(f"{len(report['rejected_citations'])} citation(s) rejected, "
          f"{len(report['removed_claims'])} claim(s) removed")
    for r in report["rejected_citations"]:
        print(f'- {r["location"]} [{r["section_id"]}] {r["reason"]}: "{r["quote"]}"')
    for r in report["removed_claims"]:
        print(f'- REMOVED {r["location"]}: {r["text"]}')

    print("\n=== CALL ===")
    print(f"model {config.MODEL}, effort {config.EFFORT}, attempts {stats['attempts']}")
    print(f"tokens: input {stats['input_tokens']}, cache write {stats['cache_write_tokens']}, "
          f"cache read {stats['cache_read_tokens']}, output {stats['output_tokens']}")
    print(f"cost ${stats['cost_usd']:.4f}, latency {stats['latency_s']:.1f}s")
    for errs in stats.get("validation_errors", []):
        print("validation retry after:\n" + errs)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "c1")
