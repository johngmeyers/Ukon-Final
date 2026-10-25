"""Loads the specimen sections and formats them for prompts."""
import json
from functools import lru_cache

from config import SAMPLE_FORM_LABEL, SECTIONS_JSON


@lru_cache
def sections() -> list[dict]:
    return json.loads(SECTIONS_JSON.read_text())


@lru_cache
def by_id() -> dict[str, dict]:
    return {s["id"]: s for s in sections()}


@lru_cache
def policy_prompt() -> str:
    """The whole policy as tagged sections. Identical on every call, so it caches."""
    parts = [
        f"<policy>\n{SAMPLE_FORM_LABEL}\n"
        "Each section below is citable by its id. DEC.* sections are from the declarations; "
        "the rest are the policy wording."
    ]
    for s in sections():
        parts.append(f'<section id="{s["id"]}" title="{s["title"]}">\n{s["text"]}\n</section>')
    parts.append("</policy>")
    return "\n\n".join(parts)
