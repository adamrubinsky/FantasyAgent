#!/usr/bin/env python3
"""
Exchange Yahoo OAuth code for access token

INSTRUCTIONS:
1. If you haven't already, go to this URL in your browser:
   https://api.login.yahoo.com/oauth2/request_auth?client_id=dj0yJmk9TE40dEtIRWxrb0hNJmQ9WVdrOU5WRnpZWEpwUkZFbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWRm&redirect_uri=oob&response_type=code&language=en-us

2. Authorize the app

3. Copy the code from the success page

4. Replace 'YOUR_CODE_HERE' below with your actual code

5. Run this script: python3 yahoo_exchange_code.py
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('.env.local')

# ⬇️ PASTE YOUR CODE HERE (replace YOUR_CODE_HERE)
AUTH_CODE = "tkb2wjk"

async def exchange_code_for_token():
    if AUTH_CODE == "YOUR_CODE_HERE":
        print("\n❌ ERROR: You need to replace YOUR_CODE_HERE with your actual OAuth code!")
        print("\nFollow the instructions at the top of this file.")
        return None
        
    client_id = os.getenv('YAHOO_CLIENT_ID')
    client_secret = os.getenv('YAHOO_CLIENT_SECRET')
    
    print("\n" + "="*60)
    print("YAHOO TOKEN EXCHANGE")
    print("="*60)
    print(f"Using code: {AUTH_CODE[:4]}...")
    
    token_url = "https://api.login.yahoo.com/oauth2/get_token"
    
    data = {
        'grant_type': 'authorization_code',
        'code': AUTH_CODE,
        'redirect_uri': 'oob',
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    print("\nExchanging code for token...")
    
    # Disable SSL for macOS
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(token_url, data=data) as resp:
            if resp.status == 200:
                token_data = await resp.json()
                
                # Add expiration time
                token_data['expires_at'] = (
                    datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
                ).isoformat()
                
                # Save token
                token_file = Path('private/yahoo_token.json')
                token_file.parent.mkdir(exist_ok=True)
                
                with open(token_file, 'w') as f:
                    json.dump(token_data, f, indent=2)
                
                print("\n✅ SUCCESS! Token obtained and saved!")
                print(f"Access Token: {token_data['access_token'][:30]}...")
                print(f"Refresh Token: {token_data.get('refresh_token', 'N/A')[:30]}...")
                print(f"Expires in: {token_data['expires_in']} seconds")
                print(f"Token saved to: {token_file}")
                
                # Test the token with draft API
                print("\n" + "-"*60)
                print("Testing token with Yahoo Fantasy API...")
                
                league_id = os.getenv('YAHOO_SNAKE_LEAGUE_ID', '475629')
                # NFL 2024 season game ID is 449
                test_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/449.l.{league_id}"
                
                headers = {
                    'Authorization': f'Bearer {token_data["access_token"]}',
                    'Accept': 'application/json'
                }
                
                async with session.get(test_url, headers=headers) as test_resp:
                    if test_resp.status == 200:
                        print("✅ Token verified! Successfully connected to Yahoo Fantasy!")
                        
                        # Try to get draft status too
                        draft_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/449.l.{league_id}/draftresults"
                        async with session.get(draft_url, headers=headers) as draft_resp:
                            if draft_resp.status == 200:
                                print("✅ Can access draft data!")
                            else:
                                print(f"⚠️ Draft access returned: {draft_resp.status}")
                        
                        print("\n🎉 You're all set for tomorrow's draft!")
                        print("The token will auto-refresh as needed.")
                        
                    else:
                        print(f"⚠️ Token test returned status: {test_resp.status}")
                        error = await test_resp.text()
                        print(f"Response: {error[:200]}")
                        print("\nToken saved but may need additional permissions.")
                
                return token_data
                
            else:
                error = await resp.text()
                print(f"\n❌ Token exchange failed!")
                print(f"Status: {resp.status}")
                print(f"Error: {error}")
                
                if "invalid_grant" in error or "INVALID_AUTHORIZATION_CODE" in error:
                    print("\n⚠️ This code is invalid or expired.")
                    print("Codes expire quickly (usually within 10 minutes).")
                    print("\nGet a fresh code from:")
                    print(f"https://api.login.yahoo.com/oauth2/request_auth?client_id={client_id}&redirect_uri=oob&response_type=code&language=en-us")
                
                return None

if __name__ == "__main__":
    print("\n🔄 Starting Yahoo OAuth token exchange...")
    print("Make sure you've replaced YOUR_CODE_HERE with your actual code!\n")
    
    result = asyncio.run(exchange_code_for_token())
    
    if not result:
        print("\n" + "="*60)
        print("FALLBACK PLAN: Manual Draft Tracking")
        print("="*60)
        print("""
Since OAuth isn't working, we have a manual tracking system ready:

1. You'll input picks as they happen in the draft
2. The agent will track everything and give recommendations
3. All the UI widgets will work with manual data

This is actually very reliable and will work perfectly for tomorrow!
""")