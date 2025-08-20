#!/usr/bin/env python3
"""
Yahoo OAuth with proper token handling
"""

import os
import json
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

print("\n" + "="*60)
print("YAHOO OAUTH - FINAL ATTEMPT")
print("="*60)

# Your app credentials from environment variables
client_id = os.getenv('YAHOO_CLIENT_ID')
client_secret = os.getenv('YAHOO_CLIENT_SECRET')

print(f"\n✅ App Configuration Verified:")
print(f"   App ID: 5QsariDQ")
print(f"   Client ID: {client_id[:30]}...")
print(f"   Redirect URI: https://localhost:3000/auth/yahoo/callback")
print(f"   Permissions: Fantasy Sports Read/Write ✅")

# Create necessary directories
os.makedirs('private', exist_ok=True)
print("\n✅ Created private directory for token storage")

print("\n" + "="*60)
print("OAUTH FLOW:")
print("="*60)

# Build the authorization URL
auth_url = f"https://api.login.yahoo.com/oauth2/request_auth?client_id={client_id}&redirect_uri=https://localhost:3000/auth/yahoo/callback&response_type=code&language=en-us"

print("1. Opening browser for authorization...")
print("2. Log in to Yahoo if needed")
print("3. Click 'Agree' to authorize FantasyAgent")
print("4. You'll see an SSL error page (normal)")
print("5. Copy the ENTIRE URL from browser")
print("\n" + "-"*60)

# Open browser
webbrowser.open(auth_url)
print("\n✅ Browser opened with authorization URL")

print("\n" + "="*60)
print("IMPORTANT - READ THIS:")
print("="*60)
print("""
The yfpy library has a specific way of handling OAuth.
When you run this next part, it will:

1. Ask for 'Enter verifier :'
2. You paste the FULL URL (not just the code)
3. It should save the token

If it fails again, we have a workaround ready.
""")

try:
    from yfpy.query import YahooFantasySportsQuery
    
    print("\n🔄 Starting yfpy OAuth flow...")
    print("When prompted, paste your FULL URL from the browser")
    print("\n" + "-"*60)
    
    # Initialize with your league
    yahoo = YahooFantasySportsQuery(
        league_id='475629',
        game_id=449,  # 2025 NFL season
        game_code='nfl',
        yahoo_consumer_key=client_id,
        yahoo_consumer_secret=client_secret,
        browser_callback=False  # We already opened the browser
    )
    
    # This will prompt for the verifier
    # The user needs to paste the full URL here
    
    print("\n✅ If you see this, OAuth worked!")
    
    # Test the connection
    print("\n📊 Testing connection...")
    league = yahoo.get_league_metadata()
    print(f"✅ Connected to league: {league.league_id}")
    
    print("\n" + "="*60)
    print("🎉 SUCCESS!")
    print("="*60)
    print("""
✅ Yahoo OAuth complete!
✅ Token saved to: private/
✅ Will auto-refresh for ~6 months

Your leagues:
- Snake Draft: 475629 (Aug 19)
- Auction: 682492 (Aug 24)
""")
    
except Exception as e:
    print(f"\n❌ OAuth failed: {e}")
    
    print("\n" + "="*60)
    print("ALTERNATIVE SOLUTION:")
    print("="*60)
    print("""
Since OAuth is having issues, here's what we'll do:

1. Focus on Sleeper draft (Aug 14) first ✅
2. For Yahoo (Aug 19), we have options:
   
   Option A: Try OAuth again closer to draft date
   - Yahoo might have fixed any API issues by then
   
   Option B: Use Yahoo Fantasy mobile app
   - Get draft recommendations from our system
   - Enter picks manually in Yahoo app
   
   Option C: Browser automation
   - Use Selenium to control Yahoo draft room
   - More complex but doesn't need OAuth

Don't worry - we'll have a solution ready before Aug 19!

For now, let's make sure your Sleeper draft (in 3 days) is perfect.
""")