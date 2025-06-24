"""
Authentication backend service decoupled from UI framework.
"""
from typing import Dict, Optional, Tuple
import providers


class AuthenticationService:
    """Handles authentication and credential management independent of UI framework."""
    
    def __init__(self, secrets_config: Dict):
        """Initialize with secrets configuration."""
        self.secrets_config = secrets_config
        self.credentials = {}
        self.authenticated = False
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Authenticate user with username/password.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not username or not password:
            return False, "Username and password required"
        
        if (username in self.secrets_config.get("passwords", {}) and 
            password == self.secrets_config["passwords"][username]):
            
            # Load API keys for all configured providers
            self.authenticated = True
            self.credentials = {}
            
            api_key_names = providers.get_all_api_key_names()
            for key_name in api_key_names:
                if key_name in self.secrets_config:
                    self.credentials[key_name] = self.secrets_config[key_name]
            
            return True, "Login Successful"
        else:
            return False, "Incorrect Username/Password"
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.authenticated
    
    def get_api_key(self, key_name: str) -> Optional[str]:
        """Get API key by name if authenticated."""
        return self.credentials.get(key_name)
    
    def get_all_credentials(self) -> Dict[str, str]:
        """Get all loaded credentials."""
        return self.credentials.copy()
    
    def logout(self):
        """Clear authentication and credentials."""
        self.authenticated = False
        self.credentials = {}