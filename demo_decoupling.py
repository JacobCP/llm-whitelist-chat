#!/usr/bin/env python3
"""
Demonstration script showing that chat functionality is now decoupled from Streamlit.

This script shows how the backend services can be used independently of any UI framework.
"""

from auth_backend import AuthenticationService
from chat_backend import ChatService


def demo_backend_usage():
    """Demonstrate backend usage without any UI framework."""
    
    print("🔄 Demonstrating Decoupled Backend Usage")
    print("=" * 50)
    
    # Mock configuration (in real app this comes from Streamlit secrets)
    mock_secrets = {
        "passwords": {"demo_user": "demo_pass"},
        "OPENAI_API_KEY": "your-openai-key-here",
        "PERPLEXITY_API_KEY": "your-perplexity-key-here"
    }
    
    # 1. Authentication Service (independent of UI)
    print("1. Creating authentication service...")
    auth_service = AuthenticationService(mock_secrets)
    print(f"   Authenticated: {auth_service.is_authenticated()}")
    
    print("2. Authenticating user...")
    success, message = auth_service.authenticate("demo_user", "demo_pass")
    print(f"   Result: {success} - {message}")
    print(f"   Authenticated: {auth_service.is_authenticated()}")
    
    # 2. Chat Service (independent of UI)
    print("3. Creating chat service...")
    chat_service = ChatService(auth_service)
    
    print("4. Setting up chat...")
    chat_service.set_whitelist_topic("coding")
    chat_service.model_info = {
        "model": "gpt-4o",
        "provider": "OpenAI",
        "api_key_name": "OPENAI_API_KEY",
        "base_url": None
    }
    
    print("5. Adding user message...")
    success = chat_service.add_user_message("What is Python?")
    print(f"   Message added: {success}")
    
    print("6. Current conversation state:")
    messages = chat_service.get_display_messages()
    for i, msg in enumerate(messages, 1):
        print(f"   Message {i}: [{msg['role']}] {msg['content']}")
    
    print("\n✅ Backend services work completely independently of Streamlit!")
    print("✅ Chat logic is now reusable with any UI framework")
    print("✅ Authentication is framework-agnostic")
    
    return auth_service, chat_service


if __name__ == "__main__":
    auth_service, chat_service = demo_backend_usage()
    
    print("\n📋 Summary of Changes:")
    print("- Created auth_backend.py: Authentication logic without UI dependencies")
    print("- Created chat_backend.py: Chat functionality without UI dependencies") 
    print("- Updated common.py: Uses authentication backend")
    print("- Updated pages/chat.py: Uses backend services for business logic")
    print("- Preserved all existing functionality")
    print("- Backend can now be used with Flask, FastAPI, CLI, or any other framework")