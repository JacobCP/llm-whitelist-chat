import copy

import openai
import streamlit as st

import common
import prompts
import providers

# Hardcoded OpenAI model for input verification
VERIFICATION_MODEL = "gpt-4o"


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
        response = client.chat.completions.create(
            model=VERIFICATION_MODEL,
            messages=messages,
            stream=False,
        )

        verification_result = response.choices[0].message.content
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
    st.header("Info")
    show_info = st.toggle("Show Info", key="info")

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

    model_selection = st.selectbox("Model", providers.get_model_provider_options())
    st.session_state.model_info = providers.parse_model_selection(model_selection)
    reset = st.button("Reset Chat")
    if reset:
        if "messages" in st.session_state:
            del st.session_state["messages"]

    style = st.selectbox("Style", [""] + list(prompts.STYLE_PROMPTS.keys()))

if show_info:
    st.markdown(open("README.md").read())


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
    required_api_key = st.session_state.model_info["api_key_name"]
    if not st.session_state.get(required_api_key, ""):
        st.error(f"Please provide {st.session_state.model_info['provider']} API key")
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

                    # Create client with provider-specific API key and base URL
                    client_kwargs = {"api_key": st.session_state[required_api_key]}
                    if st.session_state.model_info["base_url"]:
                        client_kwargs["base_url"] = st.session_state.model_info[
                            "base_url"
                        ]

                    client = openai.OpenAI(**client_kwargs)

                    st.session_state.current_messages = copy.deepcopy(
                        st.session_state.messages
                    )

                    # Use messages WITHOUT system message for generation
                    if not style:
                        st.session_state.current_messages[0]["content"] = ""
                    else:
                        st.session_state.current_messages[0] = {
                            "role": "system",
                            "content": prompts.STYLE_PROMPTS[style],
                        }
                        if st.session_state.model_info["provider"] == "Perplexity":
                            st.session_state.current_messages[-1]["content"] += (
                                "\n\n(" + prompts.STYLE_PROMPTS[style] + ")"
                            )

                    for response in client.chat.completions.create(
                        model=st.session_state.model_info["model"],
                        messages=st.session_state.current_messages,
                        stream=True,
                    ):
                        full_response += response.choices[0].delta.content or ""
                        message_placeholder.markdown(full_response + "▌")
                    if st.session_state.model_info["provider"] == "Perplexity":
                        citations = "\n\n".join(
                            [
                                f"{citation} [{idx}]"
                                for idx, citation in enumerate(response.citations)
                            ]
                        )
                        full_response += f"\n\nCitations:\n\n{citations}"

                message_placeholder.markdown(full_response)

                # Add the response to messages
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )

            except openai.AuthenticationError:
                st.error(
                    f"Invalid {st.session_state.model_info['provider']} API Key: please reset chat and try again"
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
