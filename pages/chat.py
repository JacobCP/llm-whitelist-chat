import openai
import streamlit as st

import common
import prompts
import providers
import utils

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
        
        verification_result = response.choices[0].message.content.strip()
        return verification_result != "Invalid Input"
        
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
    st.selectbox(
        "Whitelist Type", ["Topics", "Skills", "GPTs"], index=0, key="whitelist_type"
    )
    previous_whitelist = st.session_state.get("whitelist", "")
    if st.session_state["whitelist_type"] == "Topics":
        st.session_state.whitelist = st.selectbox(
            "Whitelist Topic", st.secrets["WHITELISTED_TOPICS"]
        )
        st.session_state.prompt = prompts.TOPIC_SYSTEM_PROMPT.format(
            topic=st.session_state.whitelist
        )
    elif st.session_state["whitelist_type"] == "Skills":
        st.session_state.whitelist = st.selectbox(
            "Whitelist Skill", list(st.secrets["WHITELISTED_SKILLS"])
        )
        st.session_state.skill_description = st.secrets["WHITELISTED_SKILLS"][
            st.session_state.whitelist
        ]
        if st.session_state.skill_description != "":
            st.session_state.skill_description = (
                f"\nThe definition of '{st.session_state.whitelist}' is:\n"
                f'"{st.session_state.skill_description}"\n'
            )
        st.session_state.prompt = prompts.SKILL_SYSTEM_PROMPT.format(
            skill=st.session_state.whitelist,
            skill_description=st.session_state.skill_description,
        )
    elif st.session_state["whitelist_type"] == "GPTs":
        st.session_state.whitelist = st.selectbox(
            "Whitelist Skill", list(st.secrets["WHITELISTED_GPTS"])
        )
        st.session_state.gpt_guidelines = st.secrets["WHITELISTED_GPTS"][
            st.session_state.whitelist
        ]
        st.session_state.prompt = prompts.GPT_SYSTEM_PROMPT.format(
            gpt_guidelines=st.session_state.gpt_guidelines,
        )
    st.session_state.system_message = {
        "role": "system",
        "content": st.session_state.prompt,
    }
    if st.session_state.whitelist != previous_whitelist:
        if "messages" in st.session_state:
            del st.session_state["messages"]

    common.manage_credentials()

    model_selection = st.selectbox(
        "Model", providers.get_model_provider_options()
    )
    model_info = providers.parse_model_selection(model_selection)
    model = model_info["model"]
    reset = st.button("Reset Chat")
    if reset:
        if "messages" in st.session_state:
            del st.session_state["messages"]

    st.header("Report Problems")
    report = st.toggle("Report Problem", key="report")
    if report:
        reported_by = st.text_input("Your Email", "")
        reporting_reason = st.selectbox(
            "Reason fo Reporting", ["Allowed Incorrectly", "Blocked Incorrectly"]
        )
        additional_comments = st.text_input("Additional Comments (optional)", "")
        subject = f"({reported_by}) Whitelisting Chatbot Report: {reporting_reason}"
        text = utils.format_messages(st.session_state.messages[1:])
        if reporting_reason == "Blocked Incorrectly":
            text += (
                f"\nUser: {st.session_state.get('last_invalid_message', 'not found')}"
            )
        if additional_comments:
            text = additional_comments + "\n\n" + text

        def send_report_email():
            if not reported_by:
                st.error("Email required to report problems")
                return

            utils.send_email(
                st.secrets["email"],
                st.secrets["password"],
                st.secrets["email_to"],
                subject,
                text,
            )
            st.session_state["report"] = False
            st.success("Report Sent!")

        send_email = st.button("Report", on_click=send_report_email)

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
    required_api_key = model_info["api_key_name"]
    if not st.session_state.get(required_api_key, ""):
        st.error(f"Please provide {model_info['provider']} API key")
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
                    if model_info["base_url"]:
                        client_kwargs["base_url"] = model_info["base_url"]
                    
                    client = openai.OpenAI(**client_kwargs)
                    
                    # Use messages WITHOUT system message for generation
                    generation_messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages[1:]  # Skip system message
                    ]
                    
                    for response in client.chat.completions.create(
                        model=model,
                        messages=generation_messages,
                        stream=True,
                    ):
                        full_response += response.choices[0].delta.content or ""
                        message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                
                # Add the response to messages
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )
                
            except openai.AuthenticationError:
                st.error(f"Invalid {model_info['provider']} API Key: please reset chat and try again")
                st.session_state.messages.pop()
                del st.session_state[required_api_key]
        else:
            # Input is invalid - remove user message and store for reporting
            st.session_state["last_invalid_message"] = st.session_state.messages.pop()[
                "content"
            ]
