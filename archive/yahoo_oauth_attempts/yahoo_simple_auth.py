#!/usr/bin/env python3
"""
Simplified Yahoo OAuth - Just follow the prompts
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

print("\n" + "="*60)
print("YAHOO OAUTH - SIMPLE METHOD")
print("="*60)

# Create directories
os.makedirs('private', exist_ok=True)
os.makedirs('auth', exist_ok=True)

client_id = os.getenv('YAHOO_CLIENT_ID')
client_secret = os.getenv('YAHOO_CLIENT_SECRET')

print(f"\n📋 Your OAuth App Details:")
print(f"   Client ID: {client_id[:30]}...")
print(f"   Client Secret: {client_secret[:10]}...")

# Save credentials for yfpy
auth_dir = Path('private')
auth_dir.mkdir(exist_ok=True)

print("\n" + "="*60)
print("METHOD 1: Try Automatic")
print("="*60)

try:
    from yfpy import Data
    from yfpy.query import YahooFantasySportsQuery
    
    # Set up the Yahoo query with minimal config
    yahoo_query = YahooFantasySportsQuery(
        auth_dir=auth_dir,
        league_id='475629',
        game_id=449,  # 2025 NFL
        game_code='nfl',
        offline=False,
        all_output_as_json=False,
        consumer_key=client_id,
        consumer_secret=client_secret,
        browser_callback=True
    )
    
    print("✅ yfpy configured")
    print("\n🌐 Browser should open for authorization...")
    print("After authorizing, paste the FULL URL when prompted")
    print("\nIf successful, token will be saved to: private/")
    
    # This will trigger the OAuth flow
    league = yahoo_query.get_league_metadata()
    print(f"\n✅ SUCCESS! Connected to league: {league.league_id}")
    
except Exception as e:
    print(f"\n⚠️ Method 1 failed: {e}")
    
    print("\n" + "="*60)
    print("METHOD 2: Manual Token Save")
    print("="*60)
    print("""
The authorization is failing at the token exchange step.
This might be because:

1. The Yahoo app settings need adjustment
2. The redirect URI isn't exactly matching
3. The codes are expiring too fast

Let's try a different approach:

1. Go to: https://developer.yahoo.com/apps/
2. Click on your app (FantasyAgent)
3. Verify these settings:
   - Redirect URI: https://localhost:3000/auth/yahoo/callback
   - API Permissions: Fantasy Sports Read

4. Try using the Yahoo Fantasy app directly:
   - Go to: https://football.fantasysports.yahoo.com/
   - Your leagues should be there
   - We can scrape the data if needed

For now, let's focus on your Sleeper draft (in 3 days).
We can revisit Yahoo OAuth closer to Aug 19.
""")