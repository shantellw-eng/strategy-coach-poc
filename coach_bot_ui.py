import os
import re
import json
from typing import Optional, Tuple, List

import streamlit as st
import anthropic

# ------------------------------------------------------------
# Strategy Coach (POC) - Streamlit Front-End (Claude)
#
# Setup:
# 1) Put your system prompt in system_prompt.txt (same folder as this file)
# 2) Set ANTHROPIC_API_KEY in Streamlit secrets or environment
# 3) Set APP_PASSWORD in Streamlit secrets (for Cloud) or environment (local)
# 4) Run: streamlit run coach_bot_ui.py
# ------------------------------------------------------------

STATE_OPEN = "<STATE_JSON>"
STATE_CLOSE = "</STATE_JSON>"

PHASES = ["objective", "scope", "advantage", "draft", "refine"]
PHASE_LABELS = {
    "objective": "Objective",
    "scope": "Scope",
    "advantage": "Advantage",
    "draft": "Draft",
    "refine": "Refine",
}

# Initial-only examples (optional). Consider removing entirely later.
#INITIAL_EXAMPLES = [
#    "Objective: Double revenue within 12 months.",
#    "Objective: Reach $5m ARR within 18 months while maintaining gross margin above 60%.",
#    "Objective: Increase retention from 85% to 92% within 12 months.",
#]

COMMITMENT_QUESTION = "Are you prepared to back this with resources and focus?"


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="Strategy Coach",
    layout="centered",
    # Keep the clean look, but allow toggle + activity indicator via Streamlit chrome
    initial_sidebar_state="collapsed",
)

# -----------------------------
# Styling (Centre-inspired: clean, blue, lots of whitespace)
# -----------------------------
def inject_css():
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

          :root{
            --brand:#003366;
            --brand-mid:#0B63B6;
            --brand-dark:#002244;
            --ink:#0B1220;
            --muted:#5B6B7A;
            --bg:#FFFFFF;
            --card:#F4F7FB;
            --border:#DDE5EF;
            --accent:#E8F0FA;
          }

          html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
          }

          /* Keep Streamlit toolbar visible but hide the bar background */
          #MainMenu {visibility: hidden;}
          footer {visibility: hidden;}
          header[data-testid="stHeader"] {
            background: transparent !important;
            box-shadow: none !important;
          }

          div[data-testid="stToolbar"]{
            opacity: 0.25;
            transition: opacity 120ms ease-in-out;
          }
          div[data-testid="stToolbar"]:hover{ opacity: 1; }

          /* Account for Streamlit's toolbar height so our header sits below it */
          .block-container {
            padding-top: 0rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 860px;
          }

          /* Full-bleed header — negative margins escape the container */
          .cbg-header-wrap {
            margin: -1rem -1rem 2rem -1rem;
          }

          /* Brand header bar — square/blocky per Centre CI */
          .cbg-header {
            background: var(--brand);
            color: white;
            padding: 14px 36px;
            display: flex;
            align-items: center;
            gap: 24px;
            border-radius: 0;
          }
          .cbg-header .org {
            font-size: 0.70rem;
            font-weight: 500;
            opacity: 0.65;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            line-height: 1;
            margin-bottom: 5px;
          }
          .cbg-header .tool {
            font-size: 1.1rem;
            font-weight: 700;
            line-height: 1.2;
            letter-spacing: -0.01em;
            color: white;
          }
          .cbg-header .hdr-divider {
            width: 1px;
            height: 38px;
            background: rgba(255,255,255,0.22);
            flex-shrink: 0;
          }
          .cbg-header .tagline {
            font-size: 0.80rem;
            opacity: 0.55;
            margin-top: 4px;
            font-style: italic;
          }

          /* Centre wordmark SVG */
          .cbg-wordmark {
            width: 140px;
            height: 48px;
            flex-shrink: 0;
          }

          /* Hero intro */
          .hero-intro {
            text-align: center;
            padding: 0.5rem 0 1.5rem 0;
          }
          .hero-intro h2 {
            font-size: 1.65rem;
            font-weight: 700;
            color: var(--ink);
            letter-spacing: -0.02em;
            margin-bottom: 0.6rem;
          }
          .hero-intro p {
            font-size: 1rem;
            color: var(--muted);
            line-height: 1.65;
            max-width: 580px;
            margin: 0 auto;
          }

          /* Intro card — square corners per Centre CI */
          .intro-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-left: 4px solid var(--brand-mid);
            border-radius: 0;
            padding: 20px 24px;
            margin: 0 0 10px 0;
          }
          .intro-card .card-title {
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            color: var(--brand-mid);
            margin-bottom: 10px;
          }
          .intro-card p {
            font-size: 0.96rem;
            color: var(--ink);
            line-height: 1.6;
            margin: 0 0 10px 0;
          }
          .intro-card p:last-child { margin-bottom: 0; }

          /* Step progress indicator */
          .step-progress {
            display: flex;
            align-items: center;
            margin: 24px 0 20px 0;
            padding: 0 4px;
          }
          .step-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            flex: 1;
          }
          /* Connecting line between steps */
          .step-item:not(:last-child)::after {
            content: '';
            position: absolute;
            top: 14px;
            left: calc(50% + 14px);
            right: calc(-50% + 14px);
            height: 2px;
            background: var(--border);
            z-index: 0;
          }
          .step-item.done:not(:last-child)::after {
            background: var(--brand-mid);
          }
          /* Step circle */
          .step-circle {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: 2px solid var(--border);
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.72rem;
            font-weight: 700;
            color: var(--muted);
            position: relative;
            z-index: 1;
            flex-shrink: 0;
          }
          .step-item.current .step-circle {
            border-color: var(--brand);
            background: var(--brand);
            color: white;
          }
          .step-item.done .step-circle {
            border-color: var(--brand-mid);
            background: var(--brand-mid);
            color: white;
          }
          /* Tick for done */
          .step-item.done .step-circle::after {
            content: '✓';
            font-size: 0.75rem;
            font-weight: 700;
          }
          /* Step label */
          .step-label {
            margin-top: 6px;
            font-size: 0.72rem;
            font-weight: 500;
            color: var(--muted);
            text-align: center;
            letter-spacing: 0.02em;
            white-space: nowrap;
          }
          .step-item.current .step-label {
            color: var(--brand);
            font-weight: 700;
          }
          .step-item.done .step-label {
            color: var(--brand-mid);
          }

          /* Chat bubbles — square */
          [data-testid="stChatMessage"] {
            border-radius: 3px;
            padding: 4px 0;
          }

          /* Buttons — square, brand blue */
          .stButton>button {
            border-radius: 3px;
            font-size: 0.88rem;
            padding: 0.45rem 0.9rem;
            border: 1.5px solid var(--border);
            font-weight: 500;
          }
          .stButton>button:hover {
            border-color: var(--brand-mid);
            color: var(--brand-mid);
          }

          /* Send button — square, navy, not red */
          div[data-testid="stForm"] button[kind="primary"],
          button[kind="primary"],
          .stFormSubmitButton button {
            background: var(--brand) !important;
            border-color: var(--brand) !important;
            border-radius: 3px !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em !important;
            color: white !important;
          }
          div[data-testid="stForm"] button[kind="primary"]:hover,
          .stFormSubmitButton button:hover {
            background: var(--brand-dark) !important;
            border-color: var(--brand-dark) !important;
          }

          section[data-testid="stSidebar"] {
            border-right: 1px solid var(--border);
          }
          /* Agent-style conversation transcript — single column, no bubbles */
          .chat-feed {
            display: flex;
            flex-direction: column;
            gap: 0;
            margin: 8px 0 16px 0;
          }
          /* Each exchange = one Marvin turn + optional user reply */
          .chat-exchange {
            border-bottom: 1px solid var(--border);
            padding: 20px 0;
          }
          .chat-exchange:last-child {
            border-bottom: none;
          }
          /* Marvin label */
          .chat-speaker {
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
          }
          .chat-speaker.marvin {
            color: var(--brand);
          }
          .chat-speaker.user {
            color: var(--muted);
          }
          /* Message text */
          .chat-text {
            font-size: 0.97rem;
            line-height: 1.7;
            color: var(--ink);
          }
          .chat-text.marvin-text {
            color: var(--ink);
          }
          .chat-text.user-text {
            color: #4B5563;
            font-style: italic;
            padding-left: 14px;
            border-left: 2px solid #C5D8EA;
            margin-top: 14px;
          }

        </style>
        """,
        unsafe_allow_html=True,
    )

def load_system_prompt() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "system_prompt.txt")
    if not os.path.exists(path):
        raise FileNotFoundError(f"system_prompt.txt not found next to coach_bot_ui.py. Expected at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def split_user_text_and_state(full_text: str) -> Tuple[str, Optional[dict]]:
    if not full_text:
        return "", None
    start = full_text.rfind(STATE_OPEN)
    end = full_text.rfind(STATE_CLOSE)
    if start == -1 or end == -1 or end < start:
        return full_text.strip(), None
    user_text = full_text[:start].strip()
    blob = full_text[start + len(STATE_OPEN) : end].strip()
    try:
        return user_text, json.loads(blob)
    except json.JSONDecodeError:
        return user_text, None


def normalise_state(state: dict) -> dict:
    def as_str(x):
        return x if isinstance(x, str) else ("" if x is None else str(x))

    def as_list_str(x):
        if x is None:
            return []
        if isinstance(x, list):
            return [as_str(i).strip() for i in x if as_str(i).strip()]
        s = as_str(x).strip()
        return [s] if s else []

    out = {
        "objective": as_str(state.get("objective", "")).strip(),
        "scope": as_str(state.get("scope", "")).strip(),
        "advantage": as_str(state.get("advantage", "")).strip(),
        "strategic_assumptions": as_list_str(state.get("strategic_assumptions", []))[:5],
        "current_phase": as_str(state.get("current_phase", "")).strip(),
        "next_question": as_str(state.get("next_question", "")).strip(),
        "draft_statement": as_str(state.get("draft_statement", "")).strip(),
        "refined_statement": as_str(state.get("refined_statement", "")).strip(),
    }
    if out["current_phase"] not in PHASES:
        out["current_phase"] = "objective"
    return out


def is_affirmation(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    yes_patterns = [
        r"^\s*yes\s*$",
        r"^\s*yep\s*$",
        r"^\s*yeah\s*$",
        r"^\s*yeh\s*$",
        r"^\s*absolutely\s*$",
        r"^\s*i\s+am\s*$",
        r"^\s*we\s+are\s*$",
        r"^\s*ok\s*$",
        r"^\s*okay\s*$",
        r"^\s*sure\s*$",
        r"^\s*let'?s\s+do\s+it\s*$",
    ]
    return any(re.search(p, t) for p in yes_patterns)


def require_password_gate() -> None:
    """
    Simple password gate:
    - Streamlit Cloud: put APP_PASSWORD in Secrets
    - Local: set APP_PASSWORD env var
    """
    expected = st.secrets.get("APP_PASSWORD") or os.environ.get("APP_PASSWORD")
    if not expected:
        st.error("APP_PASSWORD is not set in Streamlit secrets or environment.")
        st.stop()

    if st.session_state.get("authed", False):
        return

    st.markdown("##### For Centre for Business Growth program participants")
    st.caption("Enter your access password to continue.")
    with st.form("password_form"):
        pw = st.text_input("Access password", type="password")
        submitted = st.form_submit_button("Continue", type="primary")
        if submitted:
            if pw == expected:
                st.session_state.authed = True
                st.rerun()
            else:
                st.error("Password not recognised. Try again.")
    st.stop()


def call_model(conversation_messages: List[dict], session_mode: str) -> str:
    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set (Streamlit secrets or environment variable).")

    model_name = (
        st.secrets.get("ANTHROPIC_MODEL")
        or os.environ.get("ANTHROPIC_MODEL")
        or "claude-3-5-sonnet-latest"
    )

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = ""
    if conversation_messages and conversation_messages[0]["role"] == "system":
        system_prompt = conversation_messages[0]["content"]

    if session_mode == "Board":
        mode_hint = (
            "\n\nSession mode: Board.\n"
            "- Be more direct and exact.\n"
            "- Pressure-test targets with practical questions.\n"
            "- Keep it grounded and short.\n"
        )
    else:
        mode_hint = (
            "\n\nSession mode: Workshop.\n"
            "- Keep it practical and easy to answer.\n"
            "- Ask one question at a time.\n"
            "- Use plain language.\n"
        )

    system_prompt = f"{system_prompt}{mode_hint}"

    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in conversation_messages
        if m["role"] in ["user", "assistant"]
    ]

    response = client.messages.create(
        model=model_name,
        max_tokens=1100,
        temperature=0.4,
        system=system_prompt,
        messages=messages,
    )

    return "".join(block.text for block in response.content if hasattr(block, "text"))


def render_phase_tracker(current_phase: str, objective: str, scope: str, advantage: str):
    phase = current_phase if current_phase in PHASES else "objective"

    def done(val: str) -> bool:
        return bool((val or "").strip())

    phase_done = {
        "objective": done(objective),
        "scope": done(scope),
        "advantage": done(advantage),
        "draft": False,
        "refine": False,
    }

    steps_html = []
    for i, p in enumerate(PHASES):
        is_current = p == phase
        is_done = phase_done.get(p, False)

        if is_done:
            cls = "step-item done"
            circle_content = ""  # tick added via CSS ::after
        elif is_current:
            cls = "step-item current"
            circle_content = str(i + 1)
        else:
            cls = "step-item"
            circle_content = str(i + 1)

        label = PHASE_LABELS[p]
        steps_html.append(
            f'<div class="{cls}">'
            f'  <div class="step-circle">{circle_content}</div>'
            f'  <div class="step-label">{label}</div>'
            f'</div>'
        )

    st.markdown(
        '<div class="step-progress">' + "".join(steps_html) + "</div>",
        unsafe_allow_html=True,
    )


# -----------------------------
# App start
# -----------------------------
inject_css()

# Header bar — shown on ALL screens including login
def render_header():
    st.markdown(
        """
        <div class="cbg-header-wrap">
          <div class="cbg-header">
            <svg class="cbg-wordmark" viewBox="0 0 140 46" fill="none" xmlns="http://www.w3.org/2000/svg">
              <text x="0" y="13" font-family="Inter,sans-serif" font-size="8.5" font-weight="500"
                    fill="rgba(255,255,255,0.60)" letter-spacing="0.6">AUSTRALIAN CENTRE FOR</text>
              <text x="0" y="30" font-family="Inter,sans-serif" font-size="16" font-weight="800"
                    fill="white" letter-spacing="0.1">Business Growth</text>
              <line x1="0" y1="36" x2="140" y2="36" stroke="rgba(255,255,255,0.18)" stroke-width="0.8"/>
              <text x="0" y="44" font-family="Inter,sans-serif" font-size="7.5" font-weight="400"
                    fill="rgba(255,255,255,0.45)" letter-spacing="0.3">Adelaide University</text>
            </svg>
            <div class="hdr-divider"></div>
            <div>
              <div class="tool">Marvin &mdash; Strategy Coach</div>
              <div class="tagline">Good questions. Clear thinking. A strategy you can actually use.</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

render_header()
require_password_gate()

# Hero intro
st.markdown(
    """
    <div class="hero-intro">
      <h2>Where does your business need to go?</h2>
      <p>A good strategy isn't a long document. It's a clear answer to three questions: what are you trying to achieve, who are you focused on, and why do customers choose you.</p>
      <p style="margin-top:0.75rem;">Most leaders know the answer intuitively. Marvin helps you find the words.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Intro card
with st.container():
    st.markdown(
        """
        <div class="intro-card">
          <div class="card-title">What to expect</div>
          <p>Marvin will ask you a short series of focused questions about your objective, your customers, and what you're genuinely better at than the competition.</p>
          <p>The conversation takes 10&ndash;15 minutes. At the end, you'll have a clear Strategy Statement &mdash; in plain language &mdash; that you can actually use.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Init session state
if "strategy_state" not in st.session_state:
    st.session_state.strategy_state = {
        "objective": "",
        "scope": "",
        "advantage": "",
        "strategic_assumptions": [],
        "current_phase": "objective",
        "next_question": "",
        "draft_statement": "",
        "refined_statement": "",
    }

if "chat" not in st.session_state:
    system_prompt = load_system_prompt()
    st.session_state.chat = [
        {"role": "system", "content": system_prompt},
        {
            "role": "assistant",
            "content": (
                "We’ll build this step by step.\n\n"
                "Before we go further, what does the business do, and who pays you?"
            ),
        },
    ]

if "composer_text" not in st.session_state:
    st.session_state.composer_text = ""

if "last_error" not in st.session_state:
    st.session_state.last_error = ""

if "has_started" not in st.session_state:
    st.session_state.has_started = False

if "final_strategy" not in st.session_state:
    st.session_state.final_strategy = None

if "is_locked" not in st.session_state:
    st.session_state.is_locked = False

if "assistant_asked_commitment" not in st.session_state:
    st.session_state.assistant_asked_commitment = False

# Sidebar
with st.sidebar:
    st.subheader("Session")
    session_mode = st.radio(
        "Mode",
        options=["Workshop", "Board"],
        index=0,
        help="Workshop is practical and easy-to-answer. Board is more direct and exact.",
        disabled=st.session_state.is_locked,
    )

    st.divider()
    ss = st.session_state.strategy_state
    phase = ss.get("current_phase", "objective") or "objective"
    st.subheader("Current focus")
    st.markdown(f"**{PHASE_LABELS.get(phase, 'Objective')}**")

    st.divider()
    st.subheader("Working Strategy")
    st.caption("Updates as the session progresses.")
    st.markdown("**Objective**")
    st.write(ss.get("objective") or "—")
    st.markdown("**Scope**")
    st.write(ss.get("scope") or "—")
    st.markdown("**Advantage**")
    st.write(ss.get("advantage") or "—")

    if ss.get("strategic_assumptions") and phase in ["draft", "refine"]:
        st.markdown("**Assumptions**")
        for a in (ss.get("strategic_assumptions") or [])[:5]:
            st.write(f"- {a}")

    if st.session_state.final_strategy:
        st.divider()
        st.subheader("Final Strategy")
        fs = st.session_state.final_strategy
        if fs.get("draft"):
            st.markdown("**Draft**")
            st.write(fs["draft"])
        if fs.get("refined"):
            st.markdown("**Refined**")
            st.write(fs["refined"])
        if fs.get("assumptions"):
            st.markdown("**Assumptions**")
            for a in fs["assumptions"][:5]:
                st.write(f"- {a}")

    st.divider()
    st.subheader("Quick actions")
    st.caption("Use to reopen a component mid-session.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Revise objective", disabled=st.session_state.is_locked):
            st.session_state.composer_text = "Revise objective: "
            st.rerun()
        if st.button("Revise scope", disabled=st.session_state.is_locked):
            st.session_state.composer_text = "Revise scope: "
            st.rerun()
    with col2:
        if st.button("Revise advantage", disabled=st.session_state.is_locked):
            st.session_state.composer_text = "Revise advantage: "
            st.rerun()
        if st.button("Clear input", disabled=st.session_state.is_locked):
            st.session_state.composer_text = ""
            st.rerun()

    st.divider()
    if st.button("Reset session"):
        for k in [
            "chat",
            "strategy_state",
            "composer_text",
            "last_error",
            "has_started",
            "final_strategy",
            "is_locked",
            "assistant_asked_commitment",
        ]:
            st.session_state.pop(k, None)
        st.rerun()

    if st.session_state.last_error:
        st.warning(st.session_state.last_error)

# Phase tracker
ss = st.session_state.strategy_state
render_phase_tracker(
    current_phase=ss.get("current_phase", "objective"),
    objective=ss.get("objective", ""),
    scope=ss.get("scope", ""),
    advantage=ss.get("advantage", ""),
)

# Chat messages — agent-style transcript, single column
def render_chat_messages(messages):
    import html as html_module

    # Pair messages into exchanges: each assistant message followed by optional user reply
    exchanges = []
    current_assistant = None
    current_user = None

    for m in messages:
        if m["role"] == "system":
            continue
        if m["role"] == "assistant":
            # If we have a pending exchange, flush it
            if current_assistant is not None:
                exchanges.append((current_assistant, current_user))
                current_user = None
            current_assistant = m["content"]
        elif m["role"] == "user":
            current_user = m["content"]

    # Flush final
    if current_assistant is not None:
        exchanges.append((current_assistant, current_user))

    html_parts = ['<div class="chat-feed">']
    for assistant_text, user_text in exchanges:
        safe_assistant = html_module.escape(assistant_text).replace("\n\n", "</p><p>").replace("\n", "<br>")
        html_parts.append('<div class="chat-exchange">')
        html_parts.append('<div class="chat-speaker marvin">Marvin</div>')
        html_parts.append(f'<div class="chat-text marvin-text"><p>{safe_assistant}</p></div>')
        if user_text:
            safe_user = html_module.escape(user_text).replace("\n", "<br>")
            html_parts.append(f'<div class="chat-text user-text">{safe_user}</div>')
        html_parts.append('</div>')

    html_parts.append('</div>')
    st.markdown("".join(html_parts), unsafe_allow_html=True)

render_chat_messages(st.session_state.chat)

# Examples (optional)
#if not st.session_state.has_started and not st.session_state.is_locked:
#    with st.expander("Need a starting example? (Optional)", expanded=False):
#cols = st.columns(3)
        #for i in range(3):
#            with cols[i]:
#                if st.button(f"Use example {i+1}", key=f"initial_ex_{i}"):
                    #st.session_state.composer_text = INITIAL_EXAMPLES[i]
                    #st.rerun()
                #st.caption(INITIAL_EXAMPLES[i])

# Composer
# Critical: clear_on_submit=True so we don't mutate st.session_state["composer_text"] after widget instantiation
with st.form("composer_form", clear_on_submit=True):
    composer = st.text_area(
        "Message",
        key="composer_text",
        placeholder="Type your message…",
        height=120,
        disabled=st.session_state.is_locked,
    )
    send = st.form_submit_button("Send", type="primary", disabled=st.session_state.is_locked)

if st.session_state.is_locked:
    st.info("Session complete. Use Reset to start again.")

# Send logic
if send and composer.strip() and not st.session_state.is_locked:
    user_text = composer.strip()

    # Lock flow after commitment question
    if st.session_state.assistant_asked_commitment and is_affirmation(user_text):
        st.session_state.is_locked = True
        st.session_state.chat.append({"role": "user", "content": user_text})
        st.session_state.chat.append({"role": "assistant", "content": "Good. Then it’s about focus and follow-through."})
        st.session_state.assistant_asked_commitment = False
        st.rerun()

    st.session_state.chat.append({"role": "user", "content": user_text})
    st.session_state.has_started = True

    try:
        raw = call_model(st.session_state.chat, session_mode=session_mode)
        user_facing, state = split_user_text_and_state(raw)

        st.session_state.chat.append({"role": "assistant", "content": user_facing})
        st.session_state.assistant_asked_commitment = (COMMITMENT_QUESTION in user_facing)

        if isinstance(state, dict):
            st.session_state.strategy_state = normalise_state(state)

            draft_stmt = (state.get("draft_statement") or "").strip()
            refined_stmt = (state.get("refined_statement") or "").strip()
            assumptions = state.get("strategic_assumptions") or []

            if draft_stmt or refined_stmt:
                st.session_state.final_strategy = {
                    "draft": draft_stmt,
                    "refined": refined_stmt,
                    "assumptions": assumptions[:5],
                }

        st.session_state.last_error = ""
        st.rerun()

    except Exception as e:
        st.session_state.last_error = str(e)
        st.session_state.chat.append({"role": "assistant", "content": f"Error calling the model: {str(e)}"})
        st.rerun()
