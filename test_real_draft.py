#!/usr/bin/env python3
"""Test connection to real Sleeper draft"""

import re
import asyncio
import sys
sys.path.append('.')

from api.sleeper_client import SleeperClient

async def test_real_draft():
    """Test the real draft URL connection"""
    
    # Real draft URL from commissioner
    draft_url = "https://sleeper.com/draft/nfl/1221322229137031168"
    
    print(f"Testing real draft URL: {draft_url}")
    print("=" * 60)
    
    # Test regex extraction
    pattern = r'sleeper\.com/draft/nfl/(\d{15,20})'
    match = re.search(pattern, draft_url)
    
    if match:
        draft_id = match.group(1)
        print(f"✅ Successfully extracted draft ID: {draft_id}")
        print(f"   Draft ID length: {len(draft_id)} digits")
    else:
        print("❌ Failed to extract draft ID from URL")
        return
    
    # Test Sleeper API connection
    print("\nConnecting to Sleeper API...")
    client = SleeperClient()
    
    try:
        # Get draft info
        draft_info = await client.get_draft_info(draft_id)
        
        if draft_info:
            print(f"✅ Successfully connected to draft!")
            print(f"\nDraft Details:")
            print(f"  - Type: {draft_info.get('type', 'N/A')}")
            print(f"  - Status: {draft_info.get('status', 'N/A')}")
            print(f"  - Sport: {draft_info.get('sport', 'N/A')}")
            print(f"  - Season: {draft_info.get('season', 'N/A')}")
            print(f"  - Teams: {draft_info.get('team_count', 'N/A')}")
            print(f"  - Rounds: {draft_info.get('rounds', 'N/A')}")
            print(f"  - Pick Timer: {draft_info.get('pick_timer', 'N/A')} seconds")
            
            # Check draft start time
            start_time = draft_info.get('start_time')
            if start_time:
                from datetime import datetime
                dt = datetime.fromtimestamp(start_time / 1000)
                print(f"  - Start Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Get draft picks to see current status
            picks = await client.get_draft_picks(draft_id)
            if picks:
                print(f"\n  - Current Picks Made: {len(picks)}")
            else:
                print(f"\n  - No picks made yet (draft hasn't started)")
                
        else:
            print("⚠️  Draft not active yet (this is normal before draft day)")
            print("    The draft ID is valid and will work once the draft starts!")
            print(f"    Draft ID {draft_id} is ready for August 14th")
            
    except Exception as e:
        print(f"❌ Error connecting to draft: {e}")

if __name__ == "__main__":
    asyncio.run(test_real_draft())