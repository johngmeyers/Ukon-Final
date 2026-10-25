"""Question answering: one call per question.

CLI:  .venv/bin/python qa.py c1 "question" ["another question" ...]
"""
import sys

from pydantic import BaseModel, Field, model_validator

import config
from brief import SAMPLE_FORM_RULE, client_record, context_block, indication, industry_note
from llm import StructuredOutputError, call_structured
from verify import Citation, verify_answer

INSTRUCTIONS = f"""You answer coverage questions for a licensed insurance agent preparing for a client's cyber renewal. The policy is in the <policy> block above; the client, industry note, quote options and the question are in the user message.

{SAMPLE_FORM_RULE}

When to answer
- Answer only if the policy text settles the question. Then set answerable to true, write a plain-English answer of 2-4 sentences for the agent, and cite the policy.
- Otherwise set answerable to false and route the question to a CPL (the agency's coverage specialist). Always route questions about pricing or premiums, underwriting requirements, claims timing, state availability, comparisons with other policies, or anything that depends on facts the policy text doesn't contain.
- A routed answer has answer null and no citations. Give a one-line reason and a short cpl_message the agent can send: who the client is, the question, and what the CPL needs to check.

Citations
- Every statement about what the policy covers or excludes needs a citation: the section id exactly as shown, and a quote copied character for character from that one section. Quotes must be 5-30 words; aim for 10-25 by quoting the key phrase, not the whole sentence. No ellipses, no paraphrase, no joining text from different places.
- Check exclusions (III.x) and definitions (IX.x) as well as the insuring agreements, and mention a condition or exclusion that limits the answer.

What this quote includes
- DEC.Item5 shows which insuring agreements this quote includes. If the coverage exists in the form but shows "N/A" there, set in_policy_not_on_quote to true and say so in the answer. Otherwise set it to false.

Never
- Never state, estimate or compare a price or premium.
- Never answer, or suggest answers to, the client's security application questions (MFA, backups and so on).
"""


class Answer(BaseModel):
    answerable: bool = Field(description="False if the policy text doesn't settle the question")
    answer: str | None = Field(description="Plain English, 2-4 sentences; null when not answerable")
    citations: list[Citation] = Field(description="Required when answerable; empty when not")
    in_policy_not_on_quote: bool = Field(description="True if the coverage exists in the form but DEC.Item5 shows N/A")
    cpl_message: str | None = Field(description="When not answerable: a drafted message the agent can send to a CPL")
    reason: str | None = Field(description="When not answerable: one line on why the policy text can't settle it")

    @model_validator(mode="after")
    def consistent(self):
        if self.answerable:
            if not self.answer:
                raise ValueError("answerable answers need answer text")
            if not self.citations:
                raise ValueError("answerable answers need at least one citation")
        else:
            if not self.cpl_message or not self.reason:
                raise ValueError("routed answers need cpl_message and reason")
            if self.answer or self.citations:
                raise ValueError("routed answers must have answer null and no citations")
        return self


def ask(client_id: str, question: str):
    """Return (verified answer, verifier report, call stats). Raises StructuredOutputError."""
    client = client_record(client_id)
    content = (
        context_block(client, industry_note(client["industry"]), indication(client_id))
        + f"\n\n<question>\n{question}\n</question>"
    )
    answer, stats = call_structured(
        kind="qa", client_id=client_id, instructions=INSTRUCTIONS,
        user_content=content, output_model=Answer,
    )
    verified, report = verify_answer(answer, question, client_id)
    return verified, report, stats


def main(client_id: str, questions: list[str]):
    for q in questions:
        print(f"=== Q: {q}")
        try:
            a, report, stats = ask(client_id, q)
        except StructuredOutputError as e:
            print(f"FAILED (route to CPL): {e}\n")
            continue
        if a.answerable:
            print("ANSWER\n" + a.answer)
            for c in a.citations:
                print(f'   [{c.section_id}] "{c.quote}"')
            print(f"in_policy_not_on_quote: {a.in_policy_not_on_quote}")
        else:
            print("ASK YOUR CPL")
            print(f"reason: {a.reason}")
            print(f"drafted message: {a.cpl_message}")
        print(f"verifier: {len(report['rejected_citations'])} citation(s) rejected, "
              f"rerouted to CPL: {report['rerouted']}")
        for r in report["rejected_citations"]:
            print(f'- [{r["section_id"]}] {r["reason"]}: "{r["quote"]}"')
        print(f"call: attempts {stats['attempts']}, cache read {stats['cache_read_tokens']}, "
              f"output {stats['output_tokens']}, cost ${stats['cost_usd']:.4f}, "
              f"latency {stats['latency_s']:.1f}s")
        for errs in stats.get("validation_errors", []):
            print("validation retry after:\n" + errs)
        print()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit('usage: qa.py <client_id> "question" ["question" ...]')
    main(sys.argv[1], sys.argv[2:])
