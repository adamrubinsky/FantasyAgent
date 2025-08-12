#!/usr/bin/env python3
"""
Test Yahoo Fantasy API Connection
This script tests if we can connect to Yahoo Fantasy and access league data
"""

import os
import json
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

def test_yahoo_oauth():
    """Test Yahoo OAuth flow"""
    
    print("\n" + "="*60)
    print("YAHOO FANTASY API CONNECTION TEST")
    print("="*60)
    
    # Load credentials
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    
    app_id = os.getenv('YAHOO_APP_ID')
    client_id = os.getenv('YAHOO_CLIENT_ID')
    client_secret = os.getenv('YAHOO_CLIENT_SECRET')
    redirect_uri = os.getenv('YAHOO_REDIRECT_URI')
    
    print(f"\n✅ Found Yahoo credentials:")
    print(f"   App ID: {app_id}")
    print(f"   Client ID: {client_id[:20]}...")
    print(f"   Redirect URI: {redirect_uri}")
    
    # Check if yfpy is installed
    try:
        from yfpy import Data
        from yfpy.query import YahooFantasySportsQuery
        print("\n✅ yfpy library is installed")
        can_use_yfpy = True
    except ImportError:
        print("\n⚠️ yfpy not installed. Let's install it:")
        print("   Run: pip install yfpy")
        can_use_yfpy = False
    
    if not can_use_yfpy:
        print("\n" + "-"*60)
        print("ALTERNATIVE: Manual OAuth Test")
        print("-"*60)
        
        # Build OAuth URL manually
        base_url = "https://api.login.yahoo.com/oauth2/request_auth"
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'language': 'en-us'
        }
        
        auth_url = f"{base_url}?{urlencode(params)}"
        
        print("\nTo test Yahoo OAuth manually:")
        print("1. Open this URL in your browser:")
        print(f"\n   {auth_url}\n")
        print("2. Log in with your Yahoo account")
        print("3. Authorize the FantasyAgent app")
        print("4. You'll be redirected to:")
        print(f"   {redirect_uri}?code=AUTHORIZATION_CODE")
        print("5. Copy the authorization code from the URL")
        
        print("\n⚠️ Note: You'll see a connection error since localhost:3000")
        print("   isn't running with HTTPS. That's OK - just copy the code from the URL.")
        
        # Offer to open browser
        open_browser = input("\nOpen browser to test OAuth? (y/n): ")
        if open_browser.lower() == 'y':
            webbrowser.open(auth_url)
            print("\n✅ Opened browser for OAuth test")
            
            auth_code = input("\nPaste the authorization code here (or press Enter to skip): ")
            if auth_code:
                print(f"\n✅ Got auth code: {auth_code[:10]}...")
                print("\nNext step would be to exchange this code for an access token")
                print("But we need a running server to handle that properly")
        
        return False
    
    # Try using yfpy
    print("\n" + "-"*60)
    print("Testing with yfpy library")
    print("-"*60)
    
    # Create auth directory
    auth_dir = Path("auth")
    auth_dir.mkdir(exist_ok=True)
    
    try:
        print("\n🔄 Initializing Yahoo Fantasy connection...")
        print("   NOTE: This will open a browser for OAuth authorization")
        print("   After authorizing, you'll see a connection error - that's OK!")
        print("   Copy the URL and paste it back here when prompted.")
        
        # Initialize without league_id first
        yahoo_query = YahooFantasySportsQuery(
            auth_dir=auth_dir,
            league_id=None,  # Will get leagues first
            game_code="nfl",
            game_id=449,  # 2025 NFL season
            yahoo_consumer_key=client_id,
            yahoo_consumer_secret=client_secret,
            env_file_location=Path(".env.local")
        )
        
        print("\n✅ Yahoo connection successful!")
        
        # Try to get user info
        user_info = yahoo_query.get_current_user()
        print(f"\nConnected as: {user_info}")
        
        return True
        
    except Exception as e:
        print(f"\n⚠️ Error: {e}")
        
        if "token" in str(e).lower():
            print("\n💡 Token issue detected. Try:")
            print("1. Delete the 'auth' folder and retry")
            print("2. Make sure to paste the FULL redirect URL when prompted")
            
        return False


def test_yahoo_mock_connection():
    """Test Yahoo connection with mock data if real connection fails"""
    
    print("\n" + "-"*60)
    print("MOCK YAHOO DATA TEST")
    print("-"*60)
    
    print("\nSince we can't connect yet, here's what we'd get from Yahoo:")
    
    mock_leagues = [
        {
            "name": "Yahoo Snake Draft League",
            "league_id": "423.l.123456",
            "draft_date": "2025-08-19",
            "draft_type": "snake",
            "teams": 12,
            "scoring": "half_ppr"
        },
        {
            "name": "Yahoo Auction League", 
            "league_id": "423.l.789012",
            "draft_date": "2025-08-24",
            "draft_type": "auction",
            "teams": 12,
            "budget": 200,
            "scoring": "ppr"
        }
    ]
    
    print("\n📋 Your Yahoo Leagues (mock data):")
    for league in mock_leagues:
        print(f"\n   {league['name']}:")
        print(f"   - Draft: {league['draft_date']}")
        print(f"   - Type: {league['draft_type'].upper()}")
        print(f"   - Teams: {league['teams']}")
        print(f"   - Scoring: {league['scoring'].upper()}")
        if league['draft_type'] == 'auction':
            print(f"   - Budget: ${league['budget']}")
    
    print("\n🎯 What we need to build:")
    print("1. OAuth handler for Yahoo authentication")
    print("2. League detection from Yahoo API")
    print("3. Draft monitoring (polling every 5-10 seconds)")
    print("4. Snake draft agent (similar to Sleeper)")
    print("5. Auction draft agent (completely different logic)")


if __name__ == "__main__":
    print("YAHOO FANTASY CONNECTION TEST")
    print("Testing your Yahoo API setup...")
    
    # Try real connection
    success = test_yahoo_oauth()
    
    if not success:
        print("\n" + "="*60)
        print("Real connection not working yet. Testing with mock data...")
        test_yahoo_mock_connection()
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    
    if success:
        print("✅ Yahoo OAuth is working!")
        print("\n1. We can now fetch your actual leagues")
        print("2. Build draft monitoring for Aug 19 snake draft")
        print("3. Create auction logic for Aug 24 draft")
    else:
        print("⚠️ Yahoo OAuth needs setup")
        print("\n1. Install yfpy: pip install yfpy")
        print("2. Set up OAuth handler in our web server")
        print("3. Then we can access your Yahoo leagues")
        
    print("\n📅 Your Draft Schedule:")
    print("- Aug 14: Sleeper SUPERFLEX (3 days) ← Current focus")
    print("- Aug 19: Yahoo Snake (8 days)")
    print("- Aug 24: Yahoo Auction (13 days)")
    print("\nRecommendation: Focus on Sleeper first, then add Yahoo support")