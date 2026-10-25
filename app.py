"""Streamlit UI: pre-call cyber brief for one client, plus coverage Q&A.

Run:  .venv/bin/streamlit run app.py
"""
import json

import anthropic
import streamlit as st

import config
import specimen
from brief import (client_record, fill_price, generate, indication, industry_note,
                   load_cache, monthly_price, save_cache)
from llm import StructuredOutputError
from qa import ask

st.set_page_config(page_title="Cyber Brief", page_icon="🛡️")

state = st.session_state
state.setdefault("briefs", {})      # client_id -> {"brief", "report", "stats"} from live runs
state.setdefault("answers", {})     # client_id -> last Q&A result
state.setdefault("last_call", None)  # {"kind", "cost_usd", "latency_s"} for the footer


def md(text: str) -> str:
    """Escape $ so Streamlit doesn't render dollar amounts as LaTeX."""
    return text.replace("$", "\\$")


def money(n) -> str:
    return f"${n:,.0f}"


def show_citations(citations: list[dict]) -> None:
    for c in citations:
        section = specimen.by_id().get(c["section_id"], {})
        with st.expander(f"{c['section_id']} · {section.get('title', '')}"):
            st.markdown(f"> {md(c['quote'])}")
            st.caption(f"Page {section.get('page', '?')} of the sample form")


# ---------------------------------------------------------------- sidebar

clients = json.loads(config.CLIENTS_JSON.read_text())
with st.sidebar:
    client_id = st.selectbox("Client", [c["id"] for c in clients],
                             format_func=lambda cid: client_record(cid)["name"])
    cached = load_cache(client_id)
    use_cache = st.toggle("Use cached brief", value=False,
                          help="Load the saved brief instead of calling the API. Q&A stays live.")
    if use_cache and cached:
        st.caption(f"Cached {cached['saved_at']} with {cached['model']}")
    regenerate = st.button("Regenerate brief", disabled=use_cache)
    st.divider()
    st.caption(f"Model: `{config.MODEL}`")
    st.info(config.SAMPLE_FORM_LABEL)

client = client_record(client_id)
ind = indication(client_id)
industry = industry_note(client["industry"])

# ---------------------------------------------------------------- brief

result = None
if use_cache:
    if cached:
        result = cached
    else:
        st.error(f"No cached brief for {client['name']} yet. Turn off the toggle to generate one live.")
else:
    if regenerate:
        state.briefs.pop(client_id, None)
    if client_id not in state.briefs:
        with st.spinner(f"Writing the brief for {client['name']}..."):
            try:
                brief, report, stats = generate(client_id)
            except (StructuredOutputError, anthropic.APIError) as e:
                # Kept until "Regenerate", so a failure doesn't silently retry on the next click.
                state.briefs[client_id] = {"error": str(e)}
            else:
                state.briefs[client_id] = {"brief": brief.model_dump(), "report": report, "stats": stats}
                state.last_call = {"kind": "brief", **stats}
    result = state.briefs.get(client_id)
    if result and "error" in result:
        st.error(f"The brief couldn't be generated: {result['error']}\n\n"
                 "Click Regenerate brief, or turn on Use cached brief.")
        result = None

# 1. Client header
st.title(client["name"])
st.caption(f"{industry['industry']} · {client['city']}, {client['state']} · "
           f"renewal in {client['renewal_month']} · agent {client['agent']}")

if result:
    brief, report = result["brief"], result["report"]

    # 2. Why it matters
    st.subheader("Why it matters")
    st.markdown(md(brief["why_it_matters"]))

    # 3. Opener, with the price filled in code
    st.subheader("Opener")
    st.markdown(md(fill_price(brief["opener"], ind)))

    removed = report["removed_claims"]
    if removed:
        st.warning(f"{len(removed)} claim{'s' if len(removed) > 1 else ''} removed: "
                   "citation didn't match the policy.")

    # 4. Talking points
    st.subheader("Talking points")
    for i, p in enumerate(brief["talking_points"], 1):
        st.markdown(f"**{i}.** {md(p['text'])}")
        show_citations(p["citations"])

    # 5. Objections
    st.subheader("Objections")
    for o in brief["objections"]:
        st.markdown(f"**“{md(o['objection'])}”**  \n{md(o['response'])}")
        show_citations(o["citations"])

    if not use_cache and st.sidebar.button("Save this brief to cache"):
        save_cache(client_id, brief, report, result["stats"])
        st.sidebar.success("Saved.")

# 6. Indication table, straight from the JSON; monthly computed here
st.subheader("Indication")
st.badge("MOCK DATA", color="red")
st.table([
    {
        "Option": o["label"],
        "Aggregate limit": money(o["aggregate_limit"]),
        "Retention": money(o["retention"]),
        "Annual premium": money(o["annual_premium"]),
        "Monthly": f"${o['annual_premium'] / 12:,.2f}",
    }
    for o in ind["options"]
])
st.caption(md(f"{ind['carrier']}. Mock indication, not a real carrier quote. "
              f"Opener uses the Recommended option: {monthly_price(ind)} a month."))

# 7. Ask a question
st.subheader("Ask a question")
with st.form("qa", clear_on_submit=False):
    question = st.text_input("Coverage question", placeholder="Will this pay a ransom?")
    submitted = st.form_submit_button("Ask")
if submitted and question.strip():
    with st.spinner("Checking the policy..."):
        try:
            answer, qa_report, qa_stats = ask(client_id, question.strip())
            state.answers[client_id] = {"question": question.strip(), "answer": answer.model_dump(),
                                        "report": qa_report}
            state.last_call = {"kind": "question", **qa_stats}
        except (StructuredOutputError, anthropic.APIError) as e:
            state.answers[client_id] = {"question": question.strip(), "error": str(e)}

qa_result = state.answers.get(client_id)
if qa_result:
    st.markdown(f"**Q:** {md(qa_result['question'])}")
    a = qa_result.get("answer")
    if a and a["answerable"]:
        with st.container(border=True):
            st.markdown(md(a["answer"]))
            if a["in_policy_not_on_quote"]:
                st.warning("This coverage is in the policy form, but it is not included on this quote.")
            show_citations(a["citations"])
    else:
        with st.container(border=True):
            st.markdown("#### Ask your CPL")
            if a:
                if qa_result["report"]["rerouted"]:
                    st.caption("Rerouted: the answer's citations didn't match the policy.")
                st.markdown(md(a["reason"]))
                message = a["cpl_message"]
            else:
                st.caption(f"The answer couldn't be generated ({qa_result['error']}).")
                message = f"A client asked: \"{qa_result['question']}\" Can you advise how this policy responds?"
            st.caption("Drafted message (use the copy icon):")
            st.code(message, language=None, wrap_lines=True)

# ---------------------------------------------------------------- footer

st.divider()
last = state.last_call
removed_count = len(result["report"]["removed_claims"]) if result else 0
parts = [f"Claims removed by verifier: {removed_count}"]
if use_cache and result:
    parts.insert(0, "Brief loaded from cache (no API call)")
if last:
    parts.insert(0, f"Last call ({last['kind']}): ${last['cost_usd']:.4f}, {last['latency_s']:.1f}s")
st.caption(md(" · ".join(parts)))
