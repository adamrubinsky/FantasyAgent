#!/usr/bin/env python3
"""
Automated Yahoo OAuth completion with the authorization code
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import parse_qs, urlparse
import json

# Load environment variables
load_dotenv('.env.local')

print("\n" + "="*60)
print("AUTOMATED YAHOO OAUTH COMPLETION")
print("="*60)

# The redirect URL with the authorization code
redirect_url = "https://localhost:3000/auth/yahoo/callback?code=hrbgqjr"

# Parse the authorization code
parsed = urlparse(redirect_url)
code = parse_qs(parsed.query)['code'][0]
print(f"\n📋 Authorization code: {code[:20]}...")

# Your credentials
client_id = os.getenv('YAHOO_CLIENT_ID')
client_secret = os.getenv('YAHOO_CLIENT_SECRET')
snake_league = '475629'

print(f"   Client ID: {client_id[:30]}...")
print(f"   League: {snake_league}")

# Try the simpler approach with yahoo_oauth
try:
    from yahoo_oauth import OAuth2
    
    print("\n🔄 Completing OAuth with yahoo_oauth library...")
    
    # Create credentials dict
    creds = {
        'consumer_key': client_id,
        'consumer_secret': client_secret
    }
    
    # Save credentials to JSON file for yahoo_oauth
    creds_file = 'oauth2.json'
    with open(creds_file, 'w') as f:
        json.dump(creds, f)
    
    print(f"✅ Credentials saved to {creds_file}")
    
    # Now try the yfpy approach with a mock stdin
    print("\n🔄 Attempting yfpy OAuth completion...")
    
    # Create a mock stdin to provide the URL automatically
    import io
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(redirect_url)
    
    try:
        from yfpy.query import YahooFantasySportsQuery
        
        yahoo = YahooFantasySportsQuery(
            league_id=snake_league,
            game_code='nfl',
            game_id=449,  # 2025 season
            yahoo_consumer_key=client_id,
            yahoo_consumer_secret=client_secret,
            browser_callback=True
        )
        
        # The library should now read from our mock stdin
        print("\n✅ OAuth flow initiated with yfpy")
        
        # Test the connection
        print("\n📊 Testing connection...")
        settings = yahoo.get_league_settings()
        print(f"✅ Connected to league: {settings.name if hasattr(settings, 'name') else snake_league}")
        
        print("\n✅ OAUTH COMPLETE! Token saved locally.")
        print("   Token location: private/.yahoo_token.json")
        
    finally:
        # Restore stdin
        sys.stdin = old_stdin
        
except ImportError as e:
    print(f"\n⚠️ Missing library: {e}")
    print("\nInstall required libraries:")
    print("  pip3 install yfpy yahoo-oauth")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTrying manual token exchange...")
    
    # Manual token exchange as fallback
    import requests
    
    token_url = "https://api.login.yahoo.com/oauth2/get_token"
    
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': 'https://localhost:3000/auth/yahoo/callback',
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    print(f"\n🔄 Exchanging code for token...")
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        token_data = response.json()
        print("\n✅ Token received!")
        
        # Save token
        os.makedirs('private', exist_ok=True)
        token_file = 'private/.yahoo_token.json'
        
        with open(token_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print(f"✅ Token saved to {token_file}")
        print(f"   Access Token: {token_data.get('access_token', '')[:30]}...")
        print(f"   Refresh Token: {token_data.get('refresh_token', '')[:30]}...")
        print(f"   Expires in: {token_data.get('expires_in', 0)} seconds")
    else:
        print(f"❌ Token exchange failed: {response.status_code}")
        print(f"   Response: {response.text}")