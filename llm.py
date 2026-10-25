"""Shared Claude call: schema-constrained output, one validation retry, cost logging.

Uses structured outputs (`output_config.format`). Forced tool use returns a 400
on the current Sonnet. The schema comes from the Pydantic model; rules the
schema can't express (list sizes, quote lengths) live in the model's validators
and are checked here, with one retry on failure.
"""
import csv
import time
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

import config
import specimen

load_dotenv(config.ROOT / ".env")

_client = None

LOG_FIELDS = ["timestamp", "kind", "client_id", "model", "attempt", "stop_reason", "input_tokens",
              "cache_write_tokens", "cache_read_tokens", "output_tokens", "cost_usd", "latency_s"]


class StructuredOutputError(RuntimeError):
    """No usable object: refusal, truncation, or validation failed twice."""


def get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def system_blocks(instructions: str) -> list[dict]:
    # Policy first, with the cache breakpoint. The output schema is part of the cached
    # prefix, so briefs and questions each keep their own cache entry.
    return [
        {"type": "text", "text": specimen.policy_prompt(), "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": instructions},
    ]


def cost_of(usage) -> float:
    return (
        usage.input_tokens * config.PRICE_INPUT_PER_TOKEN
        + (usage.cache_creation_input_tokens or 0) * config.PRICE_CACHE_WRITE_PER_TOKEN
        + (usage.cache_read_input_tokens or 0) * config.PRICE_CACHE_READ_PER_TOKEN
        + usage.output_tokens * config.PRICE_OUTPUT_PER_TOKEN
    )


def call_structured(*, kind: str, client_id: str, instructions: str, user_content: str,
                    output_model: type[BaseModel]):
    """Return (validated output_model instance, stats summed over attempts)."""
    schema = anthropic.transform_schema(output_model)
    stats = {"attempts": 0, "input_tokens": 0, "cache_write_tokens": 0, "cache_read_tokens": 0,
             "output_tokens": 0, "cost_usd": 0.0, "latency_s": 0.0}
    content = user_content
    for attempt in (1, 2):
        start = time.monotonic()
        resp = get_client().messages.create(
            model=config.MODEL,
            max_tokens=config.MAX_TOKENS,
            system=system_blocks(instructions),
            messages=[{"role": "user", "content": content}],
            output_config={"effort": config.EFFORT, "format": {"type": "json_schema", "schema": schema}},
        )
        row = _log_call(kind, client_id, attempt, resp, time.monotonic() - start)
        stats["attempts"] = attempt
        for k in ("input_tokens", "cache_write_tokens", "cache_read_tokens", "output_tokens", "cost_usd", "latency_s"):
            stats[k] += row[k]

        if resp.stop_reason in ("refusal", "max_tokens"):
            raise StructuredOutputError(f"stop_reason={resp.stop_reason}; output may not match the schema")
        text = next((b.text for b in resp.content if b.type == "text"), "")
        try:
            return output_model.model_validate_json(text), stats
        except ValidationError as e:
            problems = "\n".join(f"- {'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors())
            stats["validation_errors"] = stats.get("validation_errors", []) + [problems]
            if attempt == 2:
                raise StructuredOutputError(f"validation failed twice:\n{problems}") from e
            content = (user_content + "\n\nYour previous response failed these checks. "
                       "Fix them and respond again:\n" + problems)


def _log_call(kind, client_id, attempt, resp, latency) -> dict:
    u = resp.usage
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind, "client_id": client_id, "model": config.MODEL, "attempt": attempt,
        "stop_reason": resp.stop_reason,
        "input_tokens": u.input_tokens,
        "cache_write_tokens": u.cache_creation_input_tokens or 0,
        "cache_read_tokens": u.cache_read_input_tokens or 0,
        "output_tokens": u.output_tokens,
        "cost_usd": round(cost_of(u), 6),
        "latency_s": round(latency, 2),
    }
    config.CALL_LOG.parent.mkdir(exist_ok=True)
    new = not config.CALL_LOG.exists()
    with config.CALL_LOG.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    return row
