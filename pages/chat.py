import copy

import openai
import streamlit as st

import common
import prompts
import providers
from chat_backend import ChatService

# Hardcoded OpenAI model for input verification
VERIFICATION_MODEL = "gpt-4o"


def get_chat_service():
    """Get or create chat service from session state."""
    if 'chat_service' not in st.session_state:
        auth_service = common.get_auth_service()
        st.session_state.chat_service = ChatService(auth_service)
    return st.session_state.chat_service


st.title("Whitelisted Chatbot")

# Get services
chat_service = get_chat_service()

with st.sidebar:
    st.header("Info")
    show_info = st.toggle("Show Info", key="info")

    st.header("Chat Controls")
    previous_whitelist = st.session_state.get("whitelist", "")
    st.session_state.whitelist = st.selectbox(
        "Whitelist Topic", st.secrets["WHITELISTED_TOPICS"]
    )
    
    # Update chat service with whitelist topic
    if st.session_state.whitelist != previous_whitelist:
        chat_service.set_whitelist_topic(st.session_state.whitelist)
        # Maintain backward compatibility with session state
        st.session_state.prompt = prompts.TOPIC_SYSTEM_PROMPT.format(
            topic=st.session_state.whitelist
        )
        st.session_state.system_message = {
            "role": "system",
            "content": st.session_state.prompt,
        }
        # Clear old messages
        if "messages" in st.session_state:
            del st.session_state["messages"]

    common.manage_credentials()

    model_selection = st.selectbox("Model", providers.get_model_provider_options())
    chat_service.set_model_info(model_selection)
    # Maintain backward compatibility
    st.session_state.model_info = providers.parse_model_selection(model_selection)
    
    reset = st.button("Reset Chat")
    if reset:
        chat_service.reset_chat()
        if "messages" in st.session_state:
            del st.session_state["messages"]

    style = st.selectbox("Style", [""] + list(prompts.STYLE_PROMPTS.keys()))

if show_info:
    st.markdown(open("README.md").read())

# Sync messages with session state for backward compatibility
chat_messages = chat_service.get_messages()
if chat_messages:
    st.session_state.messages = chat_messages
else:
    if "messages" in st.session_state:
        del st.session_state["messages"]

# display messages
for message in chat_service.get_display_messages():
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# manage user input
if prompt := st.chat_input("What is up?"):
    # Check if the required API key for the selected model is available
    if not chat_service.add_user_message(prompt):
        st.error(chat_service.get_required_api_key_error())
    else:
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response using chat service
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            error_message = None
            
            for response_chunk, error in chat_service.generate_response(style):
                if error:
                    error_message = error
                    break
                else:
                    full_response = response_chunk
                    message_placeholder.markdown(full_response + "▌")
            
            if error_message:
                if error_message == "Invalid Input":
                    st.markdown("Invalid Input")
                    # Store for reporting
                    st.session_state["last_invalid_message"] = chat_service.get_last_invalid_message()
                else:
                    st.error(error_message)
                    # Handle API key deletion for auth errors
                    if "API Key" in error_message and chat_service.model_info:
                        required_api_key = chat_service.model_info["api_key_name"]
                        if required_api_key in st.session_state:
                            del st.session_state[required_api_key]
            else:
                message_placeholder.markdown(full_response)
        
        # Sync updated messages back to session state
        st.session_state.messages = chat_service.get_messages()
