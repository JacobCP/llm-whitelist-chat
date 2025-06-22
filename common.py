import streamlit as st
import providers


def manage_credentials():
    """Manage authentication and load API keys for all providers"""
    with st.sidebar:
        # Check if any API keys are loaded
        api_key_names = providers.get_all_api_key_names()
        if not any(st.session_state.get(key_name, "") for key_name in api_key_names):
            st.text_input("Enter Username", "", key="username")
            st.text_input("Enter Password", "", type="password", key="password")
            if st.session_state.username != "" and st.session_state.password != "":
                if (
                    st.session_state.username in st.secrets.passwords
                    and st.session_state.password
                    == st.secrets.passwords[st.session_state.username]
                ):
                    # Load API keys for all configured providers
                    for key_name in api_key_names:
                        if key_name in st.secrets:
                            st.session_state[key_name] = st.secrets[key_name]
                    st.success("Login Successful")
                else:
                    st.error("Incorrect Username/Password")
