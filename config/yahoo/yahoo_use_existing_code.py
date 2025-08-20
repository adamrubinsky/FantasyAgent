#!/usr/bin/env python3
"""
Use existing Yahoo OAuth code to get access token
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

async def exchange_code_for_token(auth_code: str):
    """Exchange authorization code for access token"""
    
    client_id = os.getenv('YAHOO_CLIENT_ID')
    client_secret = os.getenv('YAHOO_CLIENT_SECRET')
    
    print("\n" + "="*60)
    print("YAHOO TOKEN EXCHANGE")
    print("="*60)
    print(f"Using code: {auth_code[:10]}...")
    print(f"Client ID: {client_id[:30]}...")
    
    token_url = "https://api.login.yahoo.com/oauth2/get_token"
    
    # Build the request data
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': 'oob',  # Out of band for CLI apps
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    print("\nExchanging code for token...")
    
    # Disable SSL verification for macOS certificate issues
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(token_url, data=data) as resp:
            if resp.status == 200:
                token_data = await resp.json()
                
                # Add expiration time
                token_data['expires_at'] = (
                    datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
                ).isoformat()
                
                # Save token to file
                token_file = Path('private/yahoo_token.json')
                token_file.parent.mkdir(exist_ok=True)
                
                with open(token_file, 'w') as f:
                    json.dump(token_data, f, indent=2)
                
                print("\n✅ SUCCESS! Token obtained and saved!")
                print(f"Access Token: {token_data['access_token'][:30]}...")
                print(f"Refresh Token: {token_data['refresh_token'][:30]}...")
                print(f"Expires in: {token_data['expires_in']} seconds")
                print(f"Token saved to: {token_file}")
                
                # Test the token
                print("\n" + "-"*60)
                print("Testing token with Yahoo API...")
                
                league_id = os.getenv('YAHOO_SNAKE_LEAGUE_ID', '475629')
                test_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/449.l.{league_id}"
                
                headers = {
                    'Authorization': f'Bearer {token_data["access_token"]}',
                    'Accept': 'application/json'
                }
                
                async with session.get(test_url, headers=headers) as test_resp:
                    if test_resp.status == 200:
                        print("✅ Token works! Successfully connected to Yahoo Fantasy API!")
                        # Get response text to see what we got
                        content = await test_resp.text()
                        print(f"Response preview: {content[:200]}...")
                    else:
                        print(f"⚠️ Test failed with status: {test_resp.status}")
                        error = await test_resp.text()
                        print(f"Error: {error[:200]}")
                
                return token_data
                
            else:
                error = await resp.text()
                print(f"\n❌ Token exchange failed!")
                print(f"Status: {resp.status}")
                print(f"Error: {error}")
                
                if "invalid_grant" in error:
                    print("\n⚠️ This authorization code may have:")
                    print("  - Already been used (codes are single-use)")
                    print("  - Expired (codes expire quickly)")
                    print("  - Been revoked")
                    print("\nYou'll need to get a new authorization code.")
                
                return None


async def main():
    # The code from our previous successful attempt
    auth_code = "kez93drhftt5kfdw75cjcfsdha4epub9"
    
    result = await exchange_code_for_token(auth_code)
    
    if not result:
        print("\n" + "="*60)
        print("ALTERNATIVE: Get a new authorization code")
        print("="*60)
        print("\n1. Visit this URL:")
        print(f"https://api.login.yahoo.com/oauth2/request_auth?client_id={os.getenv('YAHOO_CLIENT_ID')}&redirect_uri=oob&response_type=code&language=en-us")
        print("\n2. Authorize the app")
        print("3. Copy the code from the success page")
        print("4. Update the auth_code variable in this script")
        print("5. Run this script again")


if __name__ == "__main__":
    asyncio.run(main())