import requests
import streamlit as st
import os

try:
    _secret_url = st.secrets.get("BACKEND_BASE_URL", "http://localhost:8000")
except Exception:
    _secret_url = "http://localhost:8000"

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL") or _secret_url
BACKEND_QUERY_URL = f"{BACKEND_BASE_URL}/query"
BACKEND_UPLOAD_URL = f"{BACKEND_BASE_URL}/upload-report"
BACKEND_ANALYZE_URL = f"{BACKEND_BASE_URL}/analyze-report"

st.set_page_config(
    page_title="Strata Engineering - Knowledge Assistant",
    page_icon="https://strataengineering.com/favicon.ico",
    layout="wide",
)

# --- Session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_report_id" not in st.session_state:
    st.session_state.current_report_id = None
if "current_report_name" not in st.session_state:
    st.session_state.current_report_name = None
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# ================================================================
# SIDEBAR
# ================================================================
with st.sidebar:
    st.markdown("## Strata Engineering")
    st.caption("Building Science & Engineering Advisory")
    st.markdown("---")

    st.markdown("### Report Context")
    st.caption("Upload a PDF to ask questions about a specific report.")
    uploaded = st.file_uploader("Select PDF", type=["pdf"], label_visibility="collapsed")

    if uploaded is not None and st.button("Ingest Report", type="primary", use_container_width=True):
        with st.spinner("Processing..."):
            try:
                files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
                resp = requests.post(BACKEND_UPLOAD_URL, files=files, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                st.session_state.current_report_id = data["report_id"]
                st.session_state.current_report_name = data["filename"]
                st.session_state.analysis_result = None
                st.success(f"Ingested: {data['filename']}")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.session_state.current_report_id:
        st.markdown(f"**Active:** `{st.session_state.current_report_name}`")
        if st.button("Clear Report", use_container_width=True):
            st.session_state.current_report_id = None
            st.session_state.current_report_name = None
            st.session_state.analysis_result = None
            st.rerun()

    st.markdown("---")
    st.caption("This tool does not replace formal engineering review.")

# ================================================================
# HEADER
# ================================================================
st.markdown(
    "<h3 style='margin-bottom:0; color:#1a3a5c;'>Strata Engineering Knowledge Assistant</h3>"
    "<p style='color:#4a7fa5; margin-top:4px;'>Ask technical questions about building science, "
    "depreciation reports, warranties, and more.</p>",
    unsafe_allow_html=True,
)

# ================================================================
# TABS
# ================================================================
tab_chat, tab_analyze = st.tabs(["Ask a Question", "Analyze Report"])

# --- TAB 1: Chat history display only (input is always outside/below) ---
with tab_chat:
    if st.session_state.current_report_id:
        st.info(
            f"Questions scoped to: **{st.session_state.current_report_name}** — "
            "the agent will prioritize content from this report."
        )
    else:
        st.warning(
            "No report selected. Using general building science knowledge. "
            "Upload a PDF in the sidebar for report-specific questions."
        )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- TAB 2: Analyze Report ---
with tab_analyze:
    if not st.session_state.current_report_id:
        st.info("Upload and ingest a PDF report in the sidebar to run a structured analysis.")
    else:
        st.markdown(f"**Report:** {st.session_state.current_report_name}")

        if st.button("Run Analysis", type="primary"):
            with st.spinner("Analyzing report..."):
                try:
                    resp = requests.post(
                        f"{BACKEND_ANALYZE_URL}/{st.session_state.current_report_id}",
                        timeout=120,
                    )
                    resp.raise_for_status()
                    st.session_state.analysis_result = resp.json()
                except Exception as e:
                    st.error(f"Analysis error: {e}")

        result = st.session_state.analysis_result
        if result:
            st.markdown("### Executive Summary")
            st.markdown(result.get("executive_summary", ""))

            if result.get("building_overview"):
                with st.expander("Building Overview"):
                    st.markdown(result["building_overview"])

            priorities = result.get("top_priorities", [])
            if priorities:
                st.markdown("### Top Priorities")
                urgency_color = {
                    "Immediate": "🔴",
                    "Short-Term": "🟠",
                    "Medium-Term": "🟡",
                    "Long-Term": "🟢",
                }
                for item in priorities:
                    urgency = item.get("urgency", "")
                    icon = urgency_color.get(urgency, "⚪")
                    with st.expander(
                        f"{icon} #{item.get('rank')} — {item.get('component')} ({urgency})"
                    ):
                        c1, c2 = st.columns(2)
                        c1.metric("Condition", item.get("condition", ""))
                        c2.metric("Estimated Cost", item.get("estimated_cost_range", ""))
                        st.markdown(f"**Action:** {item.get('recommended_action', '')}")

            eol_items = result.get("components_near_eol", [])
            if eol_items:
                st.markdown("### Components Near End of Life")
                for item in eol_items:
                    st.markdown(
                        f"- **{item.get('component')}** — {item.get('estimated_remaining_life')}  \n"
                        f"  {item.get('notes', '')}"
                    )

            if result.get("funding_notes"):
                st.markdown("### Funding Notes")
                st.markdown(result["funding_notes"])

            escalations = result.get("escalation_items", [])
            if escalations:
                st.markdown("### Items Requiring Engineer Sign-Off")
                for item in escalations:
                    st.markdown(f"- {item}")

# ================================================================
# CHAT INPUT — outside tabs, always pinned to bottom
# ================================================================
user_input = st.chat_input(
    "Ask about balconies, parkades, rainscreens, depreciation reports, 2-5-10 warranty..."
)

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    history_for_backend = [
        m for m in st.session_state.messages[:-1]
        if m["role"] in ("user", "assistant")
    ]

    try:
        payload = {
            "question": user_input,
            "history": history_for_backend,
            "report_id": st.session_state.current_report_id,
        }
        resp = requests.post(BACKEND_QUERY_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        answer = data["answer"]
        sources = data.get("sources", [])
    except Exception as e:
        answer = f"Error contacting backend: {e}"
        sources = []

    msg_content = answer
    if sources:
        sources_md = "\n".join(f"- {s}" for s in sources)
        msg_content += f"\n\n<details><summary>Sources</summary>\n\n{sources_md}\n\n</details>"

    st.session_state.messages.append({"role": "assistant", "content": msg_content})
    st.rerun()
