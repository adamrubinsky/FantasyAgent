#!/usr/bin/env python3
"""
Complete Yahoo OAuth Token Exchange
Run this script to finish the OAuth process with your authorization code
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import requests
from base64 import b64encode

# Load environment variables
load_dotenv('.env.local')

print("\n" + "="*60)
print("YAHOO OAUTH TOKEN EXCHANGE")
print("="*60)

# Your credentials
client_id = os.getenv('YAHOO_CLIENT_ID')
client_secret = os.getenv('YAHOO_CLIENT_SECRET')

# The authorization code from the redirect URL
auth_code = "hr39k3udzu2ymt6vt9hf2pn4p79cp9s3"

print(f"\n📋 Using authorization code: {auth_code[:10]}...")

# Prepare the token exchange request
token_url = "https://api.login.yahoo.com/oauth2/get_token"

# Create Basic Auth header
auth_string = f"{client_id}:{client_secret}"
auth_bytes = auth_string.encode('ascii')
auth_b64 = b64encode(auth_bytes).decode('ascii')

headers = {
    "Authorization": f"Basic {auth_b64}",
    "Content-Type": "application/x-www-form-urlencoded"
}

data = {
    "grant_type": "authorization_code",
    "code": auth_code,
    "redirect_uri": "https://localhost:3000/auth/yahoo/callback"
}

print("\n🔄 Exchanging authorization code for access token...")

try:
    response = requests.post(token_url, headers=headers, data=data)
    
    if response.status_code == 200:
        token_data = response.json()
        
        # Save the token data
        token_file = Path("private/yahoo_token.json")
        token_file.parent.mkdir(exist_ok=True)
        
        with open(token_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print("\n✅ OAuth SUCCESSFUL!")
        print(f"   Access Token: {token_data.get('access_token', '')[:30]}...")
        print(f"   Refresh Token: {token_data.get('refresh_token', '')[:30]}...")
        print(f"   Token saved to: {token_file}")
        
        # Now test the connection with yfpy
        print("\n📊 Testing Yahoo Fantasy connection...")
        
        from yfpy.query import YahooFantasySportsQuery
        
        # Create auth directory for yfpy
        auth_dir = Path("auth")
        auth_dir.mkdir(exist_ok=True)
        
        # Initialize Yahoo query with the token
        yahoo = YahooFantasySportsQuery(
            league_id='475629',
            game_code='nfl',
            game_id=449,
            yahoo_consumer_key=client_id,
            yahoo_consumer_secret=client_secret,
            auth_dir=auth_dir
        )
        
        # yfpy expects token in specific format
        yfpy_token_file = auth_dir / "yahoo_token.json"
        with open(yfpy_token_file, 'w') as f:
            json.dump({
                'access_token': token_data['access_token'],
                'refresh_token': token_data['refresh_token'],
                'expires_in': token_data.get('expires_in', 3600),
                'token_type': 'bearer'
            }, f)
        
        print("\n✅ Token configured for yfpy!")
        print("   You can now use Yahoo Fantasy API!")
        
    else:
        print(f"\n❌ Token exchange failed: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 401:
            print("\n💡 This code may have expired. You need to:")
            print("   1. Go back to the OAuth URL")
            print("   2. Re-authorize the app")
            print("   3. Get a fresh authorization code")
            print("   4. Run this script again with the new code")
            
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure the authorization code is fresh (expires quickly)")
    print("2. Verify your Client ID and Secret are correct")
    print("3. Try re-authorizing if the code expired")

print("\n" + "="*60)
print("Next step: Test Yahoo league connection with test_yahoo_connection.py")
print("="*60)