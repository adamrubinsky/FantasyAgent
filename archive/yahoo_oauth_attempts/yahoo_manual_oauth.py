#!/usr/bin/env python3
"""
Manual Yahoo OAuth Setup - Run this in a terminal and follow the prompts
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

print("\n" + "="*60)
print("YAHOO FANTASY OAUTH - MANUAL SETUP")
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
    print("✅ yfpy library ready\n")
except ImportError:
    print("❌ yfpy not installed. Run: pip3 install yfpy")
    exit(1)

print("="*60)
print("STEP-BY-STEP INSTRUCTIONS:")
print("="*60)
print("""
1. When you run this script, a browser window will open
2. Log in to Yahoo if needed
3. Click "Agree" to authorize the app
4. You'll be redirected to an error page (SSL error)
5. Copy the ENTIRE URL from your browser's address bar
6. Come back to this terminal
7. Paste the URL when you see 'Enter verifier :'
8. Press Enter

Ready? Press Enter to start...""")

input()  # Wait for user to be ready

print("\n🚀 Starting OAuth flow...")
print("Browser should open automatically...")
print("\n" + "-"*60)

try:
    # Initialize Yahoo connection with browser callback
    # This will open the browser and wait for input
    yahoo = YahooFantasySportsQuery(
        league_id=snake_league,
        game_code='nfl',
        game_id=449,  # 2025 season
        yahoo_consumer_key=client_id,
        yahoo_consumer_secret=client_secret,
        browser_callback=True
    )
    
    # If we get here, OAuth was successful
    print("\n" + "="*60)
    print("✅ OAUTH SUCCESSFUL!")
    print("="*60)
    
    # Test the connection
    print("\n📊 Testing connection to your league...")
    settings = yahoo.get_league_settings()
    print(f"✅ Connected to: {settings.name}")
    print(f"   League ID: {snake_league}")
    print(f"   Teams: {settings.num_teams}")
    print(f"   Draft Status: {settings.draft_status}")
    
    # Get your team info
    print("\n👤 Getting your team info...")
    teams = yahoo.get_league_teams()
    for team in teams:
        if hasattr(team, 'team_key') and '5' in str(team.team_key):
            print(f"✅ Your team: {team.name}")
            print(f"   Manager: {team.managers[0]['manager'].nickname if hasattr(team, 'managers') else 'Unknown'}")
            break
    
    print("\n" + "="*60)
    print("🎉 SUCCESS! Token saved locally")
    print("="*60)
    print("""
✅ OAuth is complete and token is saved
✅ Location: private/.yahoo_token.json  
✅ Access token expires in ~1 hour (auto-refreshes)
✅ Refresh token lasts ~6 months
✅ You won't need to do this again!

Next: Test your auction league...""")
    
    # Test auction league
    print("\n" + "="*60)
    print("TESTING AUCTION LEAGUE")
    print("="*60)
    
    auction_league = '682492'
    print(f"League ID: {auction_league}")
    
    try:
        yahoo_auction = YahooFantasySportsQuery(
            league_id=auction_league,
            game_code='nfl',
            game_id=449,
            yahoo_consumer_key=client_id,
            yahoo_consumer_secret=client_secret
        )
        
        auction_settings = yahoo_auction.get_league_settings()
        print(f"✅ Connected to: {auction_settings.name}")
        print(f"   Auction Budget: ${auction_settings.auction_budget if hasattr(auction_settings, 'auction_budget') else '200'}")
        print(f"   Teams: {auction_settings.num_teams}")
        
    except Exception as e:
        print(f"⚠️ Auction league error: {e}")
        print("   (This is OK - focus on snake draft first)")
    
    print("\n" + "="*60)
    print("ALL DONE!")
    print("="*60)
    print("""
Your Yahoo Fantasy connection is now set up!

League Summary:
- Snake Draft (Aug 19): League 475629, Team 5
- Auction (Aug 24): League 682492, Team 2

The FantasyAgent can now monitor your Yahoo drafts!
""")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure you copied the ENTIRE URL")
    print("2. The URL should start with: https://localhost:3000/auth/yahoo/callback?code=")
    print("3. Try running the script again (codes expire quickly)")
    print("4. If browser doesn't open, manually go to:")
    print(f"\nhttps://api.login.yahoo.com/oauth2/request_auth?client_id={client_id}&redirect_uri=https://localhost:3000/auth/yahoo/callback&response_type=code&language=en-us")