import requests
import streamlit as st
import os

BACKEND_BASE_URL = (
    os.getenv("BACKEND_BASE_URL")
    or st.secrets.get("BACKEND_BASE_URL", "http://localhost:8000")
)
BACKEND_QUERY_URL = f"{BACKEND_BASE_URL}/query"
BACKEND_UPLOAD_URL = f"{BACKEND_BASE_URL}/upload-report"

st.set_page_config(page_title="Strata Knowledge Agent", page_icon="🏗️")

st.title("🏗️ Strata Knowledge Agent")
st.write(
    "Ask technical questions like a project manager would. "
    "The agent responds using internal building science knowledge and, "
    "optionally, a specific uploaded report.\n\n"
    "⚠️ This does *not* replace formal engineering review."
)

if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role, content}]

if "current_report_id" not in st.session_state:
    st.session_state.current_report_id = None

if "current_report_name" not in st.session_state:
    st.session_state.current_report_name = None

# Sidebar: upload a specific report
st.sidebar.header("Report context (optional)")
uploaded = st.sidebar.file_uploader("Upload a PDF report", type=["pdf"])

if uploaded is not None and st.sidebar.button("Ingest report"):
    with st.sidebar:
        st.write("Uploading and processing report...")
    try:
        files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
        resp = requests.post(BACKEND_UPLOAD_URL, files=files, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        st.session_state.current_report_id = data["report_id"]
        st.session_state.current_report_name = data["filename"]
        st.sidebar.success(f"Report ingested: {data['filename']}")
    except Exception as e:
        st.sidebar.error(f"Error uploading report: {e}")

# Show current report info
if st.session_state.current_report_id:
    st.info(
        f"Questions are currently scoped to report: "
        f"**{st.session_state.current_report_name}** "
        f"(report_id={st.session_state.current_report_id})"
    )
else:
    st.warning(
        "No specific report selected. The agent will answer using only generic "
        "building science knowledge. Upload a PDF in the sidebar to ask report-specific questions."
    )

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input(
    "Ask a question about balconies, parkades, rainscreens, or a specific report..."
)

if user_input:
    # Add user message locally
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # History for backend (no system messages)
    history_for_backend = [
        m for m in st.session_state.messages[:-1]
        if m["role"] in ("user", "assistant")
    ]

    with st.chat_message("assistant"):
        with st.spinner("Thinking like a senior building scientist..."):
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

            st.markdown(answer)

            if sources:
                with st.expander("Sources used"):
                    for s in sources:
                        st.markdown(f"- {s}")

    # Save assistant answer
    st.session_state.messages.append({"role": "assistant", "content": answer})
