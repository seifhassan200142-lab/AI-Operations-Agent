from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

API_BASE_URL = os.getenv("AI_OPS_API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Operations Agent", page_icon="🤖", layout="wide")
st.title("AI Operations Agent")
st.caption("Tool-using operations assistant with short-term memory and human approval gates.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = "streamlit-session"


def api_get(path: str) -> Any:
    response = requests.get(f"{API_BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict[str, Any] | None = None) -> Any:
    response = requests.post(f"{API_BASE_URL}{path}", json=payload or {}, timeout=120)
    response.raise_for_status()
    return response.json()


def render_pending_actions() -> None:
    st.subheader("Pending Approvals")
    try:
        actions = api_get("/api/pending-actions")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load pending actions: {exc}")
        return

    pending = [action for action in actions if action["status"] == "pending"]
    if not pending:
        st.info("No pending approvals.")
        return

    for action in pending:
        with st.container(border=True):
            st.write(f"**Action:** `{action['action_type']}`")
            st.write(f"**Reason:** {action['reason']}")
            st.json(action["payload"])
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Approve", key=f"approve-{action['id']}"):
                    result = api_post(f"/api/approve/{action['id']}")
                    st.success(result["message"])
                    st.rerun()
            with col2:
                if st.button("Reject", key=f"reject-{action['id']}"):
                    result = api_post(f"/api/reject/{action['id']}")
                    st.warning(result["message"])
                    st.rerun()


def render_database_views() -> None:
    st.subheader("Tickets")
    try:
        tickets = api_get("/api/tickets")
        st.dataframe(tickets, use_container_width=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load tickets: {exc}")

    st.subheader("Tasks")
    try:
        tasks = api_get("/api/tasks")
        st.dataframe(tasks, use_container_width=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load tasks: {exc}")


tab_chat, tab_approvals, tab_data, tab_tools = st.tabs(["Chat", "Approvals", "Tickets & Tasks", "Tools"])

with tab_chat:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("details"):
                with st.expander("Tool calls and safe reasoning summary"):
                    st.write("**Reasoning summary**")
                    st.write(message["details"].get("reasoning_summary", ""))
                    st.write("**Tool calls**")
                    st.json(message["details"].get("tool_calls", []))

    prompt = st.chat_input("Ask the operations agent...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                payload = {"message": prompt, "session_id": st.session_state.session_id}
                result = api_post("/api/chat", payload)
                st.markdown(result["answer"])
                with st.expander("Tool calls and safe reasoning summary"):
                    st.write("**Reasoning summary**")
                    st.write(result["reasoning_summary"])
                    st.write("**Tool calls**")
                    st.json(result["tool_calls"])
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": result["answer"],
                        "details": result,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"API error: {exc}")

with tab_approvals:
    render_pending_actions()

with tab_data:
    render_database_views()

with tab_tools:
    st.subheader("Registered Tools")
    try:
        tools = api_get("/api/tools")
        st.json(tools)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load tools: {exc}")
