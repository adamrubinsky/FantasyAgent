#!/usr/bin/env python3
"""
Basic Yahoo Fantasy Connection Test
Tests if we can connect to your specific Yahoo leagues
"""

import os
import json
import requests
from datetime import datetime

def test_yahoo_basic():
    """Test basic Yahoo connection without full OAuth"""
    
    print("\n" + "="*60)
    print("YAHOO FANTASY BASIC CONNECTION TEST")
    print("="*60)
    
    # Load your league info
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    
    # Your Yahoo leagues
    snake_league_id = os.getenv('YAHOO_SNAKE_LEAGUE_ID', '475629')
    snake_team_id = os.getenv('YAHOO_SNAKE_TEAM_ID', '5')
    
    auction_league_id = os.getenv('YAHOO_AUCTION_LEAGUE_ID', '682492')
    auction_team_id = os.getenv('YAHOO_AUCTION_TEAM_ID', '2')
    
    print("\n📋 Your Yahoo Leagues:")
    print(f"\n1. Snake Draft League (Aug 19):")
    print(f"   - League ID: {snake_league_id}")
    print(f"   - Your Team: #{snake_team_id}")
    print(f"   - URL: https://football.fantasysports.yahoo.com/f1/{snake_league_id}/{snake_team_id}")
    
    print(f"\n2. Auction League (Aug 24):")
    print(f"   - League ID: {auction_league_id}")
    print(f"   - Your Team: #{auction_team_id}")
    print(f"   - URL: https://football.fantasysports.yahoo.com/f1/{auction_league_id}/{auction_team_id}")
    
    # Test if we can at least reach Yahoo
    print("\n" + "-"*60)
    print("Testing Yahoo API endpoints...")
    print("-"*60)
    
    # Yahoo API base URL
    base_url = "https://fantasysports.yahooapis.com/fantasy/v2"
    
    # These endpoints require OAuth, but let's see what happens
    test_endpoints = [
        f"/league/nfl.l.{snake_league_id}",  # Snake league
        f"/league/nfl.l.{auction_league_id}", # Auction league
    ]
    
    for endpoint in test_endpoints:
        url = base_url + endpoint
        print(f"\n🔍 Testing: {url}")
        
        try:
            # This will fail without OAuth, but shows the endpoint format
            response = requests.get(url, timeout=5)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 401:
                print("   ❌ 401: Need OAuth authentication (expected)")
            elif response.status_code == 200:
                print("   ✅ 200: Somehow accessible!")
            else:
                print(f"   ⚠️ {response.status_code}: {response.reason}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}")
    
    return True

def test_yahoo_public_data():
    """Test what Yahoo data is publicly available"""
    
    print("\n" + "-"*60)
    print("Testing Public Yahoo Data")
    print("-"*60)
    
    # Some Yahoo endpoints don't require auth
    public_tests = [
        {
            "name": "NFL Game ID (2025 season)",
            "url": "https://fantasysports.yahooapis.com/fantasy/v2/game/nfl",
            "note": "Game 449 = 2025 NFL season"
        }
    ]
    
    for test in public_tests:
        print(f"\n📊 {test['name']}:")
        print(f"   URL: {test['url']}")
        print(f"   Note: {test['note']}")
        
        try:
            response = requests.get(test['url'], timeout=5)
            print(f"   Status: {response.status_code}")
        except Exception as e:
            print(f"   Error: {str(e)[:50]}")

def install_yfpy_instructions():
    """Show how to install and use yfpy"""
    
    print("\n" + "="*60)
    print("NEXT STEP: Install yfpy Library")
    print("="*60)
    
    print("""
To actually connect to your Yahoo leagues, run:

1. Install the library:
   pip install yfpy

2. Then we can use this code:

```python
from yfpy.query import YahooFantasySportsQuery

# For your snake league
yahoo_query = YahooFantasySportsQuery(
    league_id=475629,
    game_code='nfl',
    game_id=449,  # 2025 season
    yahoo_consumer_key=CLIENT_ID,
    yahoo_consumer_secret=CLIENT_SECRET
)

# This will open browser for OAuth on first run
league_info = yahoo_query.get_league_metadata()
print(f"League: {league_info.name}")
print(f"Draft Date: {league_info.draft_date}")
```

The library handles all OAuth complexity!
""")

def show_yahoo_vs_sleeper():
    """Compare Yahoo and Sleeper APIs"""
    
    print("\n" + "="*60)
    print("YAHOO vs SLEEPER API COMPARISON")
    print("="*60)
    
    comparison = """
    | Feature         | Sleeper        | Yahoo           |
    |-----------------|----------------|-----------------|
    | Authentication  | None (Public)  | OAuth Required  |
    | Rate Limit      | 1000/min       | 60/min          |
    | Draft Monitoring| WebSocket      | Polling         |
    | Player IDs      | Unique         | Different       |
    | Setup Time      | 5 minutes      | 30+ minutes     |
    | Documentation   | Excellent      | Complex         |
    """
    
    print(comparison)
    
    print("\nYour Leagues Status:")
    print("✅ Sleeper SUPERFLEX: Ready for Aug 14 draft")
    print("⚠️ Yahoo Snake: Need OAuth for Aug 19 draft")
    print("⚠️ Yahoo Auction: Need OAuth for Aug 24 draft")

if __name__ == "__main__":
    print("TESTING YAHOO FANTASY CONNECTION")
    print("Testing with your actual league IDs...")
    
    # Test basic connection
    test_yahoo_basic()
    
    # Test public endpoints
    test_yahoo_public_data()
    
    # Show next steps
    install_yfpy_instructions()
    
    # Compare to Sleeper
    show_yahoo_vs_sleeper()
    
    print("\n" + "="*60)
    print("RECOMMENDATION")
    print("="*60)
    print("""
Since your Sleeper draft is in 3 days (Aug 14), I recommend:

1. Focus on Sleeper optimization for now
2. After Aug 14, install yfpy and set up Yahoo OAuth
3. You'll have 5 days before Yahoo Snake draft (Aug 19)
4. That's plenty of time to adapt the system

Quick setup when ready:
pip install yfpy
python test_yahoo_connection.py
""")
    
    # Show your actual league URLs
    print("\n📌 Your League URLs (bookmark these):")
    print("Sleeper: https://sleeper.com/draft/nfl/1221322229137031168")
    print("Yahoo Snake: https://football.fantasysports.yahoo.com/f1/475629/5")
    print("Yahoo Auction: https://football.fantasysports.yahoo.com/f1/682492/2")