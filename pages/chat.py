import copy

import openai
import streamlit as st

import chat_store
import common
import prompts

# Models that support the Responses API (latest/common as of 2026-01)
RESPONSES_MODELS = [
    "gpt-4o",
    "gpt-5-mini",
    "gpt-5.2",
    "gpt-5.2-codex",
]

# Model feature flags (only show UI + send params when supported)
# Note: you mentioned `gpt-5.2` supports both; earlier models may not.
MODEL_CAPABILITIES = {
    "gpt-5.2": {"web_search": True, "thinking": True},
    "gpt-5.2-codex": {"web_search": True, "thinking": True},
}

THINKING_LEVELS = ["low", "medium", "high", "xhigh"]
UNSAVED_CHAT_OPTION = "__unsaved__"


def chat_has_content(messages):
    if not isinstance(messages, list):
        return False
    for message in messages:
        if message.get("role") in ("user", "assistant"):
            if str(message.get("content", "")).strip():
                return True
    return False


def update_system_message():
    st.session_state.prompt = prompts.TOPIC_SYSTEM_PROMPT.format(
        topic=st.session_state.whitelist
    )
    st.session_state.system_message = {
        "role": "system",
        "content": st.session_state.prompt,
    }


def ensure_current_chat_id():
    chat_id = st.session_state.get("current_chat_id")
    if chat_id:
        return chat_id
    chat_id = chat_store.new_chat_id()
    st.session_state.current_chat_id = chat_id
    st.session_state.chat_whitelist = st.session_state.whitelist
    st.session_state.pending_selected_chat_id = chat_id
    return chat_id


def save_current_chat():
    messages = st.session_state.get("messages", [])
    if not chat_has_content(messages):
        chat_id = st.session_state.get("current_chat_id")
        if chat_id:
            chat_store.delete_chat(chat_id)
        st.session_state.current_chat_id = None
        st.session_state.pending_selected_chat_id = UNSAVED_CHAT_OPTION
        return
    chat_id = ensure_current_chat_id()
    chat_store.save_chat(
        chat_id=chat_id,
        name=st.session_state.get("chat_name", ""),
        messages=messages,
        whitelist=st.session_state.get("chat_whitelist", st.session_state.whitelist),
    )


def start_new_chat():
    st.session_state.current_chat_id = None
    st.session_state.chat_name = chat_store.default_chat_name()
    st.session_state.chat_whitelist = st.session_state.whitelist
    st.session_state.messages = [st.session_state.system_message]
    st.session_state.pending_selected_chat_id = UNSAVED_CHAT_OPTION


def delete_current_chat():
    chat_id = st.session_state.get("current_chat_id")
    if not chat_id:
        return
    chat_store.delete_chat(chat_id)


def load_chat(chat_id):
    chat_data = chat_store.load_chat(chat_id)
    if not chat_data:
        return False
    st.session_state.current_chat_id = chat_id
    st.session_state.chat_name = chat_data.get("name") or chat_store.default_chat_name()
    st.session_state.chat_whitelist = chat_data.get("whitelist") or st.session_state.whitelist
    if st.session_state.chat_whitelist != st.session_state.whitelist:
        st.session_state.pending_whitelist = st.session_state.chat_whitelist
    messages = chat_data.get("messages")
    if not isinstance(messages, list):
        messages = []
    st.session_state.messages = messages
    return True


def format_chat_label(chat_summary):
    name = chat_summary.get("name") or "Untitled"
    updated_at = chat_summary.get("updated_at") or chat_summary.get("created_at")
    if updated_at:
        return f"{name} ({updated_at.replace('T', ' ')})"
    return name


st.title("Whitelisted Chatbot")

if "whitelist" not in st.session_state:
    st.session_state.whitelist = st.secrets["WHITELISTED_TOPICS"][0]
if "pending_whitelist" in st.session_state:
    st.session_state.whitelist = st.session_state.pop("pending_whitelist")

with st.sidebar:
    st.header("Chat Controls")
    st.selectbox("Whitelist Topic", st.secrets["WHITELISTED_TOPICS"], key="whitelist")
    update_system_message()

    if "current_chat_id" not in st.session_state:
        start_new_chat()

    if st.session_state.get("chat_whitelist") != st.session_state.whitelist:
        start_new_chat()
        st.rerun()

    col1, col2 = st.columns(2)
    if col1.button("Save & New"):
        save_current_chat()
        start_new_chat()
        st.rerun()
    if col2.button("Delete"):
        delete_current_chat()
        start_new_chat()
        st.rerun()

    chat_summaries = chat_store.list_chats()
    chat_options = [summary["id"] for summary in chat_summaries]
    chat_labels = {
        summary["id"]: format_chat_label(summary) for summary in chat_summaries
    }
    current_chat_id = st.session_state.get("current_chat_id")
    current_unsaved = not current_chat_id or current_chat_id not in chat_labels
    if current_unsaved:
        chat_options.insert(0, UNSAVED_CHAT_OPTION)
        chat_labels[UNSAVED_CHAT_OPTION] = (
            f"{st.session_state.get('chat_name', 'Untitled')} (unsaved)"
        )

    if "pending_selected_chat_id" in st.session_state:
        st.session_state.selected_chat_id = st.session_state.pop(
            "pending_selected_chat_id"
        )
    if "selected_chat_id" not in st.session_state:
        st.session_state.selected_chat_id = (
            UNSAVED_CHAT_OPTION if current_unsaved else current_chat_id
        )
    if st.session_state.selected_chat_id not in chat_options:
        st.session_state.selected_chat_id = (
            UNSAVED_CHAT_OPTION
            if current_unsaved
            else (chat_options[0] if chat_options else UNSAVED_CHAT_OPTION)
        )

    st.selectbox(
        "Chats",
        chat_options,
        format_func=lambda chat_id: chat_labels.get(chat_id, chat_id),
        key="selected_chat_id",
    )
    selected_chat_id = st.session_state.selected_chat_id
    if selected_chat_id != UNSAVED_CHAT_OPTION and selected_chat_id != current_chat_id:
        if load_chat(selected_chat_id):
            st.rerun()

    st.text_input("Chat name", key="chat_name", on_change=save_current_chat)

    common.manage_credentials()

    st.session_state.model = st.selectbox(
        "Model",
        RESPONSES_MODELS,
    )

    # Optional model features (only shown when supported)
    capabilities = MODEL_CAPABILITIES.get(
        st.session_state.model, {"web_search": False, "thinking": False}
    )

    if capabilities["web_search"]:
        st.checkbox("Enable web search", key="enable_web_search", value=False)
    else:
        st.session_state["enable_web_search"] = False

    if capabilities["thinking"]:
        if st.session_state.get("thinking_level") not in THINKING_LEVELS:
            st.session_state["thinking_level"] = "medium"
        st.selectbox("Thinking level", THINKING_LEVELS, key="thinking_level")
    else:
        st.session_state["thinking_level"] = None

    style = st.selectbox("Style", [""] + list(prompts.STYLE_PROMPTS.keys()))


# initialize/update system message
if "messages" not in st.session_state or not isinstance(
    st.session_state.messages, list
):
    st.session_state.messages = [st.session_state.system_message]
elif not st.session_state.messages:
    st.session_state.messages = [st.session_state.system_message]
else:
    st.session_state.messages[0] = st.session_state.system_message

# display messages
for message in st.session_state.messages[1:]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# manage user input
if prompt := st.chat_input("What is up?"):
    # Check if the required API key for the selected model is available
    required_api_key = "OPENAI_API_KEY"
    if not st.session_state.get(required_api_key, ""):
        st.error("Please provide OpenAI API key")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_current_chat()
        with st.chat_message("user"):
            st.markdown(prompt)

        # Single call: the selected model should output "Invalid Input" directly.
        try:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""

                client = openai.OpenAI(api_key=st.session_state[required_api_key])

                # Always include the whitelist system message. If a style is selected,
                # add it as an additional system message (without replacing the whitelist).
                generation_messages = copy.deepcopy(st.session_state.messages)
                if style:
                    generation_messages.insert(
                        1,
                        {
                            "role": "system",
                            "content": prompts.STYLE_PROMPTS[style],
                        },
                    )

                selected_model = st.session_state.model
                capabilities = MODEL_CAPABILITIES.get(
                    selected_model, {"web_search": False, "thinking": False}
                )
                request_kwargs = {
                    "model": selected_model,
                    "input": generation_messages,
                    "stream": True,
                }

                if capabilities["web_search"] and st.session_state.get(
                    "enable_web_search", False
                ):
                    request_kwargs["tools"] = [{"type": "web_search"}]

                if capabilities["thinking"] and st.session_state.get("thinking_level"):
                    request_kwargs["reasoning"] = {
                        "effort": st.session_state["thinking_level"]
                    }

                for event in client.responses.create(**request_kwargs):
                    if getattr(event, "type", None) == "response.output_text.delta":
                        full_response += getattr(event, "delta", "") or ""
                        message_placeholder.markdown(full_response + "▌")
                    elif getattr(event, "type", None) == "error":
                        raise RuntimeError(getattr(event, "error", "Unknown error"))

            message_placeholder.markdown(full_response)

            if full_response.strip() == "Invalid Input":
                # Input is invalid - remove user message and store for reporting
                st.session_state["last_invalid_message"] = st.session_state.messages.pop()[
                    "content"
                ]
                save_current_chat()
            else:
                # Add the response to messages
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )
                save_current_chat()

        except openai.AuthenticationError:
            st.error("Invalid OpenAI API Key: please start a new chat and try again")
            st.session_state.messages.pop()
            del st.session_state[required_api_key]
            save_current_chat()
