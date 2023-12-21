import streamlit as st


def manage_openai_credentials():
    with st.sidebar:
        if not st.session_state.get("OPENAI_API_KEY", ""):
            st.toggle("I have a username/password", key="use_password")
            if not st.session_state.use_password:
                st.text_input(
                    "Enter your OpenAI Key", "", type="password", key="api_key"
                )
                if st.session_state.api_key != "":
                    st.session_state["OPENAI_API_KEY"] = st.session_state.api_key
                    st.success("API Key Set")
            else:
                st.text_input("Enter Username", "", key="username")
                st.text_input("Enter Password", "", type="password", key="password")
                if st.session_state.username != "" and st.session_state.password != "":
                    if (
                        st.session_state.username in st.secrets.passwords
                        and st.session_state.password
                        == st.secrets.passwords[st.session_state.username]
                    ):
                        st.session_state["OPENAI_API_KEY"] = st.secrets[
                            "OPENAI_API_KEY"
                        ]
                        st.success("Login Successful")
                    else:
                        st.error("Incorrect Username/Password")
