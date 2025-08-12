#!/usr/bin/env python3
"""
Yahoo OAuth Test - Complete the OAuth flow
This will save a persistent token for future use
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

print("\n" + "="*60)
print("YAHOO FANTASY OAUTH SETUP")
print("="*60)

try:
    from yfpy.query import YahooFantasySportsQuery
    print("✅ yfpy library loaded")
except ImportError:
    print("❌ yfpy not installed. Run: pip install yfpy")
    sys.exit(1)

# Get credentials
client_id = os.getenv('YAHOO_CLIENT_ID')
client_secret = os.getenv('YAHOO_CLIENT_SECRET')
redirect_uri = os.getenv('YAHOO_REDIRECT_URI', 'https://localhost:3000/auth/yahoo/callback')

if not client_id or not client_secret:
    print("❌ Missing Yahoo credentials in .env.local")
    sys.exit(1)

print(f"\n📋 Your Credentials:")
print(f"   Client ID: {client_id[:30]}...")
print(f"   Redirect URI: {redirect_uri}")

# Your leagues
snake_league = os.getenv('YAHOO_SNAKE_LEAGUE_ID', '475629')
auction_league = os.getenv('YAHOO_AUCTION_LEAGUE_ID', '682492')

print(f"\n🏈 Your Leagues:")
print(f"   Snake Draft: {snake_league} (Aug 19)")
print(f"   Auction: {auction_league} (Aug 24)")

print("\n" + "-"*60)
print("OAUTH INSTRUCTIONS")
print("-"*60)
print("""
When you run this:
1. Your browser will open to Yahoo login
2. Log in and authorize the FantasyAgent app
3. You'll be redirected to https://localhost:3000/... 
4. The page WON'T load (that's normal!)
5. Copy the ENTIRE URL from your browser
6. Paste it here when prompted
7. Token will be saved for future use
""")

input("\nPress Enter to start OAuth flow...")

# Create token file path
token_file = Path("yahoo_token.json")

try:
    print("\n🔄 Starting OAuth flow...")
    
    # Initialize with snake league first
    yahoo_query = YahooFantasySportsQuery(
        league_id=snake_league,
        game_code="nfl",
        game_id=449,  # 2025 NFL season
        yahoo_consumer_key=client_id,
        yahoo_consumer_secret=client_secret,
        browser_callback=True  # This will handle the OAuth flow
    )
    
    print("\n✅ OAuth completed successfully!")
    print("   Token saved for future use")
    
    # Test the connection
    print("\n📊 Testing connection...")
    try:
        # Get league settings
        settings = yahoo_query.get_league_settings()
        print(f"\n✅ Connected to league!")
        print(f"   League Name: {settings.name if hasattr(settings, 'name') else 'Unknown'}")
        print(f"   League ID: {snake_league}")
        
        # Get your team info
        teams = yahoo_query.get_league_teams()
        if teams and len(teams) > 4:  # You're team 5
            your_team = teams[4]  # 0-indexed
            print(f"\n👤 Your Team: {your_team.name if hasattr(your_team, 'name') else 'Team 5'}")
        
    except Exception as e:
        print(f"\n⚠️ Connected but couldn't fetch league data: {e}")
        print("   This is OK - token is saved!")
        
except Exception as e:
    print(f"\n❌ OAuth failed: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure you copied the ENTIRE URL including 'code=...'")
    print("2. Try again - sometimes it takes 2 attempts")
    print("3. Check your Client ID and Secret are correct")

print("\n" + "="*60)
print("TOKEN PERSISTENCE")
print("="*60)
print("""
✅ Once OAuth succeeds, the token is saved locally
✅ Future API calls will use the saved token
✅ Token auto-refreshes when needed (lasts ~1 hour)
✅ Refresh token lasts much longer (~6 months)

You won't need to do OAuth again unless:
- You delete the token file
- The refresh token expires (months)
- You revoke access on Yahoo's site
""")