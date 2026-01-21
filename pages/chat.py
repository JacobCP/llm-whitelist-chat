import copy

import openai
import streamlit as st

import common
import prompts

# Hardcoded OpenAI model for input verification
VERIFICATION_MODEL = "gpt-4o"

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


def verify_input_with_openai(messages):
    """
    Verify input using hardcoded OpenAI model.
    Returns True if input is valid, False if "Invalid Input"
    """
    try:
        # Use OpenAI API key for verification
        openai_api_key = st.session_state.get("OPENAI_API_KEY")
        if not openai_api_key:
            st.error("OpenAI API key required for input verification")
            return False

        client = openai.OpenAI(api_key=openai_api_key)

        # Create a non-streaming response for verification
        response = client.responses.create(
            model=VERIFICATION_MODEL,
            input=messages,
        )

        verification_result = response.output_text
        if verification_result:
            verification_result = verification_result.strip()
            return verification_result != "Invalid Input"
        else:
            return False

    except openai.AuthenticationError:
        st.error("Invalid OpenAI API Key for verification")
        return False
    except Exception as e:
        st.error(f"Verification error: {str(e)}")
        return False


st.title("Whitelisted Chatbot")

with st.sidebar:
    st.header("Chat Controls")
    previous_whitelist = st.session_state.get("whitelist", "")
    st.session_state.whitelist = st.selectbox(
        "Whitelist Topic", st.secrets["WHITELISTED_TOPICS"]
    )
    st.session_state.prompt = prompts.TOPIC_SYSTEM_PROMPT.format(
        topic=st.session_state.whitelist
    )
    st.session_state.system_message = {
        "role": "system",
        "content": st.session_state.prompt,
    }
    if st.session_state.whitelist != previous_whitelist:
        if "messages" in st.session_state:
            del st.session_state["messages"]

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

    reset = st.button("Reset Chat")
    if reset:
        if "messages" in st.session_state:
            del st.session_state["messages"]

    style = st.selectbox("Style", [""] + list(prompts.STYLE_PROMPTS.keys()))


# initialize/update system message
if "messages" not in st.session_state:
    st.session_state.messages = [st.session_state.system_message]
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
        with st.chat_message("user"):
            st.markdown(prompt)

        # Step 1: Verify input using hardcoded OpenAI model with system message
        verification_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ]

        if verify_input_with_openai(verification_messages):
            # Step 2: Input is valid, generate response with selected model WITHOUT system message
            try:
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    full_response = ""

                    client = openai.OpenAI(api_key=st.session_state[required_api_key])

                    st.session_state.current_messages = copy.deepcopy(
                        st.session_state.messages
                    )

                    # Use messages WITHOUT system message for generation
                    if not style:
                        generation_messages = st.session_state.current_messages[1:]
                    else:
                        st.session_state.current_messages[0] = {
                            "role": "system",
                            "content": prompts.STYLE_PROMPTS[style],
                        }
                        generation_messages = st.session_state.current_messages

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

                # Add the response to messages
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )

            except openai.AuthenticationError:
                st.error(
                    "Invalid OpenAI API Key: please reset chat and try again"
                )
                st.session_state.messages.pop()
                del st.session_state[required_api_key]
        else:
            # Input is invalid - remove user message and store for reporting
            st.session_state["last_invalid_message"] = st.session_state.messages.pop()[
                "content"
            ]
            with st.chat_message("assistant"):
                st.markdown("Invalid Input")
