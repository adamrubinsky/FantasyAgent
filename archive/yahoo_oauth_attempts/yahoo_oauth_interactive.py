#!/usr/bin/env python3
"""
Interactive Yahoo OAuth setup - paste the full URL when prompted
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

print("\n" + "="*60)
print("YAHOO OAUTH INTERACTIVE SETUP")
print("="*60)

# Your credentials
client_id = os.getenv('YAHOO_CLIENT_ID')
client_secret = os.getenv('YAHOO_CLIENT_SECRET')
snake_league = '475629'

print(f"\n📋 Configuration:")
print(f"   League: {snake_league}")
print(f"   Client ID: {client_id[:30]}...")

# Import yfpy
try:
    from yfpy.query import YahooFantasySportsQuery
    print("✅ yfpy library ready")
except ImportError:
    print("❌ yfpy not installed. Run: pip3 install yfpy")
    exit(1)

print("\n" + "="*60)
print("INSTRUCTIONS:")
print("="*60)
print("""
1. I'll open your browser for Yahoo authorization
2. Log in and click "Agree" to authorize
3. You'll see an error page (SSL error) - THIS IS NORMAL
4. Copy the ENTIRE URL from your browser
5. Paste it when prompted below

The URL will look like:
https://localhost:3000/auth/yahoo/callback?code=XXXXXX
""")

print("\n🔄 Starting OAuth flow...")
print("When you see 'Enter verifier :' paste your FULL URL")
print("Your URL: https://localhost:3000/auth/yahoo/callback?code=hrbgqjr")
print("\n" + "-"*60)

try:
    # Initialize Yahoo connection with browser callback
    yahoo = YahooFantasySportsQuery(
        league_id=snake_league,
        game_code='nfl',
        game_id=449,  # 2025 season
        yahoo_consumer_key=client_id,
        yahoo_consumer_secret=client_secret,
        browser_callback=True
    )
    
    # The library will now prompt for the verifier/URL
    # User should paste: https://localhost:3000/auth/yahoo/callback?code=hrbgqjr
    
    print("\n📊 Testing connection...")
    settings = yahoo.get_league_settings()
    print(f"✅ Connected to league: {settings.name if hasattr(settings, 'name') else 'League'}")
    
    # Get more league details
    teams = yahoo.get_league_teams()
    print(f"   Teams in league: {len(teams)}")
    
    print("\n✅ OAUTH COMPLETE! Token saved in 'private/' directory")
    print("   You won't need to do this again for ~6 months")
    
    # Test both leagues
    print("\n" + "="*60)
    print("TESTING BOTH LEAGUES:")
    print("="*60)
    
    # Test auction league
    auction_league = '682492'
    print(f"\n📊 Testing Auction League ({auction_league})...")
    
    yahoo_auction = YahooFantasySportsQuery(
        league_id=auction_league,
        game_code='nfl',
        game_id=449,
        yahoo_consumer_key=client_id,
        yahoo_consumer_secret=client_secret
    )
    
    auction_settings = yahoo_auction.get_league_settings()
    print(f"✅ Auction League: {auction_settings.name if hasattr(auction_settings, 'name') else 'Connected'}")
    
    print("\n🎉 SUCCESS! Both leagues are accessible!")
    print("   Snake League: 475629 (Aug 19)")
    print("   Auction League: 682492 (Aug 24)")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nMake sure you paste the FULL URL including 'https://...'")
    print("The code 'hrbgqjr' needs the full URL format")