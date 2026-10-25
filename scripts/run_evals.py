"""Runs the golden set through qa.py (verifier included), scores it, writes evals/results.md.

Run:  .venv/bin/python scripts/run_evals.py [--runs 3]
Raw answers for each run go to evals/runs/run_<n>.json.

Key facts are matched by wording first; a fact the wording check misses goes to a
small grader model, which judges meaning. Every grader decision is listed in the
report with its evidence, so it can be audited.
"""
import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import yaml
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402
from llm import StructuredOutputError, get_client  # noqa: E402
from qa import ask  # noqa: E402

RUNS_DIR = config.ROOT / "evals" / "runs"
METRICS = [
    ("citations", "Citation accuracy"),
    ("routing", "Correct routing"),
    ("quote_awareness", "Quote awareness"),
    ("no_invented", "No invented coverage"),
    ("key_facts", "Key facts"),
]

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fourteen": 14, "fifteen": 15,
    "twenty": 20, "thirty": 30, "forty": 40, "sixty": 60, "ninety": 90,
}
SCALES = {"k": 1_000, "thousand": 1_000, "m": 1_000_000, "million": 1_000_000}


def norm(text: str) -> str:
    """Normalize for matching facts: case, quotes, hyphens, contractions, numbers."""
    t = unicodedata.normalize("NFKC", text).lower()
    t = t.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'}))
    t = re.sub(r"[-‐‑‒–—]", " ", t)                       # "claims-made" -> "claims made"
    t = t.replace("won't", "will not").replace("can't", "can not").replace("n't", " not")
    t = t.replace("one hundred and eighty", "180")
    t = re.sub(r"\b(" + "|".join(NUMBER_WORDS) + r")\b", lambda m: str(NUMBER_WORDS[m.group(1)]), t)
    t = re.sub(r"(?<=\d),(?=\d{3})", "", t)                 # 250,000 -> 250000
    t = re.sub(r"\$?(\d+(?:\.\d+)?)\s*(k|thousand|m|million)\b",
               lambda m: str(int(float(m.group(1)) * SCALES[m.group(2)])), t)
    t = re.sub(r"[$()]", " ", t)
    t = re.sub(r"\b(hour|day|month|year)s\b", r"\1", t)     # "8 hours" matches "8-hour"
    return re.sub(r"\s+", " ", t).strip()


def contains(text: str, phrase: str) -> bool:
    if phrase.lower() in text.lower():
        return True
    n = norm(phrase)
    return bool(n) and n in norm(text)


def has_fact(text: str, fact) -> bool:
    """A fact is a phrase, or a list of acceptable phrasings."""
    return any(contains(text, p) for p in (fact if isinstance(fact, list) else [fact]))


JUDGE_SYSTEM = (
    "You check whether an answer written for an insurance agent states specific facts. Judge meaning, not "
    "exact wording: a fact is stated if a reader of the answer would come away knowing it. A fact listed "
    "with alternative phrasings (separated by ' / ') is stated if the answer states any of them. Use only "
    "the answer text. Don't use outside knowledge, and don't credit a fact the answer only hints at."
)


class FactVerdict(BaseModel):
    fact_number: int
    present: bool
    evidence: str = Field(description="The words in the answer that state the fact; empty if not stated")


class FactVerdicts(BaseModel):
    verdicts: list[FactVerdict]


def fact_label(fact) -> str:
    return " / ".join(fact) if isinstance(fact, list) else fact


def judge_facts(answer_text: str, facts: list) -> tuple[list[dict], float]:
    """Ask the grader model which facts the answer states. Returns (verdicts, cost)."""
    listed = "\n".join(f"{i}. {fact_label(f)}" for i, f in enumerate(facts, 1))
    resp = get_client().messages.create(
        model=config.JUDGE_MODEL,
        max_tokens=2000,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": f"<answer>\n{answer_text}\n</answer>\n\n<facts>\n{listed}\n"
                                              "</facts>\n\nFor each fact, say whether the answer states it."}],
        output_config={"effort": "low",
                       "format": {"type": "json_schema", "schema": anthropic.transform_schema(FactVerdicts)}},
    )
    cost = (resp.usage.input_tokens * config.JUDGE_PRICE_INPUT_PER_TOKEN
            + resp.usage.output_tokens * config.JUDGE_PRICE_OUTPUT_PER_TOKEN)
    if resp.stop_reason in ("refusal", "max_tokens"):
        return [{"present": False, "evidence": f"(grader stopped: {resp.stop_reason})"} for _ in facts], cost
    text = next((b.text for b in resp.content if b.type == "text"), "")
    by_number = {v.fact_number: v for v in FactVerdicts.model_validate_json(text).verdicts}
    return [{"present": by_number[i].present, "evidence": by_number[i].evidence} if i in by_number
            else {"present": False, "evidence": "(grader gave no verdict)"} for i in range(1, len(facts) + 1)], cost


def check_facts(q: dict, a: dict | None) -> tuple[list[dict], float]:
    """Wording first; facts the wording misses go to the grader model."""
    text = (a or {}).get("answer") or ""
    checks, to_judge = [], []
    for f in q.get("must_include", []):
        if has_fact(text, f):
            checks.append({"fact": fact_label(f), "method": "wording", "present": True, "evidence": ""})
        else:
            to_judge.append(f)
    cost = 0.0
    if to_judge and text:
        verdicts, cost = judge_facts(text, to_judge)
        checks += [{"fact": fact_label(f), "method": "grader", **v} for f, v in zip(to_judge, verdicts)]
    else:
        checks += [{"fact": fact_label(f), "method": "wording", "present": False, "evidence": ""} for f in to_judge]
    return checks, cost


def score(q: dict, a: dict | None, report: dict | None, fact_checks: list[dict]) -> dict:
    """Return {metric: True | False | None (not applicable)}."""
    expect_answer = q["expected"] == "answer"
    if a is None:                                           # call failed outright
        return {
            "citations": False if expect_answer else None,
            "routing": not expect_answer,
            "quote_awareness": False if q.get("on_quote") is False else None,
            "no_invented": True,
            "key_facts": False if q.get("must_include") else None,
        }
    text = a["answer"] or ""
    cited = {c["section_id"] for c in a["citations"]}
    return {
        "citations": (not report["rejected_citations"] and bool(cited & set(q["expected_sections"])))
                     if expect_answer else None,
        "routing": a["answerable"] == expect_answer,
        "quote_awareness": a["in_policy_not_on_quote"] if q.get("on_quote") is False else None,
        "no_invented": not any(contains(text, p) for p in q.get("must_not_claim", [])),
        "key_facts": all(c["present"] for c in fact_checks) if q.get("must_include") else None,
    }


def run_once(golden: dict, run_no: int) -> list[dict]:
    rows = []
    for q in golden["questions"]:
        print(f"  run {run_no} {q['id']}...", end=" ", flush=True)
        try:
            a, report, stats = ask(golden["client_id"], q["question"])
            a, error = a.model_dump(), None
        except StructuredOutputError as e:
            a, report, stats, error = None, None, {}, str(e)
        fact_checks, judge_cost = check_facts(q, a)
        metrics = score(q, a, report, fact_checks)
        passed = all(v is not False for v in metrics.values())
        print("PASS" if passed else "FAIL")
        rows.append({"id": q["id"], "answer": a, "report": report, "error": error,
                     "metrics": metrics, "passed": passed, "fact_checks": fact_checks, "judge_cost_usd": judge_cost,
                     "cost_usd": stats.get("cost_usd", 0.0), "latency_s": stats.get("latency_s", 0.0),
                     "attempts": stats.get("attempts", 0)})
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / f"run_{run_no}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    return rows


def failure_detail(q: dict, row: dict) -> str:
    failed = [label for key, label in METRICS if row["metrics"][key] is False]
    lines = [f"- **Failed:** {', '.join(failed)}"]
    a = row["answer"]
    if row["error"]:
        lines.append(f"- **Error:** {row['error']}")
    elif a["answerable"]:
        lines.append(f"- **Answer:** {a['answer']}")
        lines.append(f"- **Cited:** {', '.join(c['section_id'] for c in a['citations']) or 'none'} "
                     f"(expected any of: {', '.join(q['expected_sections']) or 'none'})")
        lines.append(f"- **in_policy_not_on_quote:** {a['in_policy_not_on_quote']}")
    else:
        lines.append(f"- **Routed to CPL.** Reason: {a['reason']}")
    if row["metrics"]["key_facts"] is False:
        missing = [f"{c['fact']} ({c['method']})" for c in row["fact_checks"] if not c["present"]]
        lines.append(f"- **Missing facts:** {'; '.join(missing)}")
    if row["metrics"]["no_invented"] is False:
        hits = [p for p in q["must_not_claim"] if contains(a["answer"] or "", p)]
        lines.append(f"- **Forbidden phrases found:** {', '.join(hits)}")
    for r in (row["report"] or {}).get("rejected_citations", []):
        lines.append(f"- **Rejected citation** [{r['section_id']}] {r['reason']}: \"{r['quote']}\"")
    for r in (row["report"] or {}).get("relabeled_citations", []):
        lines.append(f"- **Relabeled citation** [{r['section_id']}] {r['reason']}: \"{r['quote']}\"")
    return "\n".join(lines)


def write_report(golden: dict, runs: list[list[dict]]) -> None:
    qs = {q["id"]: q for q in golden["questions"]}
    n_runs, n_q = len(runs), len(golden["questions"])
    all_rows = [r for run in runs for r in run]
    total_cost = sum(r["cost_usd"] for r in all_rows)
    judge_cost = sum(r["judge_cost_usd"] for r in all_rows)
    all_checks = [c for r in all_rows for c in r["fact_checks"]]

    out = [
        "# Eval results",
        "",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC by `scripts/run_evals.py`. "
        f"Model `{config.MODEL}`, effort `{config.EFFORT}`. Client `{golden['client_id']}`, "
        f"{n_q} questions, {n_runs} runs.",
        "",
        f"_{config.SAMPLE_FORM_LABEL} Indications are mock data._",
        "",
        "## Summary",
        "",
        "| | " + " | ".join(f"Run {i}" for i in range(1, n_runs + 1)) + " | All runs |",
        "|---|" + "---|" * (n_runs + 1),
    ]
    per_run = [sum(r["passed"] for r in run) for run in runs]
    out.append("| Questions passing all checks | " + " | ".join(f"{p}/{n_q}" for p in per_run)
               + f" | {sum(per_run)}/{n_q * n_runs} ({sum(per_run) / (n_q * n_runs):.0%}) |")
    for key, label in METRICS:
        cells = []
        for run in runs + [all_rows]:
            vals = [r["metrics"][key] for r in run if r["metrics"][key] is not None]
            cells.append(f"{sum(vals)}/{len(vals)}")
        out.append(f"| {label} | " + " | ".join(cells) + " |")
    out += [
        "",
        f"Cost: ${total_cost:.2f} for {len(all_rows)} questions "
        f"(${total_cost / len(all_rows):.4f} per question). "
        f"Mean latency {sum(r['latency_s'] for r in all_rows) / len(all_rows):.1f}s. "
        f"Validation retries: {sum(1 for r in all_rows if r['attempts'] > 1)}.",
        "",
        f"Key facts: {len(all_checks)} fact checks, {sum(c['method'] == 'wording' and c['present'] for c in all_checks)} "
        f"matched by wording, {sum(c['method'] == 'grader' for c in all_checks)} sent to the grader model "
        f"(`{config.JUDGE_MODEL}`, ${judge_cost:.4f} total). "
        f"Citations relabeled by the verifier: "
        f"{sum(len((r['report'] or {}).get('relabeled_citations', [])) for r in all_rows)}.",
        "",
        "## Per question",
        "",
        "| ID | Question | Expected | " + " | ".join(f"Run {i}" for i in range(1, n_runs + 1)) + " | Failed checks |",
        "|---|---|---|" + "---|" * n_runs + "---|",
    ]
    for qid, q in qs.items():
        rows = [next(r for r in run if r["id"] == qid) for run in runs]
        failed = sorted({label for r in rows for key, label in METRICS if r["metrics"][key] is False})
        out.append(f"| {qid} | {q['question']} | {q['expected']} | "
                   + " | ".join("pass" if r["passed"] else "**FAIL**" for r in rows)
                   + f" | {', '.join(failed)} |")
    out += ["", "## Failures", ""]
    any_fail = False
    for qid, q in qs.items():
        for i, run in enumerate(runs, 1):
            row = next(r for r in run if r["id"] == qid)
            if not row["passed"]:
                any_fail = True
                out += [f"### {qid}, run {i}: {q['question']}", "", failure_detail(q, row), ""]
    if not any_fail:
        out.append("None.")

    out += ["", "## Grader-model decisions on key facts", "",
            "Facts the wording check missed, judged by the grader model. Listed in full so they can be audited.", ""]
    graded = [(qid, i, c) for i, run in enumerate(runs, 1) for r in run for qid in [r["id"]]
              for c in r["fact_checks"] if c["method"] == "grader"]
    if graded:
        out += ["| Question | Run | Fact | Stated? | Evidence from the answer |", "|---|---|---|---|---|"]
        out += [f"| {qid} | {i} | {c['fact']} | {'yes' if c['present'] else '**no**'} | "
                f"{c['evidence'].replace('|', '/') or '—'} |" for qid, i, c in sorted(graded)]
    else:
        out.append("None: every fact was matched by wording.")

    relabels = [(r["id"], i, x) for i, run in enumerate(runs, 1) for r in run
                for x in (r["report"] or {}).get("relabeled_citations", [])]
    out += ["", "## Citations relabeled by the verifier", "",
            "Quotes that are real policy text but were labeled with the wrong section. The verifier "
            "moved each to the one section that contains it, so the agent sees a correct citation.", ""]
    if relabels:
        out += ["| Question | Run | Cited as | Quote | Result |", "|---|---|---|---|---|"]
        out += [f"| {qid} | {i} | {x['section_id']} | \"{x['quote']}\" | {x['reason']} |" for qid, i, x in relabels]
    else:
        out.append("None.")
    out += [
        "",
        "## Scoring notes",
        "",
        "- **Citation accuracy** applies to questions expected to be answered: no citation rejected by "
        "the verifier, and at least one cited section in `expected_sections`. A citation the verifier "
        "relabeled counts as passing, because the agent sees the corrected section.",
        "- **No invented coverage** is checked against the answer text only (not the drafted CPL message), "
        "per the spec, by case-insensitive substring matching after normalizing hyphens, contractions, "
        "number words and dollar formats. It can't tell a negated phrase from an asserted one.",
        f"- **Key facts** are matched the same way first. A fact the wording misses goes to a grader model "
        f"(`{config.JUDGE_MODEL}`), which judges whether the answer states it in meaning. A `must_include` "
        "fact given as a list passes if any of its phrasings appears.",
        "- A question passes when every applicable check passes.",
        "- Earlier runs: `evals/results_baseline.md` (first eval), `evals/results_routing_fix.md` (after "
        "the Q&A routing fix), `evals/results_quote_trim.md` (after quote trimming, before relabeling "
        "and the grader model).",
        f"- Raw answers: `evals/runs/run_<n>.json`.",
        "",
    ]
    config.EVAL_RESULTS.write_text("\n".join(out))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    golden = yaml.safe_load(config.GOLDEN_SET.read_text())
    runs = [run_once(golden, i) for i in range(1, args.runs + 1)]
    write_report(golden, runs)
    print(f"Wrote {config.EVAL_RESULTS.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
