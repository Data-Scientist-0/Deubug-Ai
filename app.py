import streamlit as st
import base64, os, requests, threading, time

API_URL = os.getenv("API_URL", "http://localhost:8000")

from agent import analyze_code, chat_response
from parser import parse_response


from agent import analyze_code, chat_response
from parser import parse_response

st.set_page_config(
    page_title="DebugAI — AI/ML Debugging Agent",
    page_icon="🤖", layout="wide",
    initial_sidebar_state="expanded",
)
# ── Keep Railway alive ────────────────────────────────────────────────────────
def keep_alive():
    while True:
        try:
            requests.get(f"{API_URL}/health", timeout=10)
        except Exception:
            pass
        time.sleep(300)

if "keep_alive_started" not in st.session_state:
    st.session_state.keep_alive_started = True
    t = threading.Thread(target=keep_alive, daemon=True)
    t.start()


def set_background(path):
    if not os.path.exists(path):
        return
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(f"""<style>
    .stApp{{background-image:url("data:image/png;base64,{b64}");background-size:cover;background-position:center;background-attachment:fixed;}}
    .stApp>header{{background-color:transparent!important;}}
    [data-testid="stSidebar"]{{background-color:rgba(8,12,28,0.93)!important;}}
    [data-testid="stSidebar"] *{{color:#d0e8ff!important;}}
    .stTabs [data-baseweb="tab-panel"]{{background-color:rgba(8,12,28,0.82);border-radius:12px;padding:1.2rem;margin-top:0.5rem;}}
    .stTabs [data-baseweb="tab-list"]{{background-color:rgba(8,12,28,0.75);border-radius:10px;padding:4px;}}
    .stTabs [data-baseweb="tab"]{{color:#a0c4ff!important;font-weight:500;}}
    .stTabs [aria-selected="true"]{{background-color:rgba(127,119,221,0.35)!important;color:#fff!important;border-radius:8px;}}
    .stTextArea textarea,.stTextInput input{{background-color:rgba(8,12,28,0.88)!important;color:#e8f4ff!important;border:1px solid rgba(127,119,221,0.5)!important;border-radius:8px!important;font-family:monospace!important;}}
    .stButton>button{{background-color:rgba(127,119,221,0.85)!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:600!important;}}
    .stButton>button:hover{{background-color:rgba(127,119,221,1)!important;}}
    .stSelectbox>div>div{{background-color:rgba(8,12,28,0.88)!important;color:#e0e0e0!important;border:1px solid rgba(127,119,221,0.4)!important;}}
    .stMultiSelect>div>div{{background-color:rgba(8,12,28,0.88)!important;color:#e0e0e0!important;}}
    h1,h2,h3,h4{{color:#a0c4ff!important;text-shadow:0 0 20px rgba(100,160,255,0.3);}}
    p,label,.stMarkdown{{color:#d0e8ff!important;}}
    .stMetric{{background-color:rgba(8,12,28,0.82)!important;border:1px solid rgba(127,119,221,0.35)!important;border-radius:10px!important;padding:0.8rem!important;}}
    .stMetric label{{color:#a0c4ff!important;}}
    .stMetric [data-testid="stMetricValue"]{{color:#fff!important;}}
    .stExpander{{background-color:rgba(8,12,28,0.82)!important;border:1px solid rgba(127,119,221,0.3)!important;border-radius:10px!important;}}
    .stAlert{{background-color:rgba(8,12,28,0.85)!important;border-radius:10px!important;}}
    [data-testid="stChatMessage"]{{background-color:rgba(8,12,28,0.82)!important;border-radius:12px!important;margin-bottom:0.5rem;}}
    </style>""", unsafe_allow_html=True)

set_background("bg.png")

st.markdown("""<style>
.severity-critical{background:rgba(255,80,80,0.15);color:#ff8080;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;border:1px solid rgba(255,80,80,0.4);}
.severity-high{background:rgba(255,140,80,0.15);color:#ffaa80;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;border:1px solid rgba(255,140,80,0.4);}
.severity-medium{background:rgba(255,200,80,0.15);color:#ffd080;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;border:1px solid rgba(255,200,80,0.4);}
.severity-low{background:rgba(80,160,255,0.15);color:#80c8ff;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;border:1px solid rgba(80,160,255,0.4);}
.stack-badge{background:rgba(127,119,221,0.25);color:#c0b8ff;padding:4px 14px;border-radius:16px;font-size:13px;font-weight:600;border:1px solid rgba(127,119,221,0.5);}
</style>""", unsafe_allow_html=True)

for k, v in [("token",None),("user_id",None),("username",None),
              ("messages",[]),("auth_page","login")]:
    if k not in st.session_state:
        st.session_state[k] = v

def api(method, path, json=None, auth=True):
    headers = {}
    if auth and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        r = getattr(requests, method)(f"{API_URL}{path}", json=json, headers=headers, timeout=60)
        return r.status_code, r.json() if r.content else {}
    except requests.exceptions.ConnectionError:
        return 0, {"detail": "Cannot connect to API server. Make sure FastAPI is running on port 8000."}
    except Exception as e:
        return 0, {"detail": str(e)}

def is_logged_in():
    return bool(st.session_state.token)

def do_logout():
    st.session_state.token = None
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.messages = []
    st.session_state.auth_page = "login"
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# AUTH PAGES
# ══════════════════════════════════════════════════════════════════════════════
def show_auth():
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;font-size:2.4rem;'>🤖 DebugAI</h1>"
                "<p style='text-align:center;color:#a0c4ff;margin-top:-0.5rem;'>AI/ML Code Debugging Agent</p>",
                unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        page = st.radio("Navigation", ["Login", "Register", "Verify Email"],
                        horizontal=True, label_visibility="collapsed",
                        index=["login","register","verify email"].index(st.session_state.auth_page))
        st.session_state.auth_page = page.lower()
        st.markdown("<br>", unsafe_allow_html=True)

        # ── LOGIN ──────────────────────────────────────────────────────────
        if st.session_state.auth_page == "login":
            username = st.text_input("Username", placeholder="Enter your username", key="l_user")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="l_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔑 Login", use_container_width=True):
                if not username or not password:
                    st.error("Please fill in all fields.")
                else:
                    code, data = api("post", "/auth/login",
                                     json={"username": username, "password": password}, auth=False)
                    if code == 200:
                        st.session_state.token    = data["access_token"]
                        st.session_state.user_id  = data["user_id"]
                        st.session_state.username = data["username"]
                        st.success(f"Welcome back, {data['username']}!")
                        st.rerun()
                    else:
                        st.error(data.get("detail", "Login failed."))

        # ── REGISTER ───────────────────────────────────────────────────────
        elif st.session_state.auth_page == "register":
            new_user  = st.text_input("Username", placeholder="Choose a username", key="r_user")
            new_email = st.text_input("Email", placeholder="your@gmail.com", key="r_email")
            new_pass  = st.text_input("Password", type="password",
                                      help="Min 8 chars, 1 uppercase, 1 number", key="r_pass")
            new_pass2 = st.text_input("Confirm Password", type="password", key="r_pass2")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📝 Create Account", use_container_width=True):
                if not all([new_user, new_email, new_pass, new_pass2]):
                    st.error("Please fill in all fields.")
                elif new_pass != new_pass2:
                    st.error("Passwords do not match.")
                else:
                    code, data = api("post", "/auth/register",
                                     json={"username": new_user, "email": new_email,
                                           "password": new_pass}, auth=False)
                    if code == 200:
                        st.success(data.get("message", "Account created!"))
                        st.info("Check your Gmail inbox for the 6-digit verification code.")
                        st.session_state.auth_page = "verify email"
                        st.session_state["pending_email"] = new_email
                        st.rerun()
                    else:
                        st.error(data.get("detail", "Registration failed."))

        # ── VERIFY OTP ─────────────────────────────────────────────────────
        elif st.session_state.auth_page == "verify email":
            default_email = st.session_state.get("pending_email", "")
            v_email = st.text_input("Email", value=default_email, key="v_email")
            v_otp   = st.text_input("6-Digit Verification Code",
                                    placeholder="Enter code from your Gmail", key="v_otp",
                                    max_chars=6)
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Verify Code", use_container_width=True):
                    if not v_email or not v_otp:
                        st.error("Enter your email and verification code.")
                    else:
                        code, data = api("post", "/auth/verify-otp",
                                         json={"email": v_email, "otp": v_otp}, auth=False)
                        if code == 200:
                            st.success(data.get("message", "Verified!"))
                            st.session_state.auth_page = "login"
                            st.rerun()
                        else:
                            st.error(data.get("detail", "Verification failed."))
            with c2:
                if st.button("🔄 Resend Code", use_container_width=True):
                    if v_email:
                        code, data = api("post", "/auth/resend-otp",
                                         json={"email": v_email}, auth=False)
                        if code == 200:
                            st.success("New code sent to your Gmail.")
                        else:
                            st.error(data.get("detail", "Could not resend."))
                    else:
                        st.error("Enter your email first.")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
def show_app():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.caption("Verified & Logged in")
        st.divider()
        st.header("⚙️ Settings")
        stack = st.selectbox("AI Stack",
            ["Auto-detect","PyTorch","TensorFlow / Keras","JAX / Flax",
             "HuggingFace Transformers","LangChain","LlamaIndex",
             "OpenAI SDK","Anthropic SDK","RAG Pipeline"])
        workflow = st.selectbox("Workflow Type",
            ["Auto-detect","Model Training","Fine-tuning (LoRA / QLoRA)","RLHF / DPO",
             "LLM API Integration","RAG Pipeline","Inference & Serving",
             "Data Preprocessing","Experiment Tracking"])
        show_traceback = st.toggle("Show Traceback Input", value=True)
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            do_logout()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Debug My Code", "💬 Chat with DebugAI",
        "💾 Saved Sessions", "👤 My Account",
    ])

    # ── TAB 1 — Debug ─────────────────────────────────────────────────────
    with tab1:
        col_l, col_r = st.columns([2, 1])
        with col_l:
            code_input = st.text_area("Paste your AI/ML code", height=300,
                placeholder="# Paste PyTorch / HuggingFace / LangChain code...")
            traceback_input = ""
            if show_traceback:
                traceback_input = st.text_area("Paste error traceback (optional)", height=130,
                    placeholder="Traceback (most recent call last):\n  File ...")
            uploaded = st.file_uploader("Or upload a .py file", type=["py"])
            if uploaded:
                code_input = uploaded.read().decode("utf-8")
                st.code(code_input, language="python")
            analyze_btn = st.button("🔍 Analyze Code", type="primary", use_container_width=True)
        with col_r:
            st.info("**Supported stacks**\n\n• PyTorch / TF / JAX\n• HuggingFace (PEFT · TRL)\n"
                    "• LangChain / LlamaIndex\n• OpenAI / Anthropic / Gemini\n"
                    "• FAISS / Chroma / Pinecone\n• W&B / MLflow\n• ONNX / TensorRT")
            st.markdown("**Bug categories**")
            for c in ["Tensor shape & device","Training & optimization","GPU / CUDA OOM",
                      "Fine-tuning (LoRA·QLoRA·DPO)","LLM API & prompt","RAG pipeline",
                      "Tokenization","Inference & serving","Experiment tracking"]:
                st.caption(f"• {c}")

        if analyze_btn:
            if not code_input.strip():
                st.warning("Paste some code first.")
            else:
                with st.spinner("DebugAI is analyzing your code..."):
                    raw = analyze_code(code=code_input, traceback=traceback_input,
                                       stack=stack, workflow=workflow)
                if raw.get("error"):
                    st.error(f"❌ {raw['error']}")
                else:
                    parsed = parse_response(raw["response"])
                    title  = f"{parsed['stack'][:40]} — {parsed['bug_count']} bug(s)"
                    s_code, _ = api("post", "/sessions", json={
                        "title": title, "stack": parsed["stack"],
                        "code": code_input, "result": raw["response"],
                        "bug_count": parsed["bug_count"],
                    })
                    if s_code in (200, 201):
                        st.success("✅ Session auto-saved to your account.")
                    st.markdown(f'<span class="stack-badge">🤖 Stack: {parsed["stack"]}</span>',
                                unsafe_allow_html=True)
                    st.write("")
                    sev = parsed["severity_counts"]
                    cols = st.columns(5)
                    cols[0].metric("Total", parsed["bug_count"])
                    cols[1].metric("🔴 Critical", sev.get("CRITICAL",0))
                    cols[2].metric("🟠 High",     sev.get("HIGH",0))
                    cols[3].metric("🟡 Medium",   sev.get("MEDIUM",0))
                    cols[4].metric("🔵 Low",      sev.get("LOW",0))
                    st.divider()
                    st.markdown(raw["response"])
                    if parsed["fixed_code"]:
                        st.divider()
                        st.download_button("⬇️ Download Fixed Code",
                            data=parsed["fixed_code"], file_name="fixed_code.py")
                    if parsed["bug_count"] == 0:
                        st.balloons()

    # ── TAB 2 — Chat ──────────────────────────────────────────────────────
    with tab2:
        st.subheader("Chat with DebugAI")
        if not st.session_state.messages:
            st.info("Ask: *Why does device mismatch happen?* · *How to fix CUDA OOM?* · *Explain LoRA rank*")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        if prompt := st.chat_input("Ask DebugAI anything about AI/ML debugging..."):
            st.session_state.messages.append({"role":"user","content":prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    reply = chat_response(st.session_state.messages)
                st.markdown(reply)
                st.session_state.messages.append({"role":"assistant","content":reply})

    # ── TAB 3 — Saved Sessions (CRUD) ─────────────────────────────────────
    with tab3:
        st.subheader("💾 Saved Sessions")
        s_code, stats = api("get", "/sessions/stats")
        if s_code == 200:
            c1,c2,c3 = st.columns(3)
            c1.metric("Total Sessions", stats.get("total_sessions",0))
            c2.metric("Total Bugs Found", stats.get("total_bugs",0))
            c3.metric("Last Session", (stats.get("last_session") or "—")[:16])
        st.divider()

        s_code, sessions = api("get", "/sessions")
        if s_code != 200:
            st.error(sessions.get("detail","Failed to load sessions."))
        elif not sessions:
            st.info("No saved sessions yet. Analyze some code and it auto-saves here.")
        else:
            _, col_del = st.columns([3,1])
            with col_del:
                if st.button("🗑️ Delete All", use_container_width=True):
                    api("delete", "/sessions/all")
                    st.success("All sessions deleted.")
                    st.rerun()

            for s in sessions:
                with st.expander(f"📄 {s['title']}  |  {s['bug_count']} bugs  |  {s['created_at'][:16]}"):
                    ca, cb = st.columns([3,1])
                    with ca:
                        st.caption(f"Stack: {s['stack']}")
                    with cb:
                        new_title = st.text_input("Rename", value=s["title"], key=f"rn_{s['id']}")
                        if st.button("✏️ Save", key=f"sv_{s['id']}", use_container_width=True):
                            rc, rd = api("put", f"/sessions/{s['id']}", json={"title": new_title})
                            st.success(rd.get("message","Renamed.")) if rc==200 else st.error(rd.get("detail","Failed."))
                            st.rerun()
                        if st.button("🗑️ Delete", key=f"dl_{s['id']}", use_container_width=True):
                            api("delete", f"/sessions/{s['id']}")
                            st.success("Deleted.")
                            st.rerun()

                    rc, full = api("get", f"/sessions/{s['id']}")
                    if rc == 200 and full.get("result"):
                        st.markdown("---")
                        st.markdown(full["result"])
                        if full.get("code"):
                            st.code(full["code"], language="python")

    # ── TAB 4 — Account ───────────────────────────────────────────────────
    with tab4:
        st.subheader("👤 My Account")
        rc, user = api("get", "/users/me")
        if rc == 200:
            c1,c2,c3 = st.columns(3)
            c1.metric("Username",     user.get("username",""))
            c2.metric("Email",        user.get("email",""))
            c3.metric("Member Since", user.get("created_at","")[:10])
        st.divider()

        with st.expander("✏️ Update Username"):
            new_uname = st.text_input("New username", key="nu_inp")
            if st.button("Update", key="btn_uname"):
                rc, rd = api("put", "/users/me", json={"username": new_uname})
                if rc == 200:
                    st.session_state.username = new_uname
                    st.success(rd.get("message","Updated."))
                    st.rerun()
                else:
                    st.error(rd.get("detail","Failed."))

        with st.expander("🔒 Change Password"):
            op = st.text_input("Current password", type="password", key="op_inp")
            np = st.text_input("New password",     type="password", key="np_inp",
                               help="Min 8 chars, 1 uppercase, 1 number")
            np2= st.text_input("Confirm new password", type="password", key="np2_inp")
            if st.button("Change Password", key="btn_pass"):
                if not all([op,np,np2]):
                    st.error("Fill in all fields.")
                elif np != np2:
                    st.error("New passwords do not match.")
                else:
                    rc, rd = api("put", "/users/me/password",
                                 json={"old_password":op,"new_password":np})
                    st.success(rd.get("message","Done.")) if rc==200 else st.error(rd.get("detail","Failed."))

        st.divider()
        st.markdown("**⚠️ Danger Zone**")
        with st.expander("🗑️ Delete My Account"):
            st.warning("Permanently deletes your account and all sessions. Cannot be undone.")
            confirm = st.text_input("Type DELETE to confirm", key="del_confirm")
            if st.button("Delete Account", key="btn_del_acc"):
                if confirm == "DELETE":
                    api("delete", "/users/me")
                    do_logout()
                else:
                    st.error("Type DELETE exactly.")

# ── Router ────────────────────────────────────────────────────────────────────
if is_logged_in():
    show_app()
else:
    show_auth()
