import os
import secrets
import base64
import hashlib
import urllib.parse
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
from internal_assistant_core import settings

# Centralized Token Manager
class UnifiedTokenManager:
    _instance = None
    _tokens: Dict[str, dict] = {}
    _pkce_data: Dict[str, dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UnifiedTokenManager, cls).__new__(cls)
        return cls._instance
    
    def set_token(self, user_id: str, token_data: dict):
        self._tokens[user_id] = token_data
    
    def get_token(self, user_id: str = "current_user") -> Optional[dict]:
        return self._tokens.get(user_id)
    
    def clear_token(self, user_id: str = "current_user"):
        if user_id in self._tokens:
            del self._tokens[user_id]
        if user_id in self._pkce_data:
            del self._pkce_data[user_id]
    
    def has_token(self, user_id: str = "current_user") -> bool:
        token_data = self._tokens.get(user_id)
        return token_data is not None and "access_token" in token_data
    
    def set_pkce_data(self, user_id: str, pkce_data: dict):
        self._pkce_data[user_id] = pkce_data
    
    def get_pkce_data(self, user_id: str = "current_user") -> Optional[dict]:
        return self._pkce_data.get(user_id)
    
    def clear_pkce_data(self, user_id: str = "current_user"):
        if user_id in self._pkce_data:
            del self._pkce_data[user_id]

# Global unified token manager
unified_token_manager = UnifiedTokenManager()

def generate_pkce_params() -> Dict[str, str]:
    """Generate PKCE parameters"""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    
    return {
        'code_verifier': code_verifier,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }

def build_unified_auth_url() -> str:
    """Build unified auth URL with combined scopes for Todo and Project"""
    pkce_params = generate_pkce_params()
    session_key = "current_user"
    unified_token_manager.set_pkce_data(session_key, pkce_params)
    
    state = secrets.token_urlsafe(32)
    pkce_params['state'] = state
    unified_token_manager.set_pkce_data(session_key, pkce_params)
    
    # Combined scopes for both Todo and Project
    scopes = [
        "https://graph.microsoft.com/User.Read",
        "https://graph.microsoft.com/Tasks.ReadWrite",  # Todo
        "https://graph.microsoft.com/Tasks.Read",       # Todo
        "https://graph.microsoft.com/Group.Read.All"    # Project
    ]
    
    auth_endpoint = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/authorize"
    
    params = {
        'client_id': settings.MS_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': 'http://localhost:8001/auth/callback',
        'scope': ' '.join(scopes),
        'state': state,
        'code_challenge': pkce_params['code_challenge'],
        'code_challenge_method': pkce_params['code_challenge_method'],
        'response_mode': 'query'
    }
    
    
    return f"{auth_endpoint}?{urllib.parse.urlencode(params)}"

def exchange_unified_code_for_token(code: str, state: str = None) -> Optional[dict]:
    """Exchange code for unified token"""
    session_key = "current_user"
    pkce_data = unified_token_manager.get_pkce_data(session_key)
    
    if not pkce_data:
        print("WARNING: PKCE data not found, skipping PKCE validation for testing")
        pkce_data = generate_pkce_params()
    
    if state and pkce_data.get('state') != state:
        print(f"WARNING: State validation failed. Expected: {pkce_data.get('state')}, Got: {state}")
    
    token_endpoint = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/token"
    
    scopes = [
        "https://graph.microsoft.com/User.Read",
        "https://graph.microsoft.com/Tasks.ReadWrite",
        "https://graph.microsoft.com/Tasks.Read", 
        "https://graph.microsoft.com/Group.Read.All"
    ]
    
    token_data = {
        'client_id': settings.MS_CLIENT_ID,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': 'http://localhost:8001/auth/callback',
        'scope': ' '.join(scopes)
    }
    
    if 'code_verifier' in pkce_data:
        token_data['code_verifier'] = pkce_data['code_verifier']
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'http://localhost:8001'
    }
    
    response = requests.post(token_endpoint, data=token_data, headers=headers)
    
    if response.status_code == 200:
        token_response = response.json()
        token_response["received_at"] = datetime.now().isoformat()
        
        # Store unified token
        unified_token_manager.set_token(session_key, token_response)
        unified_token_manager.clear_pkce_data(session_key)
        
        return token_response
    else:
        error_response = response.json() if response.content else {}
        raise Exception(f"OAuth error: {error_response}")

def is_unified_authenticated(user_id: str = "current_user") -> bool:
    """Check if user is authenticated with unified token"""
    return unified_token_manager.has_token(user_id)

def get_unified_token(user_id: str = "current_user") -> str:
    """Get unified access token"""
    token_data = unified_token_manager.get_token(user_id)
    if not token_data:
        raise Exception("User not authenticated")
    return token_data["access_token"]

def get_unified_login_status(user_id: str = "current_user") -> str:
    """Get unified login status"""
    if is_unified_authenticated(user_id):
        try:
            token = get_unified_token(user_id)
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                display_name = user_data.get('displayName', 'Unknown')
                email = user_data.get('mail') or user_data.get('userPrincipalName', 'No email')
                return f"✅ Logged in as: {display_name} ({email})"
            else:
                return "❌ Token invalid"
        except Exception as e:
            return f"❌ Authentication error: {str(e)}"
    else:
        return "❌ Not logged in"

def clear_unified_token(user_id: str = "current_user"):
    """Clear unified token"""
    unified_token_manager.clear_token(user_id)