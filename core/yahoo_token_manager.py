"""
Yahoo OAuth Token Manager
Automatically refreshes expired tokens
"""

import json
import requests
import base64
from pathlib import Path
from datetime import datetime, timedelta
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class YahooTokenManager:
    """Manages Yahoo OAuth tokens with automatic refresh"""
    
    def __init__(self):
        self.token_file = Path('private/yahoo_token.json')
        self.client_id = os.getenv('YAHOO_CLIENT_ID')
        self.client_secret = os.getenv('YAHOO_CLIENT_SECRET')
        
    def is_token_valid(self) -> bool:
        """Check if current token is still valid"""
        if not self.token_file.exists():
            logger.warning("No Yahoo token file found")
            return False
            
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            expires_at_str = token_data.get('expires_at', '')
            if not expires_at_str:
                return False
                
            # Parse expiry time
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.now()
            
            # Add 5 minute buffer - refresh if less than 5 minutes left
            buffer = timedelta(minutes=5)
            
            if now + buffer > expires_at:
                mins_left = (expires_at - now).total_seconds() / 60
                logger.warning(f"Yahoo token expiring soon ({mins_left:.1f} minutes left)")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking token validity: {e}")
            return False
    
    def refresh_token(self) -> bool:
        """Refresh the Yahoo OAuth token"""
        if not self.client_id or not self.client_secret:
            logger.error("Missing Yahoo OAuth credentials in environment")
            return False
            
        if not self.token_file.exists():
            logger.error("No token file to refresh")
            return False
            
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            refresh_token = token_data.get('refresh_token')
            if not refresh_token:
                logger.error("No refresh token found")
                return False
            
            logger.info("Refreshing Yahoo OAuth token...")
            
            # Prepare refresh request
            token_url = "https://api.login.yahoo.com/oauth2/get_token"
            
            # Create Basic Auth header
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }
            
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            
            new_token_data = response.json()
            
            # Update token data
            token_data['access_token'] = new_token_data['access_token']
            if 'refresh_token' in new_token_data:
                token_data['refresh_token'] = new_token_data['refresh_token']
            
            # Calculate new expiry time
            expires_in = new_token_data.get('expires_in', 3600)
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            token_data['expires_at'] = expires_at.isoformat()
            token_data['expires_in'] = expires_in
            
            # Save updated token
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            logger.info(f"Token refreshed! Valid until {expires_at.strftime('%H:%M:%S')}")
            return True
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error refreshing token: {e}")
            if e.response:
                logger.error(f"Response: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return False
    
    def get_valid_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        # Check if token needs refresh
        if not self.is_token_valid():
            logger.info("Token expired or expiring soon, refreshing...")
            if not self.refresh_token():
                logger.error("Failed to refresh token")
                return None
        
        # Load and return the token
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            return token_data.get('access_token')
        except Exception as e:
            logger.error(f"Error loading token: {e}")
            return None
    
    def get_token_info(self) -> Dict:
        """Get information about current token status"""
        if not self.token_file.exists():
            return {"status": "no_token", "message": "No token file found"}
            
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            expires_at_str = token_data.get('expires_at', '')
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.now()
            
            if now > expires_at:
                return {
                    "status": "expired",
                    "message": f"Token expired at {expires_at.strftime('%H:%M:%S')}",
                    "expired_mins_ago": int((now - expires_at).total_seconds() / 60)
                }
            else:
                mins_left = (expires_at - now).total_seconds() / 60
                return {
                    "status": "valid",
                    "message": f"Token valid for {mins_left:.0f} more minutes",
                    "expires_at": expires_at.isoformat(),
                    "minutes_remaining": int(mins_left)
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Global instance
token_manager = YahooTokenManager()