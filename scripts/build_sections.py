"""One-time: data/specimen.pdf -> data/specimen_sections.json.

Expects the trimmed specimen: declarations (CYUSP-00DC-1022-01) and base
wording (CYUSP-00PF-1022-01) only. Pages from any other form are skipped.

The wording is two-column: headings on the left, text on the right. We read
words with their positions, drop the diagonal "SPECIMEN" watermark and the
page headers/footers, and split on the left-column headings.

Run:  .venv/bin/python scripts/build_sections.py
Then hand-check the printed summary and warnings.
"""
import json
import re
import sys
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import SECTIONS_JSON, SPECIMEN_PDF  # noqa: E402

DEC_FORM = "CYUSP-00DC-1022-01"
POLICY_FORM = "CYUSP-00PF-1022-01"

WATERMARK_MIN_SIZE = 20        # "SPECIMEN" letters are ~100pt; body text is 8-14pt
HEADER_BOTTOM = {DEC_FORM: 110, POLICY_FORM: 70}  # insurer address block
COLUMN_X = 228                 # wording: heading column ends, text column starts
PARAGRAPH_GAP = 16             # line pitch is ~10.5pt; bigger gaps start a paragraph
HEADING_WRAP = 13              # max gap between wrapped lines of one heading
LINE_TOLERANCE = 3             # words within this many points share a line (list numbers sit ~2pt low)

# Item 5 table columns (declarations)
LIMIT_X = 330
RETENTION_X = 440
RETENTION_VALUE_X = 515        # inside the retention column: label | value
DEC_VALUE_X = 300              # other declaration items: label | value

SECTION_TITLES = {
    "I": "",
    "II": "WHAT WE COVER – OUR INSURING AGREEMENTS",
    "III": "EXCLUSIONS – WHAT IS NOT COVERED",
    "IV": "YOUR OBLIGATIONS AS AN INSURED",
    "V": "CLAIMS PROCESS",
    "VI": "LIMITS OF LIABILITY AND RETENTION",
    "VII": "CANCELLATION AND OPTIONAL EXTENDED REPORTING PERIOD",
    "VIII": "OTHER PROVISIONS",
    "IX": "DEFINITIONS",
}

# Declaration items we keep. The rest (named insured, dates, premium, quota
# share, choice of law, endorsement list, ...) describe the sample insured,
# not our client, so they are dropped.
DEC_TITLES = {
    4: "Limits of Liability",
    5: "Insuring Agreement(s) purchased, Limits of Liability, and Retentions",
    6: "Pre-Claim Assistance",
    8: "Notification of incidents, claims, or potential claims",
}

SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "not", "of", "on", "or", "the", "to"}
ACRONYMS = {"PCI"}


# ---------------------------------------------------------------- PDF reading

def read_rows(pdf_path):
    """Yield one dict per visual line: form, form page, top, words (sorted by x)."""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page = page.filter(
                lambda o: o.get("object_type") != "char" or o["size"] < WATERMARK_MIN_SIZE
            )
            lines = []
            for w in sorted(page.extract_words(), key=lambda w: (w["top"], w["x0"])):
                if lines and abs(lines[-1][0]["top"] - w["top"]) <= LINE_TOLERANCE:
                    lines[-1].append(w)
                else:
                    lines.append([w])
            lines = [sorted(ws, key=lambda w: w["x0"]) for ws in lines]

            footer = next((ws for ws in lines if text_of(ws).startswith("CYUSP-")), None)
            m = footer and re.match(r"(CYUSP-\S+) Page (\d+) of \d+", text_of(footer))
            if not m or m.group(1) not in HEADER_BOTTOM:
                continue
            form, form_page = m.group(1), int(m.group(2))
            for ws in lines:
                if ws is footer or ws[0]["top"] < HEADER_BOTTOM[form]:
                    continue
                yield {"form": form, "page": form_page, "top": ws[0]["top"], "words": ws}


def text_of(words):
    return " ".join(w["text"] for w in words)


def clean(text):
    text = re.sub(r"[ \t]+([.,;:)])", r"\1", text)   # "us ." -> "us." (bold terms are separate words)
    text = re.sub(r"\([ \t]+", "(", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def join_lines(lines):
    """lines: [(page, top, text)]. Wrapped lines join with a space, paragraphs with a newline."""
    out, prev = "", None
    for page, top, text in lines:
        if not out:
            out = text
        elif prev[0] == page and top - prev[1] > PARAGRAPH_GAP:
            out += "\n" + text
        elif out.endswith("-") and text[:1].islower():
            out += text                                   # "employment-" + "related"
        else:
            out += " " + text
        prev = (page, top)
    return clean(out)


def title_case(s):
    def word(w, first):
        if w in ACRONYMS:
            return w
        if not first and w.lower() in SMALL_WORDS:
            return w.lower()
        return "-".join("/".join(p.capitalize() for p in part.split("/")) for part in w.split("-"))
    return " ".join(word(w, i == 0) for i, w in enumerate(s.split()))


def sentence_case(s):
    s = s.lower()
    return s[:1].upper() + s[1:]


# ------------------------------------------------------------- base wording

def parse_policy(rows):
    sections = []
    cur = None
    roman = None
    title_buf = None          # while reading a SECTION's title lines
    heading = None            # (page, top) of the last heading line, for wrapped headings

    def start(sec_id, title, page):
        nonlocal cur
        cur = {"id": sec_id, "roman": roman, "title": title, "page": page, "lines": []}
        sections.append(cur)

    for r in rows:
        left = [w for w in r["words"] if w["x0"] < COLUMN_X]
        right = [w for w in r["words"] if w["x0"] >= COLUMN_X]
        L, R = text_of(left), text_of(right)
        pos = (r["page"], r["top"])

        if text_of(r["words"]) == "COALITION CYBER POLICY 3.0":
            continue

        m = re.fullmatch(r"SECTION ([IVX]+)", L)
        if m and not R:
            roman = m.group(1)
            cur, heading = None, None
            title_buf = "" if SECTION_TITLES[roman] else None
            continue

        # Section title lines (may wrap; VII's title runs into the right column).
        if title_buf is not None:
            expected = SECTION_TITLES[roman]
            title_buf = (title_buf + " " + L).strip()
            if R and (title_buf + " " + R).strip() == expected:
                title_buf, R = expected, ""
            if not expected.startswith(title_buf):
                raise ValueError(f"Section {roman} title mismatch: {title_buf!r}")
            if (R or title_buf == expected) and cur is None:
                start(roman, title_case(expected), r["page"])
            if title_buf == expected:
                title_buf = None
            if R:
                cur["lines"].append((r["page"], r["top"], R))
            continue

        wrapped = bool(L and heading and heading[0] == pos[0] and pos[1] - heading[1] <= HEADING_WRAP)

        if wrapped and (roman != "IX" or not R):
            cur["title"] += ("" if cur["title"].endswith("-") else " ") + L   # heading wraps
            heading = pos
        elif L and roman in ("II", "III"):
            m = re.match(r"([A-W])\. (.+)", L)
            if not m:
                heading = None                       # group label, e.g. "FIRST PARTY COVERAGES"
            else:
                prev = cur
                start(f"{roman}.{m.group(1)}", m.group(2), r["page"])
                heading = pos
                if not R and prev is not None:
                    # Heading printed a line below where its text starts (III.A).
                    while prev["lines"] and prev["lines"][-1][0] == pos[0] and pos[1] - prev["lines"][-1][1] <= HEADING_WRAP:
                        cur["lines"].insert(0, prev["lines"].pop())
        elif L and roman == "IX":
            start("IX.term", L, r["page"])
            heading = pos
        elif L:
            start(None, L, r["page"])                # I, IV-VIII headed paragraph; id set below
            heading = pos

        if R:
            cur["lines"].append((r["page"], r["top"], R))

    out = []
    for s in sections:
        title = clean(s["title"])
        if s["id"] == "IX.term":
            sec_id = f"IX.{title}"
        elif s["id"] is None:
            sec_id = f"{s['roman']}.{sentence_case(title.split(' – ')[0])}"
            title = title_case(title)
        else:
            sec_id = s["id"]
            title = title_case(title)
        if s["lines"]:                               # IV-VIII have no preamble text
            out.append({"id": sec_id, "title": title, "page": s["page"], "text": join_lines(s["lines"])})
    return out


# -------------------------------------------------------------- declarations

def render_item5_table(rows):
    """Rebuild the Item 5 table as one line per insuring agreement."""
    out, agr = [], None

    def flush():
        nonlocal agr
        if agr:
            parts = [clean(agr["name"])]
            if agr["limit"]:
                parts.append("Limit: " + clean(agr["limit"]))
            if agr["retention"]:
                parts.append("Retention: " + clean(agr["retention"]))
            parts += [clean(f"{lbl} {val}") for lbl, val in agr["subs"]]
            line = " | ".join(parts)
            if agr["note"]:
                line += "\nNote: " + clean(agr["note"])
            out.append(line)
        agr = None

    for r in rows:
        name = text_of([w for w in r["words"] if w["x0"] < LIMIT_X])
        limit = text_of([w for w in r["words"] if LIMIT_X <= w["x0"] < RETENTION_X])
        ret_label = text_of([w for w in r["words"] if RETENTION_X <= w["x0"] < RETENTION_VALUE_X])
        ret_value = text_of([w for w in r["words"] if w["x0"] >= RETENTION_VALUE_X])

        if name.startswith("Insuring Agreement") or (not name and not limit and ret_value == "Retention"):
            continue                                  # column header rows
        if re.match(r"[A-T]\. ", name):
            flush()
            agr = {"name": name, "limit": limit, "retention": "", "subs": [], "note": ""}
        elif name.isupper() and not (limit or ret_label or ret_value) and not (agr and _wraps(agr, r)):
            flush()
            out.append("\n" + name)                   # group label, e.g. "FIRST PARTY COVERAGES"
            continue
        elif agr is None:
            continue
        elif name.isupper():
            agr["name"] += " " + name
        elif name:
            agr["note"] += " " + name                 # the G. "If this box ..." paragraph

        if agr is None:
            continue
        agr["_last"] = (r["page"], r["top"])
        if limit and not re.match(r"[A-T]\. ", name):
            agr["limit"] += ("; " if re.match(r"i+\.", limit) else " ") + limit
        if ret_label.startswith("$"):
            agr["limit"] += " " + ret_label           # O.'s "$250" sits just inside the retention column
        elif ret_label:
            if ret_label[:1].islower() and not re.match(r"i+\.", ret_label) and agr["subs"]:
                lbl, val = agr["subs"][-1]
                agr["subs"][-1] = (lbl + " " + ret_label, val + " " + ret_value)
            else:
                agr["subs"].append((ret_label, ret_value))
        elif ret_value:
            agr["retention"] += " " + ret_value

    flush()
    return out


def _wraps(agr, r):
    """True if row r sits directly under the agreement's previous line (a wrapped name)."""
    last = agr.get("_last")
    return bool(last and last[0] == r["page"] and r["top"] - last[1] <= HEADING_WRAP)


def parse_declarations(rows):
    sections = []
    cur = None

    def start(sec_id, title, page):
        nonlocal cur
        cur = {"id": sec_id, "title": title, "page": page, "lines": [], "table": []}
        sections.append(cur)

    skipping = True                                   # everything before Item 1 is dropped
    for r in rows:
        text = text_of(r["words"])
        if m := re.match(r"Item (\d+)\.", text):
            n = int(m.group(1))
            skipping = n not in DEC_TITLES            # a dropped item runs to the next "Item N."
            if not skipping:
                start(f"DEC.Item{n}", DEC_TITLES[n], r["page"])
        if skipping:
            continue

        if cur["id"] == "DEC.Item5" and (cur["table"] or text.startswith("THIRD PARTY LIABILITY")):
            cur["table"].append(r)                    # table part of Item 5
            continue
        if cur["id"] == "DEC.Item8":                  # wrapped label beside the contact details
            cur["table"].append(r)
            continue
        cur["lines"].append((r["page"], r["top"], clean(text)))

    out = []
    for s in sections:
        if s["id"] == "DEC.Item5":
            text = join_lines(s["lines"]) + "\n" + "\n".join(render_item5_table(s["table"]))
        elif s["id"] == "DEC.Item8":
            label = text_of([w for r in s["table"] for w in r["words"] if w["x0"] < DEC_VALUE_X])
            values = [text_of([w for w in r["words"] if w["x0"] >= DEC_VALUE_X]) for r in s["table"]]
            text = "\n".join([label] + [v for v in values if v])
        else:
            text = "\n".join(t for _, _, t in s["lines"])   # short label/value rows
        out.append({"id": s["id"], "title": s["title"], "page": s["page"], "text": text.strip()})
    return out


# -------------------------------------------------------------------- checks

def check(sections):
    ids = [s["id"] for s in sections]
    warnings = []
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        warnings.append(f"duplicate ids: {sorted(dupes)}")
    for prefix, letters in (("II", "ABCDEFGHIJKLMNOPQRST"), ("III", "ABCDEFGHIJKLMNOPQRSTUVW")):
        missing = [c for c in letters if f"{prefix}.{c}" not in ids]
        if missing:
            warnings.append(f"missing {prefix}: {missing}")
    missing = [n for n in DEC_TITLES if f"DEC.Item{n}" not in ids]
    if missing:
        warnings.append(f"missing DEC items: {missing}")
    for s in sections:
        if not s["text"]:
            warnings.append(f"{s['id']}: empty text")
        if s["id"].startswith("IX.") and s["id"] != "IX" and not s["text"].startswith("means"):
            warnings.append(f"{s['id']}: definition does not start with 'means'")
        if s["id"].startswith("IX.") and re.search(r"\n[A-Z][a-z]+( [a-z]+)* means\b", s["text"]):
            warnings.append(f"{s['id']}: looks like two definitions merged")
        # Split-word artifacts from kerning, e.g. "i nsureds".
        for frag in re.findall(r"(?<![\w'’.])(?!a )[a-z] [a-z]{3,}", s["text"]):
            warnings.append(f"{s['id']}: possible split word {frag!r}")
    return warnings


def main():
    rows = list(read_rows(SPECIMEN_PDF))
    sections = parse_declarations([r for r in rows if r["form"] == DEC_FORM])
    sections += parse_policy([r for r in rows if r["form"] == POLICY_FORM])

    SECTIONS_JSON.write_text(json.dumps(sections, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(sections)} sections to {SECTIONS_JSON.relative_to(SECTIONS_JSON.parents[1])}\n")
    for s in sections:
        first = s["text"].split("\n")[0]
        print(f"{s['id']:<45} p{s['page']:<3} {s['title']}\n{'':49}{first[:110]}")
    warnings = check(sections)
    print(f"\n{len(warnings)} warning(s)")
    for w in warnings:
        print("  -", w)


if __name__ == "__main__":
    main()
