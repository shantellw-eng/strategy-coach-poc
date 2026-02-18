import os
import re
import json
from typing import Optional, Tuple, List

import streamlit as st
import anthropic

# ------------------------------------------------------------
# Strategy Statement Coach (POC) - Streamlit Front-End (Claude)
#
# What you need to do:
# 1) Put your full system prompt (plain text) in system_prompt.txt (same folder as this file)
# 2) Set ANTHROPIC_API_KEY in your environment OR Streamlit secrets
# 3) Optionally set ANTHROPIC_MODEL (defaults to "claude-sonnet-4-5-20250929")
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

# Initial-only examples (autohide after first user message)
INITIAL_EXAMPLES = [
    "Objective: Double revenue within 12 months.",
    "Objective: Reach $5m ARR within 18 months while maintaining gross margin above 60%.",
    "Objective: Increase retention from 85% to 92% within 12 months.",
]

COMMITMENT_QUESTION = "Are you prepared to back this with resources and focus?"


# -----------------------------
# Safe prefill (prevents Streamlit widget mutation error)
# -----------------------------
def request_prefill(text: str):
    st.session_state.prefill_text = text
    st.session_state.prefill_pending = True


def apply_pending_prefill():
    if st.session_state.get("prefill_pending"):
        st.session_state["composer_text"] = st.session_state.get("prefill_text", "")
        st.session_state.prefill_pending = False


def load_system_prompt() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "system_prompt.txt")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"system_prompt.txt not found next to coach_bot_ui.py. Expected at: {path}"
        )
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def split_user_text_and_state(full_text: str) -> Tuple[str, Optional[dict]]:
    """
    Returns (user_facing_text, state_dict_or_none).
    If state block is missing or invalid, returns (full_text, None).
    """
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
        "draft_statement": as_str(state.get("draft_statement", "")).strip(),
        "refined_statement": as_str(state.get("refined_statement", "")).strip(),
        "current_phase": as_str(state.get("current_phase", "")).strip(),
        "next_question": as_str(state.get("next_question", "")).strip(),
    }
    if out["current_phase"] not in PHASES:
        out["current_phase"] = "objective"
    return out


def is_affirmation(text: str) -> bool:
    """
    Lightweight check for user commitment confirmation.
    We keep it simple and conservative.
    """
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


def call_model(conversation_messages: List[dict], session_mode: str) -> str:
    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set (Streamlit secrets or environment variable).")

    model_name = (
        st.secrets.get("ANTHROPIC_MODEL")
        or os.environ.get("ANTHROPIC_MODEL")
        or "claude-sonnet-4-5-20250929"
    )

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = ""
    if conversation_messages and conversation_messages[0]["role"] == "system":
        system_prompt = conversation_messages[0]["content"]

    if session_mode == "Board":
        mode_hint = (
            "\n\nSession mode: Board.\n"
            "- Be sharper and more direct.\n"
            "- Surface arithmetic gaps quickly.\n"
            "- Apply friction when targets lack enabling mechanics.\n"
            "- Keep examples rare and incisive.\n"
        )
    else:
        mode_hint = (
            "\n\nSession mode: Workshop.\n"
            "- Keep it clear and structured.\n"
            "- Encourage clarity without overwhelming.\n"
            "- Use examples only when they materially help.\n"
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
    def tick(val: str) -> str:
        return "✓" if (val or "").strip() else " "

    phase = current_phase if current_phase in PHASES else "objective"

    cols = st.columns(5)
    for i, p in enumerate(PHASES):
        label = PHASE_LABELS[p]
        is_current = (p == phase)

        if p == "objective":
            prefix = tick(objective)
        elif p == "scope":
            prefix = tick(scope)
        elif p == "advantage":
            prefix = tick(advantage)
        else:
            prefix = " "

        text = f"{prefix} {label}"
        cols[i].markdown(f"**{text}**" if is_current else text)


# -----------------------------
# Simple password gate (POC)
# -----------------------------
def require_password():
    app_password = st.secrets.get("APP_PASSWORD", "")
    if not app_password:
        st.error("APP_PASSWORD is not set in Streamlit secrets.")
        st.stop()

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("Strategy Statement Coach (POC)")
        st.write("Enter the access code to continue.")
        pw = st.text_input("Access code", type="password")

        if pw and pw == app_password:
            st.session_state.authenticated = True
            st.rerun()

        st.stop()

require_password()


# -----------------------------
# Streamlit App
# -----------------------------

st.set_page_config(page_title="Strategy Statement Coach (POC)", layout="centered")
st.title("Strategy Statement Coach (POC)")


# Init session state
if "strategy_state" not in st.session_state:
    st.session_state.strategy_state = {
        "objective": "",
        "scope": "",
        "advantage": "",
        "strategic_assumptions": [],
        "draft_statement": "",
        "refined_statement": "",
        "current_phase": "objective",
        "next_question": "",
    }

if "chat" not in st.session_state:
    system_prompt = load_system_prompt()
    st.session_state.chat = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": "Let’s work toward a clear Strategy statement using objective, scope and advantage.\n\nFirst, let’s get clear on the outcome.\nWhat measurable result are you aiming for, and by when?"},

    ]

if "composer_text" not in st.session_state:
    st.session_state.composer_text = ""

if "prefill_pending" not in st.session_state:
    st.session_state.prefill_pending = False
    st.session_state.prefill_text = ""

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


# Sidebar = Working Board
with st.sidebar:
    st.subheader("Session")

    session_mode = st.radio(
        "Mode",
        options=["Workshop", "Board"],
        index=0,
        help="Workshop keeps it tight and practical. Board is sharper and more direct.",
        disabled=st.session_state.is_locked,
    )

    st.divider()

    ss = st.session_state.strategy_state
    phase = ss.get("current_phase", "objective") or "objective"

    st.subheader("Current Focus")
    st.markdown(f"**{PHASE_LABELS.get(phase, 'Objective')}**")

    st.divider()

    st.subheader("Working Strategy")
    obj = ss.get("objective") or "—"
    scp = ss.get("scope") or "—"
    adv = ss.get("advantage") or "—"

    st.markdown("**Objective**")
    st.markdown(obj)

    st.markdown("**Scope**")
    st.markdown(scp)

    st.markdown("**Advantage**")
    st.markdown(adv)

    assumptions = ss.get("strategic_assumptions", []) or []
    if assumptions and phase in ["draft", "refine"]:
        st.markdown("**Strategic Assumptions**")
        for a in assumptions[:5]:
            st.markdown(f"- {a}")

    if st.session_state.final_strategy:
        st.divider()
        st.subheader("Final Strategy (Locked)" if st.session_state.is_locked else "Final Strategy")
        fs = st.session_state.final_strategy

        if fs.get("draft"):
            st.markdown("**Draft**")
            st.markdown(fs["draft"])
        if fs.get("refined"):
            st.markdown("**Refined**")
            st.markdown(fs["refined"])
        if fs.get("assumptions"):
            st.markdown("**Assumptions**")
            for a in fs["assumptions"][:5]:
                st.markdown(f"- {a}")

    st.divider()

    st.subheader("Quick Actions")
    st.caption("Pre-fills your next message. Use when you want to revise a component.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Revise objective", disabled=st.session_state.is_locked):
            request_prefill("Revise objective: ")
            st.rerun()
        if st.button("Revise scope", disabled=st.session_state.is_locked):
            request_prefill("Revise scope: ")
            st.rerun()
    with col2:
        if st.button("Revise advantage", disabled=st.session_state.is_locked):
            request_prefill("Revise advantage: ")
            st.rerun()
        if st.button("Clear input", disabled=st.session_state.is_locked):
            request_prefill("")
            st.rerun()

    st.divider()

    st.subheader("Controls")
    if st.button("Reset session"):
        for k in [
            "chat",
            "strategy_state",
            "composer_text",
            "prefill_pending",
            "prefill_text",
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


# Main column: tracker
ss = st.session_state.strategy_state
render_phase_tracker(
    current_phase=ss.get("current_phase", "objective"),
    objective=ss.get("objective", ""),
    scope=ss.get("scope", ""),
    advantage=ss.get("advantage", ""),
)

st.write("")

# Chat history
for m in st.session_state.chat:
    if m["role"] == "system":
        continue
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Examples (autohide after first user message)
if not st.session_state.has_started and not st.session_state.is_locked:
    st.subheader("Examples")
    ex_cols = st.columns(3)
    for i in range(3):
        with ex_cols[i]:
            if st.button(f"Use example {i+1}", key=f"initial_ex_{i}"):
                request_prefill(INITIAL_EXAMPLES[i])
                st.rerun()
            st.caption(INITIAL_EXAMPLES[i])

# Apply pending prefill BEFORE the widget is created
apply_pending_prefill()

# Composer + send
with st.form("composer_form", clear_on_submit=False):
    composer = st.text_area(
        "Message",
        key="composer_text",
        placeholder="Type your message…",
        height=120,
        disabled=st.session_state.is_locked,
    )
    send = st.form_submit_button("Send", disabled=st.session_state.is_locked)

if st.session_state.is_locked:
    st.info("This session is locked. Reset session to start a new one.")

# Send behaviour
if send and composer.strip() and not st.session_state.is_locked:
    user_text = composer.strip()

    # Lock if commitment asked and user affirms
    if st.session_state.assistant_asked_commitment and is_affirmation(user_text):
        st.session_state.is_locked = True
        st.session_state.chat.append({"role": "user", "content": user_text})
        st.session_state.chat.append({"role": "assistant", "content": "Good. Then the real work is consistency."})
        st.session_state.assistant_asked_commitment = False
        request_prefill("")
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

            draft_stmt = st.session_state.strategy_state.get("draft_statement", "").strip()
            refined_stmt = st.session_state.strategy_state.get("refined_statement", "").strip()
            assumptions = st.session_state.strategy_state.get("strategic_assumptions", [])

            if draft_stmt and refined_stmt:
                st.session_state.final_strategy = {
                    "draft": draft_stmt,
                    "refined": refined_stmt,
                    "assumptions": assumptions[:5],
                }

        st.session_state.last_error = ""
        request_prefill("")
        st.rerun()

    except Exception as e:
        st.session_state.last_error = str(e)
        st.session_state.chat.append({"role": "assistant", "content": f"Error calling the model: {str(e)}"})
        st.rerun()
