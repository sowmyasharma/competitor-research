"""Streamlit frontend for the n8n Competitor Research workflow."""
import json
import os
import uuid
from itertools import chain
from urllib.parse import urlparse

import requests
import streamlit as st

from n8n_streaming import is_stream_event, iter_orchestrator_chunks

st.set_page_config(page_title="Competitor Research", page_icon="🔎", layout="wide")
st.markdown(
    """
    <style>
    :root {
      color-scheme: light;
      --ink: #17181d;
      --muted: #667085;
      --line: #e8e6e8;
      --mint: #2fcf9f;
      --blue: #145cff;
    }
    .stApp {
      color: var(--ink);
      background: linear-gradient(115deg, #fffdec 0%, #fff5ef 43%, #f2eaf4 100%);
    }
    [data-testid="stHeader"] { background: rgba(255,255,255,.82); }
    [data-testid="stAppViewContainer"] > .main .block-container {
      max-width: 1120px;
      padding-top: 2.2rem;
      padding-bottom: 8rem;
    }
    [data-testid="stSidebar"] {
      background: rgba(255,255,255,.88);
      border-right: 1px solid var(--line);
    }
    .hero { text-align: center; padding: 1.2rem 0 .3rem; }
    .hero h1 { color: var(--ink); font-size: clamp(2.25rem, 5vw, 3.5rem); letter-spacing: -.055em; margin: 0 0 .45rem; }
    .hero p { color: #333640; font-size: 1.12rem; margin: 0; }
    .hero-mark { color: var(--mint); font-size: 1.05rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; margin-bottom: .7rem; }
    [data-testid="stChatMessage"] {
      background: rgba(255,255,255,.84);
      border: 1px solid rgba(232,230,232,.9);
      border-radius: 18px;
      box-shadow: 0 8px 28px rgba(33,30,44,.045);
      padding: 1rem 1.2rem;
      margin-bottom: .8rem;
      color: #17181d !important;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] em {
      color: #17181d !important;
      -webkit-text-fill-color: #17181d !important;
      opacity: 1 !important;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] table {
      width: 100% !important;
      table-layout: fixed !important;
      border-collapse: collapse;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] th,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] td {
      width: 25% !important;
      vertical-align: top;
      overflow-wrap: anywhere;
      white-space: normal;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] th {
      background: #f7f8fb;
      font-weight: 650;
    }
    [data-testid="stChatInput"] {
      background: #fff;
      border: 1px solid #d9d9e1;
      border-radius: 16px;
      box-shadow: 0 8px 28px rgba(33,30,44,.08);
    }
    [data-testid="stChatInput"] > div { background: #fff; border-radius: 16px; }
    [data-testid="stChatInput"]:focus-within { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(20,92,255,.13); }
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] textarea:focus,
    [data-testid="stChatInput"] textarea:disabled {
      color: #17181d !important;
      -webkit-text-fill-color: #17181d !important;
      caret-color: #145cff;
      background-color: #fff !important;
      opacity: 1 !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
      color: #667085 !important;
      -webkit-text-fill-color: #667085 !important;
      opacity: 1 !important;
    }
    .stButton > button, .stDownloadButton > button {
      border-radius: 10px;
      border: 1px solid #dfe2e8;
      background: white;
      color: #343945;
      transition: all .15s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--mint); color: #118c68; }
    [data-testid="stStatusWidget"] { border-radius: 14px; }
    [data-testid="stAlert"] { border-radius: 14px; }
    </style>
    <div class="hero">
      <div class="hero-mark">Competitor intelligence</div>
      <h1>Research with clarity.</h1>
      <p>Discover competitors, investigate evidence, and build a sourced briefing.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def setting(name, default=""):
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default


def render_streamed_reply(lines):
    reply_parts = []
    reply_placeholder = st.empty()
    for chunk in iter_orchestrator_chunks(lines):
        reply_parts.append(chunk)
        reply_placeholder.markdown("".join(reply_parts))
    reply = "".join(reply_parts)
    reply_placeholder.markdown(reply)
    return reply


url = setting("N8N_CHAT_URL").strip()
configured = urlparse(url).scheme in ("https", "http") and bool(urlparse(url).netloc)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("Connection")
    if configured:
        st.success("Endpoint configured")
    else:
        st.warning("Add your n8n Chat URL")
    st.caption("Configuration does not confirm connectivity.")
    st.subheader("Research session")
    st.code(st.session_state.session_id, language=None)
    research_key = st.text_input("Research key (optional)", help="Use the same key to resume saved research after starting a new conversation.")
    if st.button("New conversation"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
    st.caption("New conversation clears chat context. Saved n8n research checkpoints remain available.")
    if st.session_state.messages:
        transcript = "\n\n".join(f"**{m['role'].title()}**\n\n{m['content']}" for m in st.session_state.messages)
        st.download_button("Download conversation", transcript, "competitor-research.md", "text/markdown")

if not configured:
    st.info("Copy .streamlit/secrets.toml.example to .streamlit/secrets.toml and enter the production Chat URL from n8n. See README.md for setup.")
if not st.session_state.messages:
    st.markdown('<div style="height: 16rem"></div>', unsafe_allow_html=True)
    st.markdown('Try: **Research Notion’s top three competitors for small-business knowledge management in the US. Include pricing, core features, positioning, and news from the last 90 days.**')

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Company, product scope, or follow-up question…", disabled=not configured)
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            headers = {"Accept": "text/plain"}
            header_name = setting("N8N_HEADER_NAME")
            header_value = setting("N8N_HEADER_VALUE")
            if header_name and header_value:
                headers[header_name] = header_value
            username = setting("N8N_BASIC_USER")
            auth = (username, setting("N8N_BASIC_PASSWORD")) if username else None
            outgoing = f"Research key: {research_key.strip()}\n\n{prompt}" if research_key.strip() else prompt
            processing = st.empty()
            processing.caption("⏳ Research is running in n8n. Waiting for its response…")
            with requests.post(
                url,
                json={
                    "action": "sendMessage",
                    "sessionId": st.session_state.session_id,
                    "chatInput": outgoing,
                },
                headers=headers,
                auth=auth,
                timeout=(10, 600),
                allow_redirects=False,
                stream=True,
            ) as response:
                response.raise_for_status()
                if 300 <= response.status_code < 400:
                    raise ValueError("The endpoint redirected. Use the direct n8n Chat URL.")

                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if content_type not in ("application/json", "text/plain") and not content_type.endswith("+json"):
                    raise ValueError(
                        f"Expected an application/json or text/plain response, got "
                        f"'{content_type or 'unknown content type'}'."
                    )

                response.encoding = "utf-8"
                lines = iter(response.iter_lines(decode_unicode=True))
                first_line = next((line for line in lines if line and line.strip()), None)
                if first_line is None:
                    raise ValueError("n8n returned an empty response.")

                if content_type == "text/plain" or is_stream_event(first_line):
                    reply = render_streamed_reply(chain((first_line,), lines))
                else:
                    try:
                        data = json.loads("\n".join(chain((first_line,), lines)))
                    except json.JSONDecodeError as error:
                        raise ValueError("n8n returned invalid JSON.") from error
                    if isinstance(data, list):
                        data = data[0] if len(data) == 1 else None
                    reply = data.get("output") if isinstance(data, dict) else None
                    if not isinstance(reply, str) or not reply.strip():
                        raise ValueError("Expected a JSON response with a text 'output' field.")
                    st.markdown(reply)
            processing.empty()
            st.session_state.messages.append({"role": "assistant", "content": reply})
        except requests.Timeout:
            processing.empty()
            st.warning("The stream timed out. Check n8n Executions before sending again; this app does not automatically retry.")
        except requests.HTTPError as error:
            processing.empty()
            st.error(f"n8n returned HTTP {error.response.status_code}. Check the published Chat URL, authentication settings, and Executions tab.")
        except requests.RequestException as error:
            processing.empty()
            details = str(error).replace(url, "<configured n8n URL>")
            st.error(f"n8n request failed ({type(error).__name__}): {details}")
        except ValueError as error:
            processing.empty()
            st.error(str(error))
