"""
Chat backend service decoupled from UI framework.
"""
import copy
from typing import Dict, List, Optional, Tuple, Iterator, Any
import openai
import prompts
import providers


class ChatService:
    """Handles chat functionality independent of UI framework."""
    
    # Hardcoded OpenAI model for input verification
    VERIFICATION_MODEL = "gpt-4o"
    
    def __init__(self, auth_service):
        """Initialize with authentication service."""
        self.auth_service = auth_service
        self.messages = []
        self.system_message = None
        self.whitelist_topic = ""
        self.model_info = None
        self.last_invalid_message = ""
    
    def set_whitelist_topic(self, topic: str):
        """Set the whitelist topic and update system message."""
        if topic != self.whitelist_topic:
            self.whitelist_topic = topic
            self.system_message = {
                "role": "system",
                "content": prompts.TOPIC_SYSTEM_PROMPT.format(topic=topic),
            }
            # Reset messages when topic changes
            self.messages = [self.system_message] if self.system_message else []
    
    def set_model_info(self, model_selection: str):
        """Set the model information from selection string."""
        self.model_info = providers.parse_model_selection(model_selection)
    
    def reset_chat(self):
        """Reset the chat messages."""
        self.messages = [self.system_message] if self.system_message else []
    
    def get_messages(self) -> List[Dict]:
        """Get current chat messages."""
        return self.messages.copy()
    
    def get_display_messages(self) -> List[Dict]:
        """Get messages for display (excluding system message)."""
        return self.messages[1:] if len(self.messages) > 1 else []
    
    def verify_input(self, messages: List[Dict]) -> Tuple[bool, str]:
        """
        Verify input using OpenAI model.
        
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        try:
            openai_api_key = self.auth_service.get_api_key("OPENAI_API_KEY")
            if not openai_api_key:
                return False, "OpenAI API key required for input verification"
            
            client = openai.OpenAI(api_key=openai_api_key)
            
            response = client.chat.completions.create(
                model=self.VERIFICATION_MODEL,
                messages=messages,
                stream=False,
            )
            
            verification_result = response.choices[0].message.content
            if verification_result:
                verification_result = verification_result.strip()
                return verification_result != "Invalid Input", ""
            else:
                return False, "No verification result"
        
        except openai.AuthenticationError:
            return False, "Invalid OpenAI API Key for verification"
        except Exception as e:
            return False, f"Verification error: {str(e)}"
    
    def add_user_message(self, content: str) -> bool:
        """
        Add user message and verify if required API key is available.
        
        Returns:
            True if API key is available, False otherwise
        """
        if not self.model_info:
            return False
        
        required_api_key = self.model_info["api_key_name"]
        if not self.auth_service.get_api_key(required_api_key):
            return False
        
        self.messages.append({"role": "user", "content": content})
        return True
    
    def get_required_api_key_error(self) -> str:
        """Get error message for missing API key."""
        if not self.model_info:
            return "No model selected"
        return f"Please provide {self.model_info['provider']} API key"
    
    def generate_response(self, style: str = "") -> Iterator[Tuple[str, Optional[str]]]:
        """
        Generate response for the current conversation.
        
        Args:
            style: Style prompt to apply
            
        Yields:
            Tuple of (partial_response: str, error_message: Optional[str])
            Final yield will have complete response and any error
        """
        if not self.model_info:
            yield "", "No model selected"
            return
        
        required_api_key = self.model_info["api_key_name"]
        api_key = self.auth_service.get_api_key(required_api_key)
        if not api_key:
            yield "", f"Missing {self.model_info['provider']} API key"
            return
        
        # Verify input first
        verification_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in self.messages
        ]
        
        is_valid, error_msg = self.verify_input(verification_messages)
        if not is_valid:
            # Remove the user message and store for reporting
            if self.messages and self.messages[-1]["role"] == "user":
                self.last_invalid_message = self.messages.pop()["content"]
            yield "", "Invalid Input"
            return
        
        try:
            # Create client with provider-specific API key and base URL
            client_kwargs = {"api_key": api_key}
            if self.model_info["base_url"]:
                client_kwargs["base_url"] = self.model_info["base_url"]
            
            client = openai.OpenAI(**client_kwargs)
            
            # Prepare messages for generation
            current_messages = copy.deepcopy(self.messages)
            
            # Apply style if specified
            if not style:
                current_messages[0]["content"] = ""
            else:
                current_messages[0] = {
                    "role": "system",
                    "content": prompts.STYLE_PROMPTS[style],
                }
                if self.model_info["provider"] == "Perplexity":
                    current_messages[-1]["content"] += (
                        "\n\n(" + prompts.STYLE_PROMPTS[style] + ")"
                    )
            
            full_response = ""
            citations = None
            
            # Stream the response
            for response in client.chat.completions.create(
                model=self.model_info["model"],
                messages=current_messages,
                stream=True,
            ):
                content = response.choices[0].delta.content or ""
                full_response += content
                yield full_response, None
                
                # Handle Perplexity citations
                if (self.model_info["provider"] == "Perplexity" and 
                    hasattr(response, 'citations')):
                    citations = "\n\n".join([
                        f"{citation} [{idx}]"
                        for idx, citation in enumerate(response.citations)
                    ])
            
            # Add citations if present
            if citations:
                full_response += f"\n\nCitations:\n\n{citations}"
            
            # Add the response to messages
            self.messages.append({"role": "assistant", "content": full_response})
            
            yield full_response, None
            
        except openai.AuthenticationError:
            # Remove the user message on auth error
            if self.messages and self.messages[-1]["role"] == "user":
                self.messages.pop()
            error_msg = f"Invalid {self.model_info['provider']} API Key: please reset chat and try again"
            yield "", error_msg
        except Exception as e:
            # Remove the user message on other errors
            if self.messages and self.messages[-1]["role"] == "user":
                self.messages.pop()
            yield "", f"Error generating response: {str(e)}"
    
    def get_last_invalid_message(self) -> str:
        """Get the last invalid message that was rejected."""
        return self.last_invalid_message