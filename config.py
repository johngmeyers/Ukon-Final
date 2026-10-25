"""Shared settings: model, per-token prices, paths, labels."""
from pathlib import Path

ROOT = Path(__file__).parent

# Model. Switch here; prices below must match.
MODEL = "claude-sonnet-5-5"
EFFORT = "medium"        # Sonnet 5.5 defaults to "high"; medium keeps briefs fast
MAX_TOKENS = 16000

# USD per token (Sonnet 5.5: $2 / $10 per million; cache writes 1.25x input, reads $0.20).
PRICE_INPUT_PER_TOKEN = 2.00 / 1_000_000
PRICE_OUTPUT_PER_TOKEN = 10.00 / 1_000_000
PRICE_CACHE_WRITE_PER_TOKEN = 2.50 / 1_000_000
PRICE_CACHE_READ_PER_TOKEN = 0.20 / 1_000_000

# Eval grader for key facts (evals only). Haiku 5.5: $0.10 / $0.50 per million.
JUDGE_MODEL = "claude-haiku-5-5"
JUDGE_PRICE_INPUT_PER_TOKEN = 0.10 / 1_000_000
JUDGE_PRICE_OUTPUT_PER_TOKEN = 0.50 / 1_000_000

# Paths
DATA_DIR = ROOT / "data"
SPECIMEN_PDF = DATA_DIR / "specimen.pdf"
SECTIONS_JSON = DATA_DIR / "specimen_sections.json"
CLIENTS_JSON = DATA_DIR / "clients.json"
INDICATIONS_JSON = DATA_DIR / "indications.json"
INDUSTRIES_JSON = DATA_DIR / "industries.json"
GOLDEN_SET = ROOT / "evals" / "golden_set.yaml"
EVAL_RESULTS = ROOT / "evals" / "results.md"
CACHE_DIR = ROOT / "cache"
CALL_LOG = ROOT / "logs" / "calls.csv"
VERIFY_LOG = ROOT / "logs" / "verifier_failures.csv"

SAMPLE_FORM_LABEL = (
    "Sample form: Coalition Cyber Policy 3.0 specimen "
    "(form CYUSP-00PF-1022-01, 2022). Not a current Coalition policy."
)
