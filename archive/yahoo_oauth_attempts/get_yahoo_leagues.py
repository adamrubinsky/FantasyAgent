#!/usr/bin/env python3
"""
Get Yahoo Fantasy League Information
This script will help us get your actual Yahoo league details
"""

import os
import webbrowser
from urllib.parse import urlencode

print("\n" + "="*60)
print("YAHOO LEAGUE INFORMATION SETUP")
print("="*60)

print("""
To connect to your Yahoo leagues, we need to:

1. First install the Yahoo library:
   pip install yfpy

2. Authorize the app to access your Yahoo account

3. The app will then fetch:
   - Your league IDs
   - League settings (scoring, roster, etc.)
   - Your team in each league
   - Draft dates and times

Without this, we can't monitor your Yahoo drafts!
""")

# Load credentials
from dotenv import load_dotenv
load_dotenv('.env.local')

client_id = os.getenv('YAHOO_CLIENT_ID')
redirect_uri = os.getenv('YAHOO_REDIRECT_URI')

# Build OAuth URL
base_url = "https://api.login.yahoo.com/oauth2/request_auth"
params = {
    'client_id': client_id,
    'redirect_uri': redirect_uri,
    'response_type': 'code',
    'language': 'en-us'
}

auth_url = f"{base_url}?{urlencode(params)}"

print("\n" + "-"*60)
print("MANUAL LEAGUE SETUP (if OAuth isn't working)")
print("-"*60)

print("""
If you know your Yahoo league details, we can add them manually:

For your SNAKE DRAFT league (Aug 19):
- League URL: (looks like: https://football.fantasysports.yahoo.com/f1/123456)
- League ID: (the number after /f1/)
- Your team number: (1-12)
- Scoring type: (standard, PPR, or half-PPR)

For your AUCTION league (Aug 24):  
- League URL: (same format)
- League ID: (the number)
- Your team number: (1-12)
- Budget: ($200 standard)
- Scoring type: (standard, PPR, or half-PPR)
""")

print("\n" + "="*60)
print("OAUTH URL for Yahoo Authorization:")
print("="*60)
print("\nCopy this URL to your browser:")
print(f"\n{auth_url}\n")

print("After authorizing, you'll be redirected to:")
print(f"{redirect_uri}?code=AUTH_CODE")
print("\nThe page won't load (that's OK!) - just copy the AUTH_CODE from the URL")

print("\n" + "="*60)
print("ALTERNATIVE: Manual Configuration")  
print("="*60)

print("""
You can also manually add your league info to .env.local:

# Yahoo Snake Draft League (Aug 19)
YAHOO_SNAKE_LEAGUE_ID=your-league-id-here
YAHOO_SNAKE_LEAGUE_URL=https://football.fantasysports.yahoo.com/f1/YOUR_ID
YAHOO_SNAKE_TEAM_ID=your-team-number
YAHOO_SNAKE_SCORING=half_ppr

# Yahoo Auction League (Aug 24)
YAHOO_AUCTION_LEAGUE_ID=your-league-id-here
YAHOO_AUCTION_LEAGUE_URL=https://football.fantasysports.yahoo.com/f1/YOUR_ID
YAHOO_AUCTION_TEAM_ID=your-team-number
YAHOO_AUCTION_BUDGET=200
YAHOO_AUCTION_SCORING=ppr
""")

# Try to open the browser
open_browser = input("\n🌐 Open browser to authorize Yahoo? (y/n): ").strip().lower()
if open_browser == 'y':
    webbrowser.open(auth_url)
    print("\n✅ Opened browser for Yahoo authorization")
    print("\nAfter authorizing, you'll need to:")
    print("1. Copy the authorization code from the redirect URL")
    print("2. We'll use it to get an access token")
    print("3. Then fetch your actual league information")
else:
    print("\n📝 Please provide your Yahoo league information manually")
    
    # Collect league info manually
    print("\n" + "-"*40)
    print("SNAKE DRAFT LEAGUE (Aug 19):")
    snake_url = input("League URL (or press Enter to skip): ").strip()
    if snake_url:
        # Extract league ID from URL
        if "/f1/" in snake_url:
            league_id = snake_url.split("/f1/")[1].split("/")[0].split("?")[0]
            print(f"Extracted League ID: {league_id}")
            
            team_num = input("Your team number (1-12): ").strip()
            scoring = input("Scoring (standard/ppr/half_ppr): ").strip().lower()
            
            print(f"""
Add to .env.local:
YAHOO_SNAKE_LEAGUE_ID={league_id}
YAHOO_SNAKE_TEAM_ID={team_num}
YAHOO_SNAKE_SCORING={scoring}
""")
    
    print("\n" + "-"*40)
    print("AUCTION LEAGUE (Aug 24):")
    auction_url = input("League URL (or press Enter to skip): ").strip()
    if auction_url:
        # Extract league ID from URL
        if "/f1/" in auction_url:
            league_id = auction_url.split("/f1/")[1].split("/")[0].split("?")[0]
            print(f"Extracted League ID: {league_id}")
            
            team_num = input("Your team number (1-12): ").strip()
            budget = input("Auction budget (default 200): ").strip() or "200"
            scoring = input("Scoring (standard/ppr/half_ppr): ").strip().lower()
            
            print(f"""
Add to .env.local:
YAHOO_AUCTION_LEAGUE_ID={league_id}
YAHOO_AUCTION_TEAM_ID={team_num}
YAHOO_AUCTION_BUDGET={budget}
YAHOO_AUCTION_SCORING={scoring}
""")

print("\n" + "="*60)
print("NEXT STEPS:")
print("="*60)
print("""
1. Install yfpy library: pip install yfpy
2. Add your league IDs to .env.local
3. Run the OAuth flow to get access token
4. Then we can monitor your Yahoo drafts!

For now, focus on your Sleeper draft (Aug 14)
We'll set up Yahoo monitoring after that's done.
""")