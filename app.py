import streamlit as st
import base64
import os
from agent import analyze_code, chat_response
from parser import parse_response

st.set_page_config(
    page_title="DebugAI — AI/ML Debugging Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

def set_background(image_path: str):
    absolute_path = os.path.abspath(image_path)
    if not os.path.exists(absolute_path):
        st.warning(f"Background image not found at {absolute_path}")
        return
    with open(absolute_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{b64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    .stApp > header {{ background-color: transparent !important; }}
    [data-testid="stSidebar"] {{
        background-color: rgba(8, 12, 28, 0.93) !important;
    }}
    [data-testid="stSidebar"] * {{ color: #d0e8ff !important; }}
    .stTabs [data-baseweb="tab-panel"] {{
        background-color: rgba(8, 12, 28, 0.82);
        border-radius: 12px;
        padding: 1.2rem;
        margin-top: 0.5rem;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        background-color: rgba(8, 12, 28, 0.75);
        border-radius: 10px;
        padding: 4px;
    }}
    .stTabs [data-baseweb="tab"] {{ color: #a0c4ff !important; font-weight: 500; }}
    .stTabs [aria-selected="true"] {{
        background-color: rgba(127,119,221,0.35) !important;
        color: #ffffff !important;
        border-radius: 8px;
    }}
    .stTextArea textarea {{
        background-color: rgba(8,12,28,0.88) !important;
        color: #e8f4ff !important;
        border: 1px solid rgba(127,119,221,0.5) !important;
        border-radius: 8px !important;
        font-family: monospace !important;
    }}
    .stButton > button {{
        background-color: rgba(127,119,221,0.85) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }}
    .stButton > button:hover {{
        background-color: rgba(127,119,221,1) !important;
    }}
    .stSelectbox > div > div {{
        background-color: rgba(8,12,28,0.88) !important;
        color: #e0e0e0 !important;
        border: 1px solid rgba(127,119,221,0.4) !important;
    }}
    .stMultiSelect > div > div {{
        background-color: rgba(8,12,28,0.88) !important;
        color: #e0e0e0 !important;
    }}
    h1, h2, h3, h4 {{
        color: #a0c4ff !important;
        text-shadow: 0 0 20px rgba(100,160,255,0.3);
    }}
    p, label, .stMarkdown {{ color: #d0e8ff !important; }}
    .stMetric {{
        background-color: rgba(8,12,28,0.82) !important;
        border: 1px solid rgba(127,119,221,0.35) !important;
        border-radius: 10px !important;
        padding: 0.8rem !important;
    }}
    .stMetric label {{ color: #a0c4ff !important; }}
    .stMetric [data-testid="stMetricValue"] {{ color: #ffffff !important; }}
    .stExpander {{
        background-color: rgba(8,12,28,0.82) !important;
        border: 1px solid rgba(127,119,221,0.3) !important;
        border-radius: 10px !important;
    }}
    .stAlert {{
        background-color: rgba(8,12,28,0.85) !important;
        border-radius: 10px !important;
    }}
    [data-testid="stChatMessage"] {{
        background-color: rgba(8,12,28,0.82) !important;
        border-radius: 12px !important;
        margin-bottom: 0.5rem;
    }}
    </style>
    """, unsafe_allow_html=True)

set_background("bg.png")

st.markdown("""
<style>
.severity-critical {
    background:rgba(255,80,80,0.15); color:#ff8080;
    padding:2px 10px; border-radius:12px;
    font-size:12px; font-weight:600;
    border:1px solid rgba(255,80,80,0.4);
}
.severity-high {
    background:rgba(255,140,80,0.15); color:#ffaa80;
    padding:2px 10px; border-radius:12px;
    font-size:12px; font-weight:600;
    border:1px solid rgba(255,140,80,0.4);
}
.severity-medium {
    background:rgba(255,200,80,0.15); color:#ffd080;
    padding:2px 10px; border-radius:12px;
    font-size:12px; font-weight:600;
    border:1px solid rgba(255,200,80,0.4);
}
.severity-low {
    background:rgba(80,160,255,0.15); color:#80c8ff;
    padding:2px 10px; border-radius:12px;
    font-size:12px; font-weight:600;
    border:1px solid rgba(80,160,255,0.4);
}
.stack-badge {
    background:rgba(127,119,221,0.25); color:#c0b8ff;
    padding:4px 14px; border-radius:16px;
    font-size:13px; font-weight:600;
    border:1px solid rgba(127,119,221,0.5);
}
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None

with st.sidebar:
    st.header("⚙️ Settings")
    stack = st.selectbox(
        "AI Stack",
        ["Auto-detect","PyTorch","TensorFlow / Keras","JAX / Flax",
         "HuggingFace Transformers","LangChain","LlamaIndex",
         "OpenAI SDK","Anthropic SDK","RAG Pipeline"],
    )
    workflow = st.selectbox(
        "Workflow Type",
        ["Auto-detect","Model Training","Fine-tuning (LoRA / QLoRA)","RLHF / DPO",
         "LLM API Integration","RAG Pipeline","Inference & Serving",
         "Data Preprocessing","Experiment Tracking"],
    )
    severity_filter = st.multiselect(
        "Show Severities",
        ["🔴 Critical","🟠 High","🟡 Medium","🔵 Low"],
        default=["🔴 Critical","🟠 High","🟡 Medium","🔵 Low"],
    )
    show_traceback = st.toggle("Show Traceback Input", value=True)
    st.divider()
    st.markdown("**DebugAI** — AI/ML Debugging Agent")
    st.caption("Built for AI Engineers")
    if st.button("🗑️ Clear Session", use_container_width=True):
        st.session_state.clear()
        st.rerun()

tab1, tab2, tab3 = st.tabs(
    ["🔍 Debug My Code", "💬 Chat with DebugAI", "📜 Session History"]
)

with tab1:
    col_left, col_right = st.columns([2, 1])
    with col_left:
        code_input = st.text_area(
            "Paste your AI/ML code",
            height=300,
            placeholder=(
                "# Paste your PyTorch / HuggingFace / LangChain / OpenAI code here...\n"
                "# Example: a training loop, a RAG chain, an API call, a tokenizer config..."
            ),
        )
        traceback_input = ""
        if show_traceback:
            traceback_input = st.text_area(
                "Paste error traceback (optional)",
                height=150,
                placeholder="Traceback (most recent call last):\n  File ...\n  ...",
            )
        uploaded = st.file_uploader("Or upload a .py file", type=["py"])
        if uploaded is not None:
            code_input = uploaded.read().decode("utf-8")
            st.code(code_input, language="python")
        analyze_btn = st.button("🔍 Analyze Code", type="primary", use_container_width=True)

    with col_right:
        st.info(
            "**Supported stacks**\n\n"
            "• PyTorch / TF / JAX\n"
            "• HuggingFace (PEFT · TRL · Accelerate)\n"
            "• LangChain / LlamaIndex\n"
            "• OpenAI / Anthropic / Gemini SDKs\n"
            "• FAISS / Chroma / Pinecone\n"
            "• W&B / MLflow / DVC\n"
            "• ONNX / TensorRT"
        )
        st.markdown("**Bug categories**")
        for cat in [
            "Tensor shape & device errors",
            "Training & optimization bugs",
            "GPU / CUDA OOM issues",
            "Fine-tuning (LoRA · QLoRA · DPO)",
            "LLM API & prompt errors",
            "RAG pipeline issues",
            "Tokenization errors",
            "Inference & serving bugs",
            "Experiment tracking",
        ]:
            st.caption(f"• {cat}")

    if analyze_btn:
        if not code_input.strip():
            st.warning("Please paste some AI/ML code or upload a .py file first.")
        else:
            with st.spinner("DebugAI is analyzing your code..."):
                raw = analyze_code(
                    code=code_input,
                    traceback=traceback_input,
                    stack=stack,
                    workflow=workflow,
                )
            if raw.get("error"):
                st.error(f"❌ {raw['error']}")
                st.info("Make sure your GEMINI_API_KEY is set correctly in your .env file.")
            else:
                parsed = parse_response(raw["response"])
                st.session_state.last_result = parsed
                st.session_state.history.append({
                    "preview": code_input[:150] + "...",
                    "stack": parsed["stack"],
                    "bug_count": parsed["bug_count"],
                    "severities": parsed["severity_counts"],
                    "result": parsed,
                })
                st.divider()
                st.markdown(
                    f'<span class="stack-badge">🤖 Stack: {parsed["stack"]}</span>',
                    unsafe_allow_html=True,
                )
                st.write("")
                sev = parsed["severity_counts"]
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total Issues", parsed["bug_count"])
                m2.metric("🔴 Critical", sev.get("CRITICAL", 0))
                m3.metric("🟠 High", sev.get("HIGH", 0))
                m4.metric("🟡 Medium", sev.get("MEDIUM", 0))
                m5.metric("🔵 Low", sev.get("LOW", 0))
                st.divider()
                st.markdown(raw["response"])
                st.divider()
                if parsed["fixed_code"]:
                    st.download_button(
                        "⬇️ Download Fixed Code",
                        data=parsed["fixed_code"],
                        file_name="fixed_code.py",
                        mime="text/plain",
                    )
                if parsed["bug_count"] == 0:
                    st.balloons()
                    st.success("No bugs detected! Clean code.")

with tab2:
    st.subheader("Chat with DebugAI")
    st.caption("Ask follow-up questions about your AI/ML code, error patterns, or debugging strategies.")
    if not st.session_state.messages:
        st.info(
            "Examples you can ask:\n\n"
            "- *Why does device mismatch happen in multi-GPU training?*\n"
            "- *Show me how to properly use gradient checkpointing in PyTorch*\n"
            "- *What is the difference between LoRA rank 8 and rank 64?*\n"
            "- *How do I fix CUDA OOM in a fine-tuning loop?*"
        )
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    if prompt := st.chat_input("Ask DebugAI anything about AI/ML debugging..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = chat_response(st.session_state.messages)
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

with tab3:
    st.subheader("Session History")
    st.caption("All debugging runs from this session.")
    if not st.session_state.history:
        st.info("No sessions yet. Go to **Debug My Code** and analyze some code!")
    else:
        for i, entry in enumerate(reversed(st.session_state.history)):
            idx = len(st.session_state.history) - i
            sev = entry.get("severities", {})
            label = (
                f"Session #{idx}  |  Stack: {entry.get('stack','Unknown')}  "
                f"|  {entry.get('bug_count',0)} issues  "
                f"|  🔴 {sev.get('CRITICAL',0)}  🟠 {sev.get('HIGH',0)}  "
                f"🟡 {sev.get('MEDIUM',0)}  🔵 {sev.get('LOW',0)}"
            )
            with st.expander(label):
                st.code(entry.get("preview",""), language="python")
                if entry.get("result",{}).get("raw"):
                    if st.button(f"View full result #{idx}", key=f"view_{i}"):
                        st.markdown(entry["result"]["raw"])