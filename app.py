"""Streamlit frontend for the n8n Competitor Research workflow."""
import os
import uuid
from urllib.parse import urlparse

import requests
import streamlit as st

st.set_page_config(page_title="Competitor Research", page_icon="🔎", layout="wide")
st.title("🔎 Competitor Research")
st.caption("Discover competitors, investigate evidence, and build a sourced briefing.")


def setting(name, default=""):
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default


url = setting("N8N_CHAT_URL").strip()
configured = urlparse(url).scheme in ("https", "http") and bool(urlparse(url).netloc)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("Connection")
    st.success("Endpoint configured") if configured else st.warning("Add your n8n Chat URL")
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
            headers = {}
            header_name = setting("N8N_HEADER_NAME")
            header_value = setting("N8N_HEADER_VALUE")
            if header_name and header_value:
                headers[header_name] = header_value
            username = setting("N8N_BASIC_USER")
            auth = (username, setting("N8N_BASIC_PASSWORD")) if username else None
            outgoing = f"Research key: {research_key.strip()}\n\n{prompt}" if research_key.strip() else prompt
            with st.spinner("The research team is working…"):
                response = requests.post(url, json={"action": "sendMessage", "sessionId": st.session_state.session_id, "chatInput": outgoing}, headers=headers, auth=auth, timeout=(10, 180), allow_redirects=False)
                response.raise_for_status()
                if 300 <= response.status_code < 400:
                    raise ValueError("The endpoint redirected. Use the direct n8n Chat URL.")
                data = response.json()
                if isinstance(data, list):
                    data = data[0] if len(data) == 1 else None
                reply = data.get("output") if isinstance(data, dict) else None
                if not isinstance(reply, str) or not reply.strip():
                    raise ValueError("Expected a JSON response with a text 'output' field. Set Research Chat to When Last Node Finishes and republish n8n.")
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        except requests.Timeout:
            st.warning("The request timed out. n8n may still be working. Check its Executions tab before sending again; this app does not automatically retry.")
        except requests.HTTPError as error:
            st.error(f"n8n returned HTTP {error.response.status_code}. Check the published Chat URL, authentication settings, and Executions tab.")
        except requests.RequestException:
            st.error("Could not connect to n8n. Check the endpoint and your network connection.")
        except ValueError as error:
            st.error(str(error))
