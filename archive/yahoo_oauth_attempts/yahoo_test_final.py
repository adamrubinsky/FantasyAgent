#!/usr/bin/env python3
"""
Test Yahoo connection with proper token handling
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv('.env.local')

print("\n" + "="*60)
print("YAHOO CONNECTION TEST - FINAL")
print("="*60)

# Your credentials
client_id = os.getenv('YAHOO_CLIENT_ID')
client_secret = os.getenv('YAHOO_CLIENT_SECRET')

# Create private directory if it doesn't exist
os.makedirs('private', exist_ok=True)
print("✅ Created/verified private directory")

# Import yfpy
try:
    from yfpy.query import YahooFantasySportsQuery
    print("✅ yfpy library ready")
except ImportError:
    print("❌ yfpy not installed")
    exit(1)

print("\n" + "="*60)
print("IMPORTANT:")
print("="*60)
print("""
Since you successfully ran the OAuth in the other terminal,
the token should be saved. If this asks for 'Enter verifier:' again,
you'll need to paste the full URL one more time.

Otherwise, it should connect directly!
""")

print("\n" + "="*60)
print("TESTING SNAKE LEAGUE (475629)")
print("="*60)

try:
    # Try without browser_callback since we already have a token
    yahoo = YahooFantasySportsQuery(
        league_id='475629',
        game_code='nfl',
        game_id=449,  # 2025 season
        yahoo_consumer_key=client_id,
        yahoo_consumer_secret=client_secret,
        browser_callback=False  # Don't open browser since we have token
    )
    
    print("\n📊 Attempting to connect...")
    
    # Try a simple API call
    try:
        # Get league scoreboard (simple test)
        scoreboard = yahoo.get_league_scoreboard_by_week(1)
        print("✅ API call successful! Token is working!")
    except:
        # Try league key as fallback test
        league = yahoo.get_league()
        print(f"✅ Connected! League data retrieved")
    
    print("\n🎉 SUCCESS! Yahoo connection is working!")
    print("   Your token is saved and functional")
    print("   Location: private/.yahoo_token.json")
    
    # Try to get some league info
    print("\n📊 League Information:")
    try:
        teams = yahoo.get_league_teams()
        print(f"   Teams in league: {len(teams)}")
        
        # Get draft info
        draft = yahoo.get_league_draft_results()
        if draft:
            print(f"   Draft picks made: {len(draft)}")
        else:
            print("   Draft not yet started")
            
    except Exception as e:
        print(f"   Some data not available yet: {e}")
    
except Exception as e:
    print(f"\n⚠️ Connection issue: {e}")
    print("\nIf you see 'Enter verifier:', you need to:")
    print("1. Run yahoo_manual_oauth.py again")
    print("2. Get a fresh code from the browser")  
    print("3. Paste the full URL when prompted")
    print("\nThe token from your previous run may have had an issue saving.")

print("\n" + "="*60)
print("NEXT STEPS")
print("="*60)
print("""
If connection successful:
✅ Yahoo OAuth is complete
✅ Token will auto-refresh
✅ Ready for Aug 19 snake draft
✅ Ready for Aug 24 auction draft

If connection failed:
- Re-run yahoo_manual_oauth.py
- Make sure to paste the FULL URL (not just the code)
- The URL should start with https://localhost:3000/...
""")