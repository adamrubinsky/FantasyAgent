#!/usr/bin/env python3
"""
Debug Yahoo Fantasy API access
Test different endpoints to see what works
"""

import asyncio
import aiohttp
import json
from pathlib import Path

async def test_yahoo_api():
    # Load token
    token_file = Path('private/yahoo_token.json')
    with open(token_file, 'r') as f:
        token_data = json.load(f)
    
    access_token = token_data['access_token']
    
    # League ID from your URL
    league_id = "1246753"
    
    # Different endpoint formats to try
    endpoints = [
        # Current year NFL season is game_key 449
        f"https://fantasysports.yahooapis.com/fantasy/v2/league/449.l.{league_id}",
        f"https://fantasysports.yahooapis.com/fantasy/v2/league/nfl.l.{league_id}",
        f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_id}",
        
        # Try with game keys
        f"https://fantasysports.yahooapis.com/fantasy/v2/game/449/leagues;league_keys=449.l.{league_id}",
        f"https://fantasysports.yahooapis.com/fantasy/v2/game/nfl",
        
        # User's leagues
        "https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games;game_keys=nfl/leagues",
        "https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/teams",
        
        # Try draft endpoints
        f"https://fantasysports.yahooapis.com/fantasy/v2/league/449.l.{league_id}/draftresults",
        f"https://fantasysports.yahooapis.com/fantasy/v2/league/449.l.{league_id}/teams",
    ]
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/xml',
        'Content-Type': 'application/xml'
    }
    
    print("=" * 70)
    print("YAHOO API ENDPOINT TESTING")
    print("=" * 70)
    print(f"League ID: {league_id}")
    print(f"Token: {access_token[:30]}...")
    print("-" * 70)
    
    # Disable SSL for macOS
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for endpoint in endpoints:
            print(f"\n📍 Testing: {endpoint}")
            
            try:
                async with session.get(endpoint, headers=headers) as resp:
                    print(f"   Status: {resp.status}")
                    
                    if resp.status == 200:
                        content = await resp.text()
                        print(f"   ✅ SUCCESS! Response length: {len(content)}")
                        
                        # Check if it's a mock draft
                        if "mock" in content.lower():
                            print("   ⚠️  This appears to be a MOCK draft")
                        
                        # Look for league name
                        import re
                        name_match = re.search(r'<name>(.*?)</name>', content)
                        if name_match:
                            print(f"   League Name: {name_match.group(1)}")
                        
                        # Look for draft status
                        if "draft_status" in content:
                            status_match = re.search(r'<draft_status>(.*?)</draft_status>', content)
                            if status_match:
                                print(f"   Draft Status: {status_match.group(1)}")
                        
                        # Save successful response for analysis
                        if "league" in endpoint and resp.status == 200:
                            with open(f"yahoo_response_{league_id}.xml", "w") as f:
                                f.write(content[:5000])  # Save first 5000 chars
                            print(f"   💾 Saved response to yahoo_response_{league_id}.xml")
                    
                    elif resp.status == 401:
                        print("   ❌ 401 Unauthorized - Token may be expired")
                    
                    elif resp.status == 403:
                        print("   ❌ 403 Forbidden - No access to this resource")
                        error_content = await resp.text()
                        if "Mock" in error_content or "mock" in error_content:
                            print("   ℹ️  Mock drafts may have different access rules")
                    
                    elif resp.status == 404:
                        print("   ❌ 404 Not Found - Wrong endpoint format")
                    
                    else:
                        print(f"   ⚠️  Unexpected status: {resp.status}")
                        
            except Exception as e:
                print(f"   💥 Error: {e}")
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS:")
    print("-" * 70)
    print("""
    If all endpoints return 403:
    - Mock drafts may not be accessible via API
    - Try with a real league URL instead
    - The token may not have draft permissions
    
    If some work:
    - Use the working endpoint format
    - Check the saved XML file for data structure
    """)

if __name__ == "__main__":
    asyncio.run(test_yahoo_api())