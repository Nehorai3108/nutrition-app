"""Streamlit sidebar chatbot widget powered by Grok (xAI)."""

import json
import os

import streamlit as st

from chatbot.grok_client import get_client, chat_completion, MODEL
from chatbot.system_prompt import SYSTEM_PROMPT
from chatbot.tools import TOOLS, execute_tool

_MAX_TOOL_ROUNDS = 5


def render_chatbot_sidebar():
    """Render the chatbot widget inside the Streamlit sidebar."""

    st.markdown("### 💬 צ'אט עם העוזר")

    if not os.environ.get("XAI_API_KEY"):
        st.info("להפעלת הצ'אט, הגדר משתנה סביבה XAI_API_KEY")
        return

    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    # Display chat history in a scrollable container
    chat_container = st.container(height=350)
    with chat_container:
        for msg in st.session_state["chat_messages"]:
            if msg["role"] in ("user", "assistant"):
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("שאל אותי משהו...", key="chatbot_input")

    if user_input:
        # Add user message
        st.session_state["chat_messages"].append({"role": "user", "content": user_input})

        # Build messages for API
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in st.session_state["chat_messages"]:
            if msg["role"] in ("user", "assistant"):
                api_messages.append({"role": msg["role"], "content": msg["content"]})
            elif msg["role"] == "tool":
                api_messages.append({
                    "role": "tool",
                    "tool_call_id": msg["tool_call_id"],
                    "content": msg["content"],
                })
            elif msg["role"] == "assistant_tool_calls":
                api_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": msg["tool_calls"],
                })

        # Call Grok in a loop (tool calls may require multiple rounds)
        client = get_client()
        assistant_text = ""
        mutated = False

        for _ in range(_MAX_TOOL_ROUNDS):
            try:
                response = chat_completion(client, api_messages, TOOLS, stream=False)
            except Exception as e:
                assistant_text = f"שגיאה בתקשורת: {e}"
                break

            choice = response.choices[0]
            message = choice.message

            if message.tool_calls:
                # Record the assistant's tool_calls message for context
                tc_list = []
                for tc in message.tool_calls:
                    tc_list.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    })
                api_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tc_list,
                })
                st.session_state["chat_messages"].append({
                    "role": "assistant_tool_calls",
                    "tool_calls": tc_list,
                })

                # Execute each tool call
                for tc in message.tool_calls:
                    fn_name = tc.function.name
                    fn_args = json.loads(tc.function.arguments)
                    result = execute_tool(fn_name, fn_args)

                    if fn_name in ("modify_meal_item", "update_user_profile",
                                   "recalculate_targets", "update_inventory",
                                   "generate_new_meal_plan"):
                        mutated = True

                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                    api_messages.append(tool_msg)
                    st.session_state["chat_messages"].append(tool_msg)

                # Continue the loop — Grok needs to process tool results
                continue

            # Text response — we're done
            assistant_text = message.content or ""
            break

        # Save assistant response
        if assistant_text:
            st.session_state["chat_messages"].append({"role": "assistant", "content": assistant_text})

        # Rerun to display updated chat
        st.rerun()
