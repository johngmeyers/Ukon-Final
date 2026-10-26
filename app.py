"""Streamlit UI, webmail view: each brief arrives as a renewal email in the agent's inbox.

Styled like a familiar webmail client (no third-party branding). Presentation
only: brief generation, the verifier and Q&A are unchanged.

Run:  .venv/bin/streamlit run app.py
"""
import json
import re
import threading
from datetime import date
from html import escape
from urllib.parse import quote

import anthropic
import streamlit as st

import config
import specimen
from brief import (client_record, fill_price, generate, indication, industry_note,
                   load_cache, save_cache)
from llm import StructuredOutputError
from qa import ask

SENDER = "UKON Cyber Desk"
SENDER_ADDR = "cyberdesk@ukon.example"
DIGEST = "digest"

st.set_page_config(page_title="Inbox · Mail", page_icon="✉️", layout="wide")

state = st.session_state
state.setdefault("briefs", {})      # client_id -> {"brief", "report", "stats"} from live runs
state.setdefault("answers", {})     # client_id -> list of Q&A replies, oldest first
state.setdefault("last_call", None)  # {"kind", "cost_usd", "latency_s"} for the footer
state.setdefault("open", None)       # None = inbox list; else DIGEST or a client id
state.setdefault("read", set())      # opened inbox items
state.setdefault("questions_asked", 0)


def icon(path: str, size: int = 20, color: str = "#444746") -> str:
    """A 24x24 Material icon path (Apache 2.0) as an <img>; st.html strips inline <svg>."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}">'
           f'<path d="{path}"/></svg>')
    return (f'<img src="data:image/svg+xml,{quote(svg)}" width="{size}" height="{size}" alt="" '
            f'style="vertical-align:middle;flex:none">')


I_MENU = "M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"
I_SEARCH = ("M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57"
            "l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z")
I_MAIL = ("M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6"
          "l8 5 8-5v2z")
I_EDIT = ("M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a.996.996 0 0 0 0-1.41l-2.34-2.34"
          "a.996.996 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z")
I_INBOX = ("M19 3H4.99C3.89 3 3 3.9 3 5l.01 14c0 1.1.89 2 1.99 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 12h-4"
           "c0 1.66-1.35 3-3 3s-3-1.34-3-3H4.99V5H19v10z")
I_STAR = ("M22 9.24l-7.19-.62L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.63-7.03L22 9.24z"
          "M12 15.4l-3.76 2.27 1-4.28-3.32-2.88 4.38-.38L12 6.1l1.71 4.04 4.38.38-3.32 2.88 1 4.28L12 15.4z")
I_CLOCK = ("M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20"
           "c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z")
I_SEND = "M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"
I_FILE = "M6 2c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6H6zm7 7V3.5L18.5 9H13z"
I_LABEL = ("M17.63 5.84C17.27 5.33 16.67 5 16 5L5 5.01C3.9 5.01 3 5.9 3 7v10c0 1.1.9 1.99 2 1.99L16 19"
           "c.67 0 1.27-.33 1.63-.84L22 12l-4.37-6.16z")
I_CHECKBOX = "M19 5v14H5V5h14m0-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"
I_REFRESH = ("M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55"
             " 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11"
             "h7V4l-2.35 2.35z")
I_MORE = ("M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"
          "m0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z")

st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
.stApp, .stApp p, .stApp li, .stApp button, .stApp input, .stApp textarea { font-family: Roboto, Arial, sans-serif; }
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }
.block-container, [data-testid="stMainBlockContainer"] { padding: .5rem 1rem 1rem 1rem !important; max-width: 100% !important; }

/* top bar */
.topbar { display: flex; align-items: center; gap: 14px; height: 56px; }
.topbar .brand { display: flex; align-items: center; gap: 8px; width: 210px; font-size: 22px; color: #444746; }
.topbar .search { flex: 1; max-width: 720px; display: flex; align-items: center; gap: 12px; background: #e9eef6;
  border-radius: 24px; height: 46px; padding: 0 16px; color: #444746; font-size: 16px; }
.topbar .right { margin-left: auto; display: flex; align-items: center; gap: 12px; }
.avatar { width: 32px; height: 32px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 500; font-size: 14px; flex: none; }
.av-desk { background: #1a73e8; } .av-me { background: #188038; }
.av-big { width: 40px; height: 40px; font-size: 18px; }

/* left nav */
.compose { display: inline-flex; align-items: center; gap: 12px; background: #c2e7ff; color: #001d35; border-radius: 16px;
  height: 56px; padding: 0 22px 0 18px; font-weight: 500; font-size: 14px; margin: 4px 0 14px 0;
  box-shadow: 0 1px 2px rgba(60,64,67,.15); }
.nav a, .nav div.item { display: flex; align-items: center; gap: 16px; height: 32px; padding: 0 12px 0 24px; margin-left: -16px;
  border-radius: 0 16px 16px 0; font-size: 14px; color: #202124; text-decoration: none; }
.nav .active { background: #d3e3fd; font-weight: 700; color: #041e49; }
.nav .count { margin-left: auto; font-size: 12px; }
.nav .labels { font-size: 16px; color: #1f1f1f; margin: 18px 0 6px 8px; }

/* main panel */
.st-key-panel { background: #fff; border-radius: 16px; padding: 4px 16px 16px 16px; min-height: 80vh; }
.toolbar { display: flex; align-items: center; gap: 22px; height: 48px; padding-left: 8px; color: #444746; font-size: 12px; }
.toolbar .range { margin-left: auto; }
.tabs { display: flex; border-bottom: 1px solid #f1f3f4; }
.tab { width: 250px; height: 52px; display: flex; align-items: center; gap: 14px; padding-left: 16px; font-size: 14px; color: #444746; }
.tab.on { color: #0b57d0; border-bottom: 3px solid #0b57d0; font-weight: 500; }

/* inbox rows */
.st-key-rows { gap: 0 !important; }
[class*="st-key-row-"] { border-bottom: 1px solid #f1f3f4; padding: 0 12px 0 8px; }
[class*="st-key-row-"]:hover { box-shadow: inset 1px 0 0 #dadce0, inset -1px 0 0 #dadce0, 0 1px 3px rgba(60,64,67,.3); }
[class*="st-key-row-r-"] { background: #f2f6fc; }
[class*="st-key-row-"] [data-testid="stHorizontalBlock"] { gap: 8px; }
[class*="st-key-open-"] button { border: none; background: transparent; box-shadow: none; padding: 0; min-height: 40px;
  width: 100%; justify-content: flex-start; }
[class*="st-key-open-"] button:hover, [class*="st-key-open-"] button:focus { background: transparent; color: inherit; }
[class*="st-key-open-"] button > div, [class*="st-key-open-"] button [data-testid="stMarkdownContainer"] { width: 100%; overflow: hidden; }
[class*="st-key-open-"] button p { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: left;
  color: #5f6368; font-size: 14px; margin: 0; }
[class*="st-key-open-"] button strong { color: #1f1f1f; }
[class*="st-key-row-u-"] button strong { font-weight: 700; }
[class*="st-key-row-r-"] button strong { font-weight: 400; }
.rowicons { display: flex; gap: 10px; align-items: center; height: 40px; }
.rowdate { text-align: right; font-size: 12px; color: #5f6368; line-height: 40px; }
.rowdate.unread { font-weight: 700; color: #1f1f1f; }

/* reading view */
.st-key-back button { border: none; background: transparent; box-shadow: none; color: #444746; padding: 0 8px; }
.subj { display: flex; align-items: center; gap: 12px; margin: 6px 0 18px 56px; }
.subj h2 { font-size: 22px; font-weight: 400; color: #1f1f1f; margin: 0; padding: 0; }
.chip { font-size: 12px; background: #ddd; color: #444746; border-radius: 4px; padding: 1px 6px; }
.msg { display: flex; gap: 16px; padding: 4px 0 16px 0; }
.msg .meta { flex: 1; min-width: 0; }
.from { display: flex; align-items: baseline; gap: 6px; font-size: 14px; }
.from b { font-weight: 700; color: #1f1f1f; } .from .addr, .to, .when { font-size: 12px; color: #5f6368; }
.when { margin-left: auto; white-space: nowrap; }
.body { font-size: 14px; color: #222; line-height: 1.6; margin-top: 14px; font-family: Arial, sans-serif; }
.body .lead { font-size: 16px; font-weight: 700; margin-bottom: 4px; }
.body h4 { font-size: 14px; font-weight: 700; margin: 18px 0 4px 0; padding: 0; color: #222; }
.body ol, .body ul { padding-left: 22px; margin: 4px 0; }
.body p { margin: 4px 0; }
.sig { color: #5f6368; margin-top: 18px; font-size: 13px; }
.thread-sep { border-top: 1px solid #e0e0e0; margin: 8px 0 12px 56px; }
/* Citations as numbered footnotes: plain HTML that renders in any email client */
sup.fn { font-size: 11px; color: #0b57d0; font-weight: 500; margin-left: 1px; }
.sources { border-top: 1px solid #e0e0e0; margin-top: 18px; padding-top: 4px; }
.sources ol { padding-left: 22px; margin: 4px 0; }
.sources li { font-size: 13px; line-height: 1.5; margin-bottom: 6px; color: #3c4043; }
.sources q { font-style: italic; }
table.opts { border-collapse: collapse; font-size: 13px; margin: 6px 0; }
table.opts th { font-weight: 700; } table.opts th, table.opts td { border-bottom: 1px solid #e0e0e0; padding: 4px 16px 4px 0; text-align: left; }
.badge { font-size: 11px; font-weight: 700; padding: 1px 6px; border-radius: 4px; color: #b3261e; border: 1px solid #b3261e; }
.note { font-size: 12px; color: #5f6368; }
.warn { font-size: 13px; background: #fef7e0; border-left: 3px solid #f9ab00; padding: 4px 10px; margin: 6px 0; }
/* CPL handoff: the drafted text plus a mailto: button, which real email clients support */
.cpl-draft { border: 1px solid #dadce0; border-radius: 8px; padding: 10px 14px; margin: 10px 0 12px 0; background: #fff; }
.cpl-draft .head { font-size: 13px; color: #5f6368; line-height: 1.7; border-bottom: 1px solid #f1f3f4; padding-bottom: 6px;
  margin-bottom: 8px; }
.cpl-draft .head b { display: inline-block; width: 58px; font-weight: 500; }
.cpl-draft .text { white-space: pre-wrap; }
a.mailbtn { display: inline-flex; align-items: center; gap: 8px; background: #0b57d0; color: #fff !important;
  border-radius: 18px; padding: 8px 18px; text-decoration: none !important; font: 500 14px Roboto, Arial, sans-serif; }
a.mailbtn:hover { background: #0a4cb8; box-shadow: 0 1px 3px rgba(60,64,67,.3); }
[data-testid="stForm"] { border: none; border-radius: 16px; box-shadow: 0 1px 3px rgba(60,64,67,.3), 0 4px 8px 3px rgba(60,64,67,.15);
  margin-left: 56px; width: calc(100% - 56px); padding: 12px 16px; }
[data-testid="stFormSubmitButton"] button { border-radius: 18px; padding: 0 24px; font-weight: 500; }
.st-key-footer p { font-size: 11px !important; color: #80868b !important; }
</style>
""")


# ---------------------------------------------------------------- formatting

def recommended(ind: dict) -> dict:
    return next(o for o in ind["options"] if o["label"] == "Recommended")


def monthly(ind: dict) -> float:
    return recommended(ind)["annual_premium"] / 12


def headline(ind: dict) -> str:
    """First line of the email body, computed from indications.json."""
    return (f"About ${monthly(ind):,.0f}/month for "
            f"${recommended(ind)['aggregate_limit'] / 1_000_000:g}M of cyber coverage")


def subject(client: dict) -> str:
    return f"{client['name']} renews {client['renewal_month']}: cyber is ready to offer"


def sent_time(item: str, clients: list[dict]) -> str:
    """Mock send times on the indication date: the digest first, then one email per client."""
    order = [DIGEST] + [c["id"] for c in clients]
    return f"7:{30 + 2 * order.index(item):02d} AM"


def long_date(ind: dict, time: str) -> str:
    return date.fromisoformat(ind["indication_date"]).strftime("%a, %b %-d, %Y, ") + time


def section_label(section_id: str) -> str:
    title = specimen.by_id().get(section_id, {}).get("title", "")
    if section_id.startswith("DEC.Item"):
        return f"Declarations, Item {section_id.removeprefix('DEC.Item')}"
    if section_id.startswith("IX."):
        return f"Definition of “{title}”"
    if re.fullmatch(r"[IVX]+\.[A-W]", section_id):            # insuring agreements and exclusions
        return f"{section_id} {title}"
    return f"Section {section_id.split('.')[0]}: {title}"


class Sources:
    """Numbered footnotes for one email or reply: one number per policy section, listing its quotes."""

    def __init__(self):
        self.quotes: dict[str, list[str]] = {}       # section_id -> quotes, in first-cited order

    def refs(self, citations: list[dict]) -> str:
        nums = set()
        for c in citations:
            quotes = self.quotes.setdefault(c["section_id"], [])
            if c["quote"] not in quotes:
                quotes.append(c["quote"])
            nums.add(list(self.quotes).index(c["section_id"]) + 1)
        return f'<sup class="fn">{",".join(str(n) for n in sorted(nums))}</sup>' if nums else ""

    def html(self) -> str:
        if not self.quotes:
            return ""
        rows = "".join(
            f'<li><b>{escape(section_label(sid))}</b> (p. {specimen.by_id().get(sid, {}).get("page", "?")}): '
            + "; ".join(f"<q>{escape(q)}</q>" for q in quotes) + "</li>"
            for sid, quotes in self.quotes.items()
        )
        return (f'<div class="sources"><h4>Policy sources</h4><ol>{rows}</ol>'
                f'<div class="note">{escape(config.SAMPLE_FORM_LABEL)}</div></div>')


def message(av_class: str, initial: str, name: str, addr: str, to: str, when: str, body: str) -> str:
    return (f'<div class="msg"><span class="avatar av-big {av_class}">{initial}</span><div class="meta">'
            f'<div class="from"><b>{escape(name)}</b><span class="addr">&lt;{escape(addr)}&gt;</span>'
            f'<span class="when">{escape(when)}</span></div><div class="to">to {escape(to)}</div>'
            f'<div class="body">{body}</div></div></div>')


def options_table(ind: dict) -> str:
    rows = "".join(
        f"<tr><td>{escape(o['label'])}</td><td>${o['aggregate_limit']:,}</td><td>${o['retention']:,}</td>"
        f"<td>${o['annual_premium']:,}</td><td>${o['annual_premium'] / 12:,.2f}</td></tr>"
        for o in ind["options"]
    )
    return ('<h4>Options <span class="badge">MOCK DATA</span></h4>'
            '<table class="opts"><tr><th>Option</th><th>Aggregate limit</th><th>Retention</th>'
            f'<th>Annual premium</th><th>Monthly</th></tr>{rows}</table>'
            f'<div class="note">{escape(ind["carrier"])}. Mock indication, not a real carrier quote.</div>')


@st.cache_resource
def daily_usage() -> dict:
    """Question count shared by every visitor's session in this server process."""
    return {"day": None, "count": 0, "lock": threading.Lock()}


def question_allowed() -> str | None:
    """None if a reply may be sent; otherwise why not. Limits apply to the public demo only."""
    if not config.PUBLIC_DEMO:
        return None
    if state.questions_asked >= config.MAX_QUESTIONS_PER_SESSION:
        return f"You've reached this demo's limit of {config.MAX_QUESTIONS_PER_SESSION} questions per visit."
    usage = daily_usage()
    with usage["lock"]:
        today = date.today().isoformat()
        if usage["day"] != today:
            usage.update(day=today, count=0)
        if usage["count"] >= config.MAX_QUESTIONS_PER_DAY:
            return "The demo has reached today's question limit. Please try again tomorrow."
        usage["count"] += 1
    state.questions_asked += 1
    return None


def open_item(item) -> None:
    state.open = item
    if item:
        state.read.add(item)


# ---------------------------------------------------------------- frame

clients = json.loads(config.CLIENTS_JSON.read_text())
agent = clients[0]["agent"]
initials = "".join(w[0] for w in agent.split())[:2]
items = [DIGEST] + [c["id"] for c in clients]
unread = [i for i in items if i not in state.read]

st.html(f"""
<div class="topbar">
  <div class="brand">{icon(I_MENU, 24)}{icon(I_MAIL, 30, "#5f6368")}<span>Mail</span></div>
  <div class="search">{icon(I_SEARCH, 22)}<span>Search mail</span></div>
  <div class="right">
    <span class="avatar av-me" title="{escape(agent)}">{escape(initials)}</span></div>
</div>
""")

nav_col, main_col = st.columns([1, 5.4], gap="small")

with nav_col:
    st.html(f"""
    <div class="compose">{icon(I_EDIT, 22, "#001d35")}Compose</div>
    <div class="nav">
      <div class="item active">{icon(I_INBOX, 20, "#041e49")}Inbox<span class="count">{len(unread) or ""}</span></div>
      <div class="item">{icon(I_STAR)}Starred</div>
      <div class="item">{icon(I_CLOCK)}Snoozed</div>
      <div class="item">{icon(I_SEND)}Sent</div>
      <div class="item">{icon(I_FILE)}Drafts</div>
      <div class="labels">Labels</div>
      <div class="item">{icon(I_LABEL, 20, "#1a73e8")}Cyber renewals</div>
    </div>
    """)
    if config.PUBLIC_DEMO:
        # Shared link: visitors only read cached briefs; the only live calls are replies.
        controls, use_cache, regenerate = None, True, False
    else:
        controls = st.expander("Demo controls")
        with controls:
            use_cache = st.toggle("Use cached brief", value=True,
                                  help="Load the saved brief instead of calling the API. Replies stay live.")
            regenerate = st.button("Regenerate brief", disabled=use_cache or state.open in (None, DIGEST))
            st.caption(f"Model: `{config.MODEL}`")

panel = main_col.container(key="panel")

# ---------------------------------------------------------------- inbox list

if state.open is None:
    with panel:
        st.html(f"""
        <div class="toolbar">{icon(I_CHECKBOX)}{icon(I_REFRESH)}{icon(I_MORE)}
          <span class="range">1–{len(items)} of {len(items)}</span></div>
        <div class="tabs"><div class="tab on">{icon(I_INBOX, 20, "#0b57d0")}Primary</div></div>
        """)
        with st.container(key="rows"):
            snippets = {DIGEST: ("This week: 4 renewals with cyber ready",
                                 "Cyber is ready to offer on " + ", ".join(c["name"] for c in clients))}
            for c in clients:
                snippets[c["id"]] = (subject(c), f"{headline(indication(c['id']))}. Why it matters, "
                                                 "talking points and objections, ready for your call.")
            for item in items:
                is_unread = item not in state.read
                subj, snip = snippets[item]
                with st.container(key=f"row-{'u' if is_unread else 'r'}-{item}"):
                    icons_col, text_col, date_col = st.columns([0.55, 9, 0.9], vertical_alignment="center")
                    icons_col.html(f'<div class="rowicons">{icon(I_CHECKBOX, 20, "#8e918f")}'
                                   f'{icon(I_STAR, 20, "#8e918f")}</div>')
                    label = f"**{SENDER}**  **{subj}** — {snip}".replace("$", "\\$")
                    text_col.button(label, key=f"open-{item}", on_click=open_item, args=(item,),
                                    use_container_width=True)
                    date_col.html(f'<div class="rowdate{" unread" if is_unread else ""}">'
                                  f'{sent_time(item, clients)}</div>')
    st.stop()

# ---------------------------------------------------------------- reading view: shared top

with panel:
    st.button("Inbox", icon=":material/arrow_back:", key="back", on_click=open_item, args=(None,))

# ---------------------------------------------------------------- digest email

if state.open == DIGEST:
    with panel:
        first_ind = indication(clients[0]["id"])
        lines = "".join(
            f"<li><b>{escape(c['name'])}</b> ({escape(industry_note(c['industry'])['industry'])}), "
            f"renews {escape(c['renewal_month'])}: {escape(headline(indication(c['id'])))}</li>"
            for c in clients
        )
        body = (f"<p>Hi {escape(agent.split()[0])},</p>"
                f"<p>Cyber is ready to offer on these renewals. Each has its own email with a two-minute brief.</p>"
                f"<ol>{lines}</ol>"
                f'<p class="note">Prices are monthly figures from mock indications. '
                f"{escape(config.SAMPLE_FORM_LABEL)}</p><div class='sig'>— {SENDER}</div>")
        st.html(f'<div class="subj"><h2>This week: {len(clients)} renewals with cyber ready</h2>'
                f'<span class="chip">Inbox</span></div>'
                + message("av-desk", "U", SENDER, SENDER_ADDR, "me", long_date(first_ind, sent_time(DIGEST, clients)),
                          body))
    st.stop()

# ---------------------------------------------------------------- brief (unchanged logic)

client_id = state.open
client = client_record(client_id)
ind = indication(client_id)
industry = industry_note(client["industry"])
cached = load_cache(client_id)

result = None
with panel:
    if use_cache:
        if cached:
            result = cached
        else:
            st.error(f"This email isn't available right now." if config.PUBLIC_DEMO else
                     f"No cached brief for {client['name']} yet. Turn off Use cached brief to generate one live.")
    else:
        if regenerate:
            state.briefs.pop(client_id, None)
        if client_id not in state.briefs:
            with st.spinner(f"Loading the email for {client['name']}..."):
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
                     "Use Regenerate brief or Use cached brief under Demo controls.")
            result = None

if controls is not None:
    with controls:
        if use_cache and cached:
            st.caption(f"Cached {cached['saved_at']} with {cached['model']}")
        if result and not use_cache and st.button("Save this brief to cache"):
            save_cache(client_id, result["brief"], result["report"], result["stats"])
            st.success("Saved.")

# ---------------------------------------------------------------- client email

with panel:
    parts = [f'<div class="lead">{escape(headline(ind))}</div>',
             f'<div class="note">{escape(client["name"])} · {escape(industry["industry"])} · '
             f'{escape(client["city"])}, {escape(client["state"])}</div>']
    sources = Sources()
    if result:
        brief, report = result["brief"], result["report"]
        parts.append(f'<h4>Why it matters</h4><p>{escape(brief["why_it_matters"])}</p>')
        parts.append(f'<h4>Opener</h4><p>{escape(fill_price(brief["opener"], ind))}</p>')
        removed = report["removed_claims"]
        if removed:
            parts.append(f'<div class="warn">{len(removed)} claim{"s" if len(removed) > 1 else ""} removed: '
                         "citation didn't match the policy.</div>")
        points = "".join(f"<li>{escape(p['text'])}{sources.refs(p['citations'])}</li>" for p in brief["talking_points"])
        parts.append(f"<h4>Talking points</h4><ol>{points}</ol>")
        objections = "".join(
            f"<li><b>“{escape(o['objection'])}”</b><br>{escape(o['response'])}{sources.refs(o['citations'])}</li>"
            for o in brief["objections"]
        )
        parts.append(f"<h4>Objections</h4><ul>{objections}</ul>")
    parts.append(options_table(ind))
    parts.append(sources.html() or f'<p class="note">{escape(config.SAMPLE_FORM_LABEL)}</p>')
    parts.append(f'<div class="sig">— {SENDER}</div>')
    when = long_date(ind, sent_time(client_id, clients))
    st.html(f'<div class="subj"><h2>{escape(subject(client))}</h2><span class="chip">Inbox</span></div>'
            + message("av-desk", "U", SENDER, SENDER_ADDR, "me", when, "".join(parts)))

    # Thread: replies under the email
    for n, item in enumerate(state.answers.get(client_id, [])):
        st.html('<div class="thread-sep"></div>'
                + message("av-me", escape(initials), agent, "you", SENDER, "just now",
                          f"<p>{escape(item['question'])}</p>"))
        a = item.get("answer")
        if a and a["answerable"]:
            note = ('<div class="warn">This coverage is in the policy form, but it is not included on this quote.</div>'
                    if a["in_policy_not_on_quote"] else "")
            reply_sources = Sources()
            body = f"<p>{escape(a['answer'])}{reply_sources.refs(a['citations'])}</p>{note}"
            st.html('<div class="thread-sep"></div>'
                    + message("av-desk", "U", SENDER, SENDER_ADDR, "me", "just now", body + reply_sources.html()))
        else:
            if a:
                why = escape(a["reason"])
                if item["report"]["rerouted"]:
                    why += " (Rerouted: the answer's citations didn't match the policy.)"
                draft = a["cpl_message"]
            else:
                why = "I couldn't confirm an answer from the policy wording, so this one needs your CPL."
                draft = (f"Hi, my client {client['name']} ({industry['industry'].lower()}) asked: "
                         f"\"{item['question']}\" Can you advise how this policy responds?")
            # Nothing is sent. A mailto: link opens a pre-filled message in the agent's own
            # email client, which is what a real email can offer (no scripts or copy buttons).
            subj = f"Coverage question: {client['name']}"
            href = (f"mailto:{quote(config.CPL_EMAIL)}?subject={quote(subj)}&body={quote(draft)}")
            to_line = escape(config.CPL_EMAIL) or "Your CPL (add their address)"
            st.html('<div class="thread-sep"></div>'
                    + message("av-desk", "U", SENDER, SENDER_ADDR, "me", "just now",
                              f"<p><b>This one needs your CPL</b></p><p>{why}</p>"
                              f'<div class="cpl-draft"><div class="head"><div><b>To</b>{to_line}</div>'
                              f'<div><b>Subject</b>{escape(subj)}</div></div>'
                              f'<div class="text">{escape(draft)}</div></div>'
                              f'<a class="mailbtn" href="{escape(href)}" target="_blank">'
                              f'{icon(I_MAIL, 18, "#ffffff")}Email your CPL</a>'
                              '<p class="note">Opens a new message with this text, ready to review and send.</p>'))

    with st.form("reply", clear_on_submit=True):
        question = st.text_area("Reply", placeholder="Reply to ask a question about this policy",
                                label_visibility="collapsed", height=90, max_chars=config.MAX_QUESTION_CHARS)
        submitted = st.form_submit_button("Send", type="primary")
    if config.PUBLIC_DEMO:
        st.caption("Demo only: please don't enter real client information.")
    blocked = question_allowed() if submitted and question.strip() else None
    if blocked:
        st.warning(blocked)
    elif submitted and question.strip():
        q = question.strip()
        with st.spinner("Checking the policy..."):
            try:
                answer, qa_report, qa_stats = ask(client_id, q)
                item = {"question": q, "answer": answer.model_dump(), "report": qa_report}
                state.last_call = {"kind": "question", **qa_stats}
            except (StructuredOutputError, anthropic.APIError) as e:
                item = {"question": q, "error": str(e)}
        state.answers.setdefault(client_id, []).append(item)
        st.rerun()

    # Footer (local runs only: visitors don't need cost details)
    if config.PUBLIC_DEMO:
        st.stop()
    last = state.last_call
    foot = []
    if use_cache and result:
        foot.append("Brief loaded from cache (no API call)")
    if last:
        foot.append(f"Last call ({last['kind']}): ${last['cost_usd']:.4f}, {last['latency_s']:.1f}s")
    foot.append(f"Claims removed by verifier: {len(result['report']['removed_claims']) if result else 0}")
    with st.container(key="footer"):
        st.caption(" · ".join(foot).replace("$", "\\$"))
