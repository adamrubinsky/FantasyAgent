#!/usr/bin/env python3
"""
Check the actual current draft status
"""

import asyncio
import aiohttp
import json
from pathlib import Path

async def check_draft():
    # Load token
    token_file = Path('private/yahoo_token.json')
    with open(token_file, 'r') as f:
        token_data = json.load(f)
    
    access_token = token_data['access_token']
    league_id = "1246753"
    
    # Try different endpoints
    endpoints = [
        f"https://fantasysports.yahooapis.com/fantasy/v2/league/nfl.l.{league_id}",
        f"https://fantasysports.yahooapis.com/fantasy/v2/league/nfl.l.{league_id}/teams",
        f"https://fantasysports.yahooapis.com/fantasy/v2/league/nfl.l.{league_id}/draftresults",
        f"https://fantasysports.yahooapis.com/fantasy/v2/league/nfl.l.{league_id}/transactions"
    ]
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/xml'
    }
    
    print("Checking draft status...")
    
    # Disable SSL for macOS
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for endpoint in endpoints:
            print(f"\n{'='*60}")
            print(f"Endpoint: {endpoint.split('/')[-1]}")
            print('='*60)
            
            async with session.get(endpoint, headers=headers) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    
                    # Look for draft status indicators
                    import re
                    
                    # Check draft status
                    draft_status = re.search(r'<draft_status>(.*?)</draft_status>', content)
                    if draft_status:
                        print(f"Draft Status: {draft_status.group(1)}")
                    
                    # Check if draft is live
                    is_draft_live = re.search(r'<is_draft_live>(\d)</is_draft_live>', content)
                    if is_draft_live:
                        print(f"Is Draft Live: {'Yes' if is_draft_live.group(1) == '1' else 'No'}")
                    
                    # Count draft results
                    draft_results = re.findall(r'<draft_result>', content)
                    if draft_results:
                        print(f"Draft Results Count: {len(draft_results)}")
                        
                        # Get the last pick number
                        picks = re.findall(r'<pick>(\d+)</pick>', content)
                        if picks:
                            last_pick = max(int(p) for p in picks)
                            print(f"Last Pick Number: {last_pick}")
                            print(f"Current Round: {(last_pick - 1) // 10 + 1}")
                            print(f"Next Pick: {last_pick + 1}")
                    
                    # Check for live draft info
                    if 'draftclient' in content or 'draft_client' in content:
                        print("Found draft client reference")
                    
                    # Look for team rosters
                    team_pattern = r'<team_key>461\.l\.1246753\.t\.1</team_key>'
                    team_matches = re.findall(team_pattern, content)
                    if team_matches:
                        print(f"Found Team 1 (your team) {len(team_matches)} times")
                    
                    # Save the league response for inspection
                    if 'league' in endpoint and 'draftresults' not in endpoint:
                        with open("league_status.xml", "w") as f:
                            f.write(content[:10000])
                        print("Saved league status to league_status.xml")
                    
                    # Check for mock draft indicator
                    if 'mock' in content.lower():
                        print("⚠️  This is a MOCK draft")
                else:
                    print(f"Status: {resp.status}")
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    print("""
    The draft results endpoint shows historical data from completed drafts.
    For live draft data, we need to check different endpoints or use the 
    draft client URL directly.
    """)

if __name__ == "__main__":
    asyncio.run(check_draft())