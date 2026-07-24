import os
import uuid
import logging
import streamlit as st
from dotenv import load_dotenv

from langgraph.errors import GraphRecursionError
from basic_chatbot import build_chatbot_graph

# Configure logging for internal diagnostics (prevents leaking to UI)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables (.env file)
load_dotenv()


# Helper function for Secure Secrets Management (st.secrets priority, os.getenv fallback)
def get_secret(key_name: str) -> str | None:
    """Prioritizes Streamlit's native secrets management before falling back to environment variables."""
    try:
        if key_name in st.secrets:
            return st.secrets[key_name]
    except Exception:
        pass
    return os.getenv(key_name)


# Streamlit Page Configuration
st.set_page_config(
    page_title="Agentic AI Chatbot - Enterprise Security Hardened",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark-themed accents & clean typography)
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
    }
    .main-header {
        font-family: 'Inter', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4F46E5, #9333EA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #9CA3AF;
        font-size: 1.0rem;
        margin-bottom: 1.5rem;
    }
    .status-badge-ok {
        background-color: #065F46;
        color: #34D399;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .status-badge-warn {
        background-color: #991B1B;
        color: #FCA5A5;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .session-badge {
        background-color: #1E293B;
        color: #94A3B8;
        padding: 6px 12px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# --- Session Initialization & Session Isolation ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []


# --- Sidebar Configuration ---
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/bot.png", width=64)
    st.title("🛡️ Security Controls")
    st.markdown("---")

    # Secrets Management Evaluation
    groq_key = get_secret("GROQ_API_KEY")
    tavily_key = get_secret("TAVILY_API_KEY")

    # Fallback to manual entry if secrets/env are not set
    if not groq_key:
        groq_key = st.text_input("Groq API Key", type="password")
        if groq_key:
            os.environ["GROQ_API_KEY"] = groq_key

    if not tavily_key:
        tavily_key = st.text_input("Tavily API Key", type="password")
        if tavily_key:
            os.environ["TAVILY_API_KEY"] = tavily_key

    # Display API Connection Badges
    if groq_key or os.getenv("GROQ_API_KEY"):
        st.markdown('Groq API Key: <span class="status-badge-ok">Configured</span>', unsafe_allow_html=True)
    else:
        st.markdown('Groq API Key: <span class="status-badge-warn">Missing</span>', unsafe_allow_html=True)

    if tavily_key or os.getenv("TAVILY_API_KEY"):
        st.markdown('Tavily API Key: <span class="status-badge-ok">Configured</span>', unsafe_allow_html=True)
    else:
        st.markdown('Tavily API Key: <span class="status-badge-warn">Missing</span>', unsafe_allow_html=True)

    st.markdown("---")

    # Model Selection
    selected_model = st.selectbox(
        "Select LLM Model",
        options=["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        index=0
    )

    # Isolated Session Status
    st.markdown("### 🔒 Active Session")
    short_session_id = st.session_state.thread_id[:8] + "..." + st.session_state.thread_id[-4:]
    st.markdown(f'<div class="session-badge">ID: {short_session_id}</div>', unsafe_allow_html=True)
    st.caption("Each session is cryptographically isolated using UUIDv4.")

    # New Isolated Session Button
    if st.button("🔄 Start New Session", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("### 🛡️ Security Hardening")
    st.markdown("- 🔐 **Prompt Injection Shield**: System prompt hardening active.")
    st.markdown("- 🔁 **Loop Cap**: `recursion_limit` set to 6.")
    st.markdown("- 🚫 **Sanitized Errors**: Raw tracebacks suppressed in UI.")


# --- Main Chat UI ---
st.markdown('<div class="main-header">Agentic AI Chatbot</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Security-Hardened Enterprise LangGraph ReAct Agent</div>', unsafe_allow_html=True)


# Cache compiled graph resource per selected model
@st.cache_resource(show_spinner=False)
def get_graph_app(model_name: str):
    return build_chatbot_graph(model_name=model_name)


# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# User Input Handler
if prompt := st.chat_input("How can I help you today? (e.g. 'Search latest AI news' or 'Multiply 25 by 14')"):
    active_groq_key = get_secret("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    if not active_groq_key:
        st.error("GROQ_API_KEY is not configured. Please add it to your secrets or environment variables.")
        st.stop()

    # Render User Message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Execute LangGraph Agent with Security Measures
    with st.chat_message("assistant"):
        with st.spinner("Agent evaluating request safely..."):
            try:
                chatbot_app = get_graph_app(selected_model)
                
                # Security Measure 2 & 3: Session Isolation + Infinite Loop Prevention (recursion_limit=6)
                config = {
                    "configurable": {"thread_id": st.session_state.thread_id},
                    "recursion_limit": 6
                }

                # Invoke the LangGraph agent
                result = chatbot_app.invoke(
                    {"messages": [("user", prompt)]},
                    config=config
                )

                # Extract final assistant response
                if "messages" in result and result["messages"]:
                    last_msg = result["messages"][-1]
                    assistant_response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                else:
                    assistant_response = "No response generated by the assistant."

                st.markdown(assistant_response)
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})

            # Security Measure 4: Graceful Error Handling & Leak Prevention
            except GraphRecursionError:
                logger.warning(f"Recursion limit reached for session {st.session_state.thread_id}")
                user_error = (
                    "⚠️ **Execution Limit Reached**: The assistant reached the maximum allowed tool execution "
                    "steps (6 iterations) without producing a final answer. Please rephrase your query to be more specific."
                )
                st.error(user_error)
                st.session_state.messages.append({"role": "assistant", "content": user_error})

            except Exception as e:
                # Log actual exception details server-side, never expose stack traces to UI
                logger.error(f"Internal Error in session {st.session_state.thread_id}: {e}", exc_info=True)
                user_error = (
                    "⚠️ **System Error**: An error occurred while processing your request. "
                    "The system has safely logged the event. Please try again or click **Start New Session** in the sidebar."
                )
                st.error(user_error)
                st.session_state.messages.append({"role": "assistant", "content": user_error})
