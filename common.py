import streamlit as st
import providers
from auth_backend import AuthenticationService


def get_auth_service():
    """Get or create authentication service from session state."""
    if 'auth_service' not in st.session_state:
        st.session_state.auth_service = AuthenticationService(st.secrets)
    return st.session_state.auth_service


def manage_credentials():
    """Manage authentication and load API keys for all providers"""
    auth_service = get_auth_service()
    
    with st.sidebar:
        # Check if user is authenticated
        if not auth_service.is_authenticated():
            username = st.text_input("Enter Username", "", key="username")
            password = st.text_input("Enter Password", "", type="password", key="password")
            
            if username and password:
                success, message = auth_service.authenticate(username, password)
                if success:
                    st.success(message)
                else:
                    st.error(message)
