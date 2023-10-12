import openai
import streamlit as st

import prompts
import utils

MODEL = "gpt-4"

st.title("Whitelisted Chatbot")

with st.sidebar:
    st.header("Info")
    show_info = st.toggle("Show Info", key="info")

    st.header("Chat Controls")
    if not st.session_state.get("OPENAI_API_KEY", ""):
        use_password = st.toggle("I have a username/password", key="use_password")
        if not use_password:
            api_key = st.text_input("Enter your OpenAI Key", "", type="password")
            if api_key != "":
                st.session_state["OPENAI_API_KEY"] = api_key
                st.success("API Key Set")
        else:
            username = st.text_input("Enter Username", "")
            password = st.text_input("Enter Password", "", type="password")
            passwords = st.secrets["passwords"]
            if username != "" and password != "":
                if username in passwords and password == passwords[username]:
                    st.session_state["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
                    st.success("Login Successful")
                else:
                    st.error("Incorrect Username/Password")

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
system_message = {"role": "system", "content": prompts.SYSTEM_PROMPT}
if "messages" not in st.session_state:
    st.session_state.messages = [system_message]
st.session_state.messages[0] = system_message

# display messages
for message in st.session_state.messages[1:]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# manage user input
if prompt := st.chat_input("What is up?"):
    if not st.session_state.get("OPENAI_API_KEY", ""):
        st.error("please provide api key")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        try:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                openai.api_key = st.session_state["OPENAI_API_KEY"]

                for response in openai.ChatCompletion.create(
                    model=MODEL,
                    messages=[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ],
                    stream=True,
                ):
                    full_response += response.choices[0].delta.get("content", "")
                    message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
        except openai.error.AuthenticationError as e:
            st.error("Invalid API Key: please reset chat and try again")
            st.session_state.messages.pop()
            del st.session_state["OPENAI_API_KEY"]

        if full_response != "Invalid Input":
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )
        else:
            st.session_state["last_invalid_message"] = st.session_state.messages.pop()[
                "content"
            ]