#!/usr/bin/env python3
"""
Refresh Yahoo OAuth token using the refresh token
"""

import json
import requests
import base64
from pathlib import Path
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

def refresh_yahoo_token():
    """Refresh the Yahoo OAuth token using the refresh token"""
    
    # Load current token
    token_file = Path('private/yahoo_token.json')
    if not token_file.exists():
        print("❌ No token file found at private/yahoo_token.json")
        return False
        
    with open(token_file, 'r') as f:
        token_data = json.load(f)
    
    refresh_token = token_data.get('refresh_token')
    if not refresh_token:
        print("❌ No refresh token found in token file")
        return False
    
    # Get credentials from environment
    client_id = os.getenv('YAHOO_CLIENT_ID')
    client_secret = os.getenv('YAHOO_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("❌ Missing YAHOO_CLIENT_ID or YAHOO_CLIENT_SECRET in .env.local")
        return False
    
    print(f"🔄 Refreshing Yahoo OAuth token...")
    print(f"   Client ID: {client_id[:20]}...")
    
    # Prepare refresh request
    token_url = "https://api.login.yahoo.com/oauth2/get_token"
    
    # Create Basic Auth header
    auth_string = f"{client_id}:{client_secret}"
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
    
    try:
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
        with open(token_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print(f"✅ Token refreshed successfully!")
        print(f"   Valid until: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Token saved to: {token_file}")
        
        return True
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text if e.response else 'No response'}")
        return False
    except Exception as e:
        print(f"❌ Error refreshing token: {e}")
        return False

if __name__ == "__main__":
    success = refresh_yahoo_token()
    if success:
        print("\n🎉 Token refresh complete! You can now use the Yahoo API.")
    else:
        print("\n❌ Token refresh failed. You may need to re-authenticate.")
        print("   Run: python3 config/yahoo/yahoo_get_new_oauth.py")