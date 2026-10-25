"""Deterministic citation checker. No AI.

A citation passes if its section_id exists and its quote appears in that
section's text after normalizing whitespace, case, quotes and hyphenation.
If the quote is real policy text but labelled with the wrong section (it appears
in exactly one other section), the citation is relabelled to that section.
"""
import csv
import re
import unicodedata
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

import config
import specimen

LOG_FIELDS = ["timestamp", "kind", "client_id", "question", "location", "section_id", "quote", "reason"]

_CHAR_MAP = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
})


class Citation(BaseModel):
    section_id: str = Field(description="Section id exactly as shown in the policy, e.g. II.I or IX.Security failure")
    quote: str = Field(description="Verbatim quote from that section, 5-30 words, copied exactly, no ellipses")

    @field_validator("quote")
    @classmethod
    def quote_length(cls, v: str) -> str:
        words = v.split()
        if len(words) < 5:
            raise ValueError(f"quote must be 5-30 words, got {len(words)}")
        # Trim rather than reject: the first 30 words of a verbatim quote are still
        # verbatim, so the verifier can check them and a good answer isn't thrown away.
        return " ".join(words[:30]) if len(words) > 30 else v


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_CHAR_MAP).lower()
    text = re.sub(r"\s*-\s*", "-", text)          # "non- renewal", "employment -related"
    return re.sub(r"\s+", " ", text).strip()


def _quote_key(c: Citation) -> str:
    return normalize(c.quote).strip(" \"'.,;:")


def check_citation(c: Citation) -> str | None:
    """Return None if the citation passes, else the reason it failed."""
    section = specimen.by_id().get(c.section_id)
    if section is None:
        return "unknown section_id"
    quote = _quote_key(c)
    if not quote or quote not in normalize(section["text"]):
        return "quote not found in section"
    return None


def sections_containing(c: Citation) -> list[str]:
    quote = _quote_key(c)
    return [s["id"] for s in specimen.sections() if quote and quote in normalize(s["text"])]


def _filter(citations, location, rejected, relabeled):
    passing = []
    for c in citations:
        reason = check_citation(c)
        if not reason:
            passing.append(c)
            continue
        found = sections_containing(c)
        if len(found) == 1:
            # Real policy text with the wrong label: fix the label rather than drop it.
            relabeled.append({"location": location, "section_id": c.section_id, "quote": c.quote,
                              "reason": f"relabeled to {found[0]}"})
            passing.append(c.model_copy(update={"section_id": found[0]}))
        else:
            rejected.append({"location": location, "section_id": c.section_id, "quote": c.quote, "reason": reason})
    return passing


def verify_brief(brief, client_id: str):
    """Drop failed citations; remove any point or objection whose citations all failed.

    Returns (verified brief copy, report) where report has "removed_claims",
    "rejected_citations" and "relabeled_citations".
    """
    rejected, relabeled, removed = [], [], []
    points = []
    for i, p in enumerate(brief.talking_points, 1):
        passing = _filter(p.citations, f"talking_points[{i}]", rejected, relabeled)
        if p.citations and not passing:
            removed.append({"location": f"talking_points[{i}]", "text": p.text})
        else:
            points.append(p.model_copy(update={"citations": passing}))
    objections = []
    for i, o in enumerate(brief.objections, 1):
        passing = _filter(o.citations, f"objections[{i}]", rejected, relabeled)
        if o.citations and not passing:
            removed.append({"location": f"objections[{i}]", "text": o.objection})
        else:
            objections.append(o.model_copy(update={"citations": passing}))

    _log_failures("brief", client_id, "", rejected + relabeled)
    verified = brief.model_copy(update={"talking_points": points, "objections": objections})
    return verified, {"removed_claims": removed, "rejected_citations": rejected, "relabeled_citations": relabeled}


def verify_answer(answer, question: str, client_id: str):
    """Drop failed citations; an answerable answer with none left becomes a CPL route.

    Returns (verified answer copy, report).
    """
    rejected, relabeled = [], []
    passing = _filter(answer.citations, "answer", rejected, relabeled)
    _log_failures("qa", client_id, question, rejected + relabeled)
    rerouted = answer.answerable and not passing
    if rerouted:
        answer = answer.model_copy(update={
            "answerable": False,
            "answer": None,
            "citations": [],
            "in_policy_not_on_quote": False,
            "reason": "The draft answer's citations didn't match the policy text.",
            "cpl_message": answer.cpl_message or (
                f'A client asked: "{question}" I couldn\'t confirm the answer from the policy '
                "wording. Can you advise how this policy responds?"
            ),
        })
    else:
        answer = answer.model_copy(update={"citations": passing})
    return answer, {"rerouted": rerouted, "rejected_citations": rejected, "relabeled_citations": relabeled}


def _log_failures(kind, client_id, question, rejected):
    if not rejected:
        return
    config.VERIFY_LOG.parent.mkdir(exist_ok=True)
    new = not config.VERIFY_LOG.exists()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with config.VERIFY_LOG.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        for r in rejected:
            w.writerow({"timestamp": now, "kind": kind, "client_id": client_id, "question": question, **r})
