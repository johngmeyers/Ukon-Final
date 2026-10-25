"""Shared settings: model, per-token prices, paths, labels."""
from pathlib import Path

ROOT = Path(__file__).parent

# Model. Switch here; prices below must match.
MODEL = "claude-sonnet-5-5"

# USD per token (Sonnet 5.5: $2 / $10 per million).
PRICE_INPUT_PER_TOKEN = 2.00 / 1_000_000
PRICE_OUTPUT_PER_TOKEN = 10.00 / 1_000_000

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

SAMPLE_FORM_LABEL = (
    "Sample form: Coalition Cyber Policy 3.0 specimen "
    "(form CYUSP-00PF-1022-01, 2022). Not a current Coalition policy."
)
