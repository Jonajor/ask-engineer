import requests
import streamlit as st
import os
from pdf_export import generate_pdf

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

st.markdown("""
<style>
/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Page: white background, navy text ── */
.stApp { background-color: #ffffff; }
.stApp, .main, .main * {
    color: #1a3a5c;
}

/* ── Sidebar: navy background, white text ── */
[data-testid="stSidebar"] {
    background-color: #1a3a5c !important;
}
[data-testid="stSidebar"], [data-testid="stSidebar"] * {
    color: #ffffff !important;
}
[data-testid="stSidebar"] hr {
    border-color: #2d5480 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background-color: #2d6a9f !important;
    color: #ffffff !important;
    border: none;
    border-radius: 6px;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #4a7fa5 !important;
}
[data-testid="stSidebar"] .stDownloadButton > button {
    background-color: #1e5c3a !important;
    color: #ffffff !important;
    border: none;
    border-radius: 6px;
}

/* ── Header: blue gradient, white text ── */
.se-header {
    background: linear-gradient(135deg, #1a3a5c 0%, #2d6a9f 100%);
    border-radius: 10px;
    padding: 20px 28px;
    margin-bottom: 20px;
}
.se-header h1 { margin: 0 0 4px 0; font-size: 1.5rem; font-weight: 700; color: #ffffff !important; }
.se-header p  { margin: 0; font-size: 0.88rem; color: #b8d4ea !important; }

/* ── Tabs: inactive = white bg + blue text, active = navy bg + white text ── */
.stTabs [data-baseweb="tab-list"] {
    background-color: #f0f6fc;
    border-radius: 8px 8px 0 0;
    gap: 4px;
    border-bottom: 2px solid #d0e4f0;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px 6px 0 0;
    padding: 8px 20px;
    font-weight: 500;
    background-color: #ffffff;
    color: #1a3a5c !important;
}
.stTabs [aria-selected="true"] {
    background-color: #1a3a5c !important;
    color: #ffffff !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background-color: #ffffff;
    border-radius: 0 0 10px 10px;
    padding: 20px;
    border: 1px solid #d0e4f0;
    border-top: none;
}
.stTabs [data-baseweb="tab-panel"] * { color: #1a3a5c; }

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    border-radius: 10px;
    margin-bottom: 8px;
    background-color: #f5f9ff;
}
[data-testid="stChatMessage"] * { color: #1a3a5c !important; }

/* ── Alerts ── */
.stAlert { border-radius: 8px; border-left-width: 4px; }
[data-testid="stAlert"] * { color: #1a3a5c !important; }

/* ── Expanders ── */
.streamlit-expanderHeader {
    background-color: #f0f6fc !important;
    border-radius: 6px !important;
    color: #1a3a5c !important;
}
</style>
""", unsafe_allow_html=True)

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
    if st.session_state.messages:
        pdf_bytes = generate_pdf(
            st.session_state.messages,
            report_name=st.session_state.current_report_name,
        )
        st.download_button(
            label="Export Q&A to PDF",
            data=pdf_bytes,
            file_name="strata-engineering-session.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    st.markdown("---")
    st.caption("This tool does not replace formal engineering review.")

# ================================================================
# HEADER
# ================================================================
st.markdown("""
<div class="se-header">
    <h1>Strata Engineering &mdash; Knowledge Assistant</h1>
    <p>Ask technical questions about building science, depreciation reports, warranties, and more.
    Upload a PDF report in the sidebar for report-specific analysis.</p>
</div>
""", unsafe_allow_html=True)

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
            if msg.get("sources"):
                with st.expander("Sources"):
                    for s in msg["sources"]:
                        st.markdown(f"- {s}")

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

    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
    st.rerun()
