#!/usr/bin/env python3
"""
Get new Yahoo OAuth authorization code
Interactive script to help you through the OAuth process
"""

import os
import webbrowser
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

print("\n" + "="*70)
print(" YAHOO OAUTH - GET NEW AUTHORIZATION CODE")
print("="*70)

client_id = os.getenv('YAHOO_CLIENT_ID')

# Build the authorization URL
auth_url = f"https://api.login.yahoo.com/oauth2/request_auth?client_id={client_id}&redirect_uri=oob&response_type=code&language=en-us"

print("\n📋 STEP-BY-STEP INSTRUCTIONS:")
print("-" * 70)
print("\n1️⃣  Opening your browser to Yahoo OAuth page...")
print("2️⃣  Log in to Yahoo if needed")
print("3️⃣  Click 'Agree' to authorize FantasyAgent") 
print("4️⃣  You'll see a SUCCESS page with a code")
print("5️⃣  Copy ONLY the code (not the whole page)")
print("\n" + "-"*70)

# Open browser
webbrowser.open(auth_url)

print("\n✅ Browser opened!")
print("\n" + "="*70)
print(" IMPORTANT - READ THIS CAREFULLY:")
print("="*70)
print("""
After you authorize, Yahoo will show you a page that says:

    "You have successfully authorized this application"
    
Below that will be a code that looks like:
    
    ➡️  7-character code (letters and numbers)
    
Example: "abc123d" (yours will be different)

COPY ONLY THE CODE, not any other text!
""")

print("\n" + "="*70)
print(" ENTER YOUR CODE:")
print("="*70)

# Get the code from user
auth_code = input("\nPaste your authorization code here: ").strip()

if auth_code:
    print(f"\n✅ Got code: {auth_code}")
    
    # Update the exchange script with the new code
    exchange_script = f'''#!/usr/bin/env python3
"""
Exchange Yahoo OAuth code for access token
Auto-generated with new code: {auth_code}
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('.env.local')

async def exchange_code_for_token():
    auth_code = "{auth_code}"
    client_id = os.getenv('YAHOO_CLIENT_ID')
    client_secret = os.getenv('YAHOO_CLIENT_SECRET')
    
    print(f"\\nExchanging code: {{auth_code[:4]}}... for token")
    
    token_url = "https://api.login.yahoo.com/oauth2/get_token"
    
    data = {{
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': 'oob',
        'client_id': client_id,
        'client_secret': client_secret
    }}
    
    # Disable SSL for macOS
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(token_url, data=data) as resp:
            if resp.status == 200:
                token_data = await resp.json()
                
                # Save token
                token_data['expires_at'] = (
                    datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
                ).isoformat()
                
                token_file = Path('private/yahoo_token.json')
                token_file.parent.mkdir(exist_ok=True)
                
                with open(token_file, 'w') as f:
                    json.dump(token_data, f, indent=2)
                
                print("\\n✅ SUCCESS! Token obtained and saved!")
                print(f"Access Token: {{token_data['access_token'][:30]}}...")
                print(f"Token saved to: {{token_file}}")
                
                # Test the token
                league_id = os.getenv('YAHOO_SNAKE_LEAGUE_ID', '475629')
                test_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/449.l.{{league_id}}"
                
                headers = {{'Authorization': f'Bearer {{token_data["access_token"]}}'}}
                
                async with session.get(test_url, headers=headers) as test_resp:
                    if test_resp.status == 200:
                        print("\\n✅ Token verified! Ready for draft!")
                        return token_data
                    else:
                        print(f"\\n⚠️ Token test failed: {{test_resp.status}}")
                        return token_data
            else:
                error = await resp.text()
                print(f"\\n❌ Exchange failed: {{error}}")
                return None

if __name__ == "__main__":
    result = asyncio.run(exchange_code_for_token())
    if result:
        print("\\n🎉 You're all set for tomorrow's draft!")
'''
    
    # Save the exchange script
    exchange_file = 'yahoo_exchange_new_code.py'
    with open(exchange_file, 'w') as f:
        f.write(exchange_script)
    
    print(f"\n✅ Created exchange script: {exchange_file}")
    print("\n" + "="*70)
    print(" NEXT STEP:")
    print("="*70)
    print(f"\nRun this command to exchange your code for a token:")
    print(f"\n    python3 {exchange_file}\n")
    
else:
    print("\n❌ No code entered. Please try again.")