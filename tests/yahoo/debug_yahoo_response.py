#!/usr/bin/env python3
"""
Debug Yahoo API response to understand the data structure
"""

import asyncio
import aiohttp
import json
from pathlib import Path

async def debug_yahoo():
    # Load token
    token_file = Path('private/yahoo_token.json')
    with open(token_file, 'r') as f:
        token_data = json.load(f)
    
    access_token = token_data['access_token']
    league_id = "1246753"
    
    # Get draft results
    draft_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/nfl.l.{league_id}/draftresults"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/xml'
    }
    
    print("Fetching draft results...")
    
    # Disable SSL for macOS
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(draft_url, headers=headers) as resp:
            print(f"Status: {resp.status}")
            
            if resp.status == 200:
                content = await resp.text()
                
                # Save full response
                with open("yahoo_draft_response.xml", "w") as f:
                    f.write(content)
                print(f"Saved full response ({len(content)} bytes) to yahoo_draft_response.xml")
                
                # Try to find draft results
                import re
                
                # Look for any draft-related tags
                draft_tags = ['draft_result', 'pick', 'player', 'team', 'round']
                for tag in draft_tags:
                    pattern = f'<{tag}>'
                    count = len(re.findall(pattern, content))
                    if count > 0:
                        print(f"Found {count} <{tag}> tags")
                
                # Try to extract first few picks
                print("\nLooking for picks...")
                
                # Pattern 1: draft_result blocks
                picks_pattern = r'<draft_result>(.*?)</draft_result>'
                picks = re.findall(picks_pattern, content, re.DOTALL)
                
                if picks:
                    print(f"\nFound {len(picks)} draft_result entries!")
                    for i, pick in enumerate(picks[:3]):  # Show first 3
                        print(f"\nPick {i+1} raw XML:")
                        print(pick[:500])  # First 500 chars
                else:
                    print("No draft_result tags found")
                    
                    # Try alternative patterns
                    # Look for player names with context
                    player_pattern = r'<player_key>.*?</player_key>.*?<name>(.*?)</name>'
                    players = re.findall(player_pattern, content, re.DOTALL)[:10]
                    
                    if players:
                        print(f"\nFound {len(players)} players:")
                        for p in players[:5]:
                            print(f"  - {p}")
            else:
                error = await resp.text()
                print(f"Error: {error[:500]}")

if __name__ == "__main__":
    asyncio.run(debug_yahoo())