#!/usr/bin/env python3
"""
Yahoo OAuth Setup - Run this directly in your terminal
This creates a persistent token that lasts for months
"""

import os
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

print("\n" + "="*60)
print("YAHOO FANTASY OAUTH SETUP")
print("="*60)

# Import yfpy
try:
    from yfpy.query import YahooFantasySportsQuery
    print("✅ yfpy library ready")
except ImportError:
    print("❌ yfpy not installed. Run: pip3 install yfpy")
    exit(1)

# Get credentials
client_id = os.getenv('YAHOO_CLIENT_ID')
client_secret = os.getenv('YAHOO_CLIENT_SECRET')
snake_league = os.getenv('YAHOO_SNAKE_LEAGUE_ID', '475629')

print(f"\n📋 Configuration:")
print(f"   League: {snake_league}")
print(f"   Client ID: {client_id[:30]}...")

# Build the OAuth URL manually first
auth_url = f"https://api.login.yahoo.com/oauth2/request_auth?client_id={client_id}&redirect_uri=https://localhost:3000/auth/yahoo/callback&response_type=code&language=en-us"

print("\n" + "="*60)
print("STEP 1: AUTHORIZE THE APP")
print("="*60)
print("\nOpen this URL in your browser:")
print(f"\n{auth_url}\n")

print("After authorizing, you'll see an error page.")
print("That's normal! Copy the ENTIRE URL from your browser.")
print("It will look like: https://localhost:3000/auth/yahoo/callback?code=...")

# Open browser automatically
webbrowser.open(auth_url)
print("\n✅ Opened browser for authorization")

print("\n" + "="*60)
print("STEP 2: COMPLETE OAUTH")
print("="*60)
print("""
After authorizing in your browser:

1. Copy the ENTIRE redirect URL (with the error page)
2. Run this command in your terminal:

python3 -c "from yfpy.query import YahooFantasySportsQuery; yahoo = YahooFantasySportsQuery(league_id='475629', game_code='nfl', game_id=449, yahoo_consumer_key='YOUR_CLIENT_ID', yahoo_consumer_secret='YOUR_SECRET', browser_callback=True)"

3. Paste the URL when prompted
4. Token will be saved!

""")

print("="*60)
print("TOKEN PERSISTENCE INFO")
print("="*60)
print("""
✅ The token is saved in a .json file locally
✅ It auto-refreshes when needed (access token: ~1 hour)
✅ Refresh token lasts ~6 months
✅ You only need to do this OAuth dance ONCE

After this, all Yahoo API calls will work automatically!
""")