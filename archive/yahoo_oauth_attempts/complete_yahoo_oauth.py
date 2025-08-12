#!/usr/bin/env python3
"""
Complete Yahoo OAuth with the authorization code
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

print("\n" + "="*60)
print("COMPLETING YAHOO OAUTH")
print("="*60)

from yfpy.query import YahooFantasySportsQuery

# Your credentials
client_id = os.getenv('YAHOO_CLIENT_ID')
client_secret = os.getenv('YAHOO_CLIENT_SECRET')
snake_league = '475629'

# The redirect URL you got
redirect_url = "https://localhost:3000/auth/yahoo/callback?code=hr39k3udzu2ymt6vt9hf2pn4p79cp9s3"

print(f"\n📋 Using authorization code from URL")
print(f"   League: {snake_league}")

try:
    print("\n🔄 Completing OAuth...")
    
    # Initialize with the authorization
    yahoo = YahooFantasySportsQuery(
        league_id=snake_league,
        game_code='nfl',
        game_id=449,  # 2025 season
        yahoo_consumer_key=client_id,
        yahoo_consumer_secret=client_secret,
        browser_callback=True
    )
    
    # When it prompts, you'll paste the URL
    print("\n⚠️ When prompted, paste this URL:")
    print(redirect_url)
    print("\nThe yfpy library will extract the code and complete OAuth")
    
    # Try to test the connection
    print("\n📊 Testing connection...")
    settings = yahoo.get_league_settings()
    print(f"✅ Connected to league: {settings.name if hasattr(settings, 'name') else snake_league}")
    
    print("\n✅ OAuth COMPLETE! Token saved locally.")
    print("   You won't need to do this again!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nIf you see a prompt asking for the URL, paste:")
    print(redirect_url)