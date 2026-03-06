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
BACKEND_IMPROVE_URL = f"{BACKEND_BASE_URL}/improve-report"
BACKEND_LOGIN_URL = f"{BACKEND_BASE_URL}/auth/login"
BACKEND_ADMIN_URL = f"{BACKEND_BASE_URL}/admin"

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

/* ── Hide sidebar collapse/expand buttons ── */
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] { display: none !important; }

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

/* ── File uploader in sidebar: white card, blue text & button ── */
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background-color: #ffffff;
    border-radius: 8px;
    padding: 4px;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] * {
    color: #2d6a9f !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    border-color: #2d6a9f !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
    background-color: #2d6a9f !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] button:hover {
    background-color: #1a3a5c !important;
}
</style>
""", unsafe_allow_html=True)

# --- Session state ---
if "token" not in st.session_state:
    st.session_state.token = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_report_id" not in st.session_state:
    st.session_state.current_report_id = None
if "current_report_name" not in st.session_state:
    st.session_state.current_report_name = None
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "improvement_result" not in st.session_state:
    st.session_state.improvement_result = None


def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


# ================================================================
# LOGIN PAGE
# ================================================================
if not st.session_state.token:
    st.markdown("""
    <style>
    #MainMenu, footer, header { visibility: hidden; }
    .stApp { background-color: #f0f6fc; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1a3a5c 0%,#2d6a9f 100%);
                    border-radius:12px;padding:32px 36px;margin-top:80px;text-align:center;">
            <h2 style="color:#ffffff;margin:0 0 4px 0;">Strata Engineering</h2>
            <p style="color:#b8d4ea;margin:0;font-size:0.9rem;">Knowledge Assistant</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            try:
                resp = requests.post(BACKEND_LOGIN_URL, json={"username": username, "password": password}, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.token = data["token"]
                    st.session_state.current_user = data["user"]
                    st.rerun()
                else:
                    st.error(resp.json().get("detail", "Login failed"))
            except Exception as e:
                st.error(f"Could not reach server: {e}")
    st.stop()

# ================================================================
# SIDEBAR
# ================================================================
with st.sidebar:
    st.markdown("## Strata Engineering")
    st.caption("Building Science & Engineering Advisory")
    st.markdown("---")

    cu = st.session_state.current_user or {}
    st.caption(f"Signed in as **{cu.get('username','')}**")
    company = cu.get("company_name")
    if company:
        st.caption(f"Company: {company}")
    role = cu.get("role", "user")
    if role == "superadmin":
        st.caption("Role: Super Admin")
    elif role == "admin":
        st.caption("Role: Company Admin")
    if st.button("Sign Out", use_container_width=True):
        for key in ["token", "current_user", "messages", "current_report_id",
                    "current_report_name", "analysis_result", "improvement_result"]:
            st.session_state[key] = None if key in ("token", "current_user", "current_report_id",
                                                      "current_report_name", "analysis_result",
                                                      "improvement_result") else []
        st.rerun()
    st.markdown("---")

    st.markdown("### Report Context")
    st.caption("Upload a PDF to ask questions about a specific report.")
    uploaded = st.file_uploader("Select PDF", type=["pdf"], label_visibility="collapsed")

    if uploaded is not None and st.button("Ingest Report", type="primary", use_container_width=True):
        with st.spinner("Processing..."):
            try:
                files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
                resp = requests.post(BACKEND_UPLOAD_URL, files=files, headers=auth_headers(), timeout=120)
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
            st.session_state.improvement_result = None
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
_tabs = ["Ask a Question", "Analyze Report", "Improve Report"]
if role in ("superadmin", "admin"):
    _tabs.append("Admin")
_tab_objects = st.tabs(_tabs)
tab_chat = _tab_objects[0]
tab_analyze = _tab_objects[1]
tab_improve = _tab_objects[2]
tab_admin = _tab_objects[3] if len(_tab_objects) > 3 else None

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
                        headers=auth_headers(), timeout=120,
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

# --- TAB 3: Improve Report ---
with tab_improve:
    if not st.session_state.current_report_id:
        st.info("Upload and ingest a PDF report in the sidebar to get improvement tips.")
    else:
        st.markdown(f"**Report:** {st.session_state.current_report_name}")
        st.caption("Peer-review style feedback for engineers and technicians before making the report official.")

        if st.button("Get Improvement Tips", type="primary", use_container_width=True):
            with st.spinner("Reviewing report for improvements..."):
                try:
                    resp = requests.post(
                        f"{BACKEND_IMPROVE_URL}/{st.session_state.current_report_id}",
                        headers=auth_headers(), timeout=120,
                    )
                    resp.raise_for_status()
                    st.session_state.improvement_result = resp.json()
                except Exception as e:
                    st.error(f"Error getting improvement tips: {e}")

        imp = st.session_state.improvement_result
        if imp:
            score = imp.get("overall_score", "")
            st.markdown(f"### Overall Score: **{score}**")
            st.markdown(imp.get("summary", ""))

            strengths = imp.get("strengths", [])
            if strengths:
                with st.expander("✅ Strengths", expanded=False):
                    for s in strengths:
                        st.markdown(f"- {s}")

            missing = imp.get("missing_sections", [])
            if missing:
                with st.expander("⚠️ Missing Sections", expanded=True):
                    for m in missing:
                        st.markdown(f"- {m}")

            tips = imp.get("tips", [])
            if tips:
                st.markdown("### Improvement Tips")
                severity_icon = {"Critical": "🔴", "Recommended": "🟠", "Minor": "🟡"}
                for tip in tips:
                    icon = severity_icon.get(tip.get("severity", ""), "⚪")
                    with st.expander(
                        f"{icon} [{tip.get('severity')}] {tip.get('category')} — {tip.get('issue', '')[:80]}"
                    ):
                        st.markdown(f"**Issue:** {tip.get('issue', '')}")
                        st.markdown(f"**Suggestion:** {tip.get('suggestion', '')}")

# --- TAB 4: Admin (superadmin + company admin) ---
if tab_admin:
    with tab_admin:
        st.markdown(f"### Admin Panel")

        if role == "superadmin":
            admin_section = st.radio("Section", ["Companies", "Users"], horizontal=True)
        else:
            admin_section = "Users"

        # ── Companies (superadmin only) ──────────────────────────
        if admin_section == "Companies":
            st.markdown("#### Create Company")
            with st.form("create_company"):
                c1, c2 = st.columns(2)
                co_name = c1.text_input("Company Name")
                co_slug = c2.text_input("Slug (unique ID, e.g. strata-eng)")
                co_status = c1.selectbox("Status", ["trial", "active", "inactive"])
                trial_days = c2.number_input("Trial Days", min_value=1, max_value=365, value=14)
                if st.form_submit_button("Create Company", type="primary"):
                    try:
                        resp = requests.post(
                            f"{BACKEND_ADMIN_URL}/companies",
                            json={"name": co_name, "slug": co_slug, "status": co_status, "trial_days": int(trial_days)},
                            headers=auth_headers(), timeout=15,
                        )
                        resp.raise_for_status()
                        st.success(f"Company '{co_name}' created.")
                    except Exception as e:
                        st.error(f"Error: {e}")

            st.markdown("#### All Companies")
            try:
                resp = requests.get(f"{BACKEND_ADMIN_URL}/companies", headers=auth_headers(), timeout=15)
                resp.raise_for_status()
                companies = resp.json()
                for co in companies:
                    status_badge = {"trial": "🟡", "active": "🟢", "inactive": "🔴"}.get(co["status"], "⚪")
                    with st.expander(f"{status_badge} {co['name']} ({co['slug']}) — {co['status'].upper()}"):
                        st.caption(f"ID: {co['id']}")
                        if co.get("trial_ends_at"):
                            st.caption(f"Trial ends: {co['trial_ends_at'][:10]}")
                        new_status = st.selectbox(
                            "Change status", ["trial", "active", "inactive"],
                            index=["trial", "active", "inactive"].index(co["status"]),
                            key=f"co_status_{co['id']}",
                        )
                        if st.button("Update Status", key=f"co_btn_{co['id']}"):
                            try:
                                r = requests.patch(
                                    f"{BACKEND_ADMIN_URL}/companies/{co['id']}/status",
                                    params={"status": new_status},
                                    headers=auth_headers(), timeout=15,
                                )
                                r.raise_for_status()
                                st.success("Status updated.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
            except Exception as e:
                st.error(f"Could not load companies: {e}")

        # ── Users ───────────────────────────────────────────────
        if admin_section == "Users":
            st.markdown("#### Create User")
            with st.form("create_user"):
                c1, c2 = st.columns(2)
                u_username = c1.text_input("Username")
                u_email = c2.text_input("Email")
                u_password = c1.text_input("Password", type="password")
                u_role = c2.selectbox("Role", ["user", "admin"] if role == "superadmin" else ["user"])

                u_company_id = None
                if role == "superadmin":
                    try:
                        resp = requests.get(f"{BACKEND_ADMIN_URL}/companies", headers=auth_headers(), timeout=15)
                        companies_list = resp.json() if resp.ok else []
                    except Exception:
                        companies_list = []
                    company_options = {co["name"]: co["id"] for co in companies_list}
                    if company_options:
                        selected_co = st.selectbox("Company", list(company_options.keys()))
                        u_company_id = company_options[selected_co]
                    else:
                        st.warning("No companies yet — create one first.")

                if st.form_submit_button("Create User", type="primary"):
                    try:
                        payload = {"username": u_username, "email": u_email, "password": u_password, "role": u_role}
                        if u_company_id:
                            payload["company_id"] = u_company_id
                        resp = requests.post(
                            f"{BACKEND_ADMIN_URL}/users",
                            json=payload, headers=auth_headers(), timeout=15,
                        )
                        resp.raise_for_status()
                        st.success(f"User '{u_username}' created.")
                    except Exception as e:
                        st.error(f"Error: {e}")

            st.markdown("#### All Users")
            try:
                resp = requests.get(f"{BACKEND_ADMIN_URL}/users", headers=auth_headers(), timeout=15)
                resp.raise_for_status()
                users_list = resp.json()
                for u in users_list:
                    active_icon = "🟢" if u["is_active"] else "🔴"
                    role_badge = {"superadmin": "SA", "admin": "Admin", "user": "User"}.get(u["role"], u["role"])
                    with st.expander(f"{active_icon} {u['username']} [{role_badge}] — {u.get('company_name') or 'No company'}"):
                        st.caption(f"Email: {u['email']} | ID: {u['id']}")
                        btn_label = "Deactivate" if u["is_active"] else "Activate"
                        if st.button(btn_label, key=f"user_toggle_{u['id']}"):
                            try:
                                r = requests.patch(
                                    f"{BACKEND_ADMIN_URL}/users/{u['id']}/toggle",
                                    headers=auth_headers(), timeout=15,
                                )
                                r.raise_for_status()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
            except Exception as e:
                st.error(f"Could not load users: {e}")

# ================================================================
# CHAT INPUT — outside tabs, always pinned to bottom
# ================================================================
user_input = st.chat_input(
    "Ask about balconies, parkades, rainscreens, depreciation reports, 2-5-10 warranty..."
)

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    history_for_backend = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
        if m["role"] in ("user", "assistant")
    ]

    try:
        payload = {
            "question": user_input,
            "history": history_for_backend,
            "report_id": st.session_state.current_report_id,
        }
        resp = requests.post(BACKEND_QUERY_URL, json=payload, headers=auth_headers(), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        answer = data["answer"]
        sources = data.get("sources", [])
    except Exception as e:
        answer = f"Error contacting backend: {e}"
        sources = []

    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
    st.rerun()
