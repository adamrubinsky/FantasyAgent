#!/usr/bin/env python3
"""
Test yfpy OAuth connection to Yahoo Fantasy
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

print("\n" + "="*60)
print("YAHOO FANTASY YFPY CONNECTION TEST")
print("="*60)

# Check if yfpy works
try:
    from yfpy import Data
    from yfpy.query import YahooFantasySportsQuery
    print("✅ yfpy library imported successfully")
except ImportError as e:
    print(f"❌ Failed to import yfpy: {e}")
    exit(1)

# Get credentials
client_id = os.getenv('YAHOO_CLIENT_ID')
client_secret = os.getenv('YAHOO_CLIENT_SECRET')
snake_league_id = os.getenv('YAHOO_SNAKE_LEAGUE_ID', '475629')
auction_league_id = os.getenv('YAHOO_AUCTION_LEAGUE_ID', '682492')

print(f"\n📋 Configuration:")
print(f"   Client ID: {client_id[:20]}...")
print(f"   Snake League: {snake_league_id}")
print(f"   Auction League: {auction_league_id}")

# Create auth directory
auth_dir = Path("auth")
auth_dir.mkdir(exist_ok=True)

print("\n" + "-"*60)
print("OAUTH SETUP INSTRUCTIONS")
print("-"*60)

print("""
To connect to Yahoo, yfpy will:
1. Open your browser to Yahoo login
2. Ask you to authorize the FantasyAgent app
3. Redirect to https://localhost:3000/auth/yahoo/callback
4. You'll see a connection error (that's OK!)
5. Copy the ENTIRE URL from your browser
6. Paste it back here when prompted

This only needs to be done once - yfpy saves the token.
""")

# Try to initialize for snake league
print("\n🏈 Attempting connection to Snake League...")
try:
    yahoo_query = YahooFantasySportsQuery(
        auth_dir=auth_dir,
        league_id=snake_league_id,
        game_code="nfl",
        game_id=449,  # 2025 NFL season
        yahoo_consumer_key=client_id,
        yahoo_consumer_secret=client_secret,
        env_file_location=Path(".env.local"),
        save_token_data_to_env_file=True
    )
    
    print("\n✅ Yahoo connection initialized!")
    
    # Try to get league info
    print("\n📊 Fetching league information...")
    try:
        # Get league metadata
        league = yahoo_query.get_league_metadata()
        print(f"\n✅ Connected to: {league.name}")
        print(f"   Teams: {league.num_teams}")
        print(f"   Draft Status: {league.draft_status}")
        
        # Get your team
        team = yahoo_query.get_team_metadata()
        print(f"\n👤 Your Team: {team.name}")
        print(f"   Team ID: {team.team_id}")
        
    except Exception as e:
        print(f"\n⚠️ Could not fetch league data: {e}")
        print("   This is normal on first run - need to complete OAuth first")
    
except Exception as e:
    print(f"\n❌ Connection failed: {e}")
    print("\nCommon issues:")
    print("1. Need to complete OAuth flow first")
    print("2. Token expired - delete 'auth' folder and retry")
    print("3. Wrong credentials in .env.local")

print("\n" + "="*60)
print("NEXT STEPS")
print("="*60)

print("""
If OAuth worked:
✅ You now have access to your Yahoo leagues!
✅ Token is saved in 'auth' folder for future use
✅ We can monitor drafts and get live data

If it didn't work:
1. Make sure you copied the ENTIRE redirect URL
2. Try deleting the 'auth' folder and retry
3. Check that your Client ID and Secret are correct

For your drafts:
- Aug 14: Sleeper SUPERFLEX (ready to go!)
- Aug 19: Yahoo Snake (needs OAuth completion)
- Aug 24: Yahoo Auction (needs OAuth completion)
""")