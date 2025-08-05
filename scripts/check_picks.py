#!/usr/bin/env python3
"""
Quick script to examine the existing draft picks in detail
"""

import asyncio
import os
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.sleeper_client import SleeperClient
from dotenv import load_dotenv

# Load environment
load_dotenv('.env.local')
load_dotenv()


async def check_existing_picks():
    """Check what picks have already been made"""
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    async with SleeperClient(username=username, league_id=league_id) as client:
        # Get league and draft info
        league = await client.get_league_info()
        draft_id = league.get('draft_id')
        
        print(f"League: {league.get('name')}")
        print(f"Draft ID: {draft_id}")
        print(f"League Status: {league.get('status')}")
        print()
        
        # Get draft details
        draft_info = await client.get_draft_info(draft_id)
        print(f"Draft Status: {draft_info.get('status')}")
        print(f"Draft Type: {draft_info.get('type')}")
        print(f"Start Time: {draft_info.get('start_time', 'Not set')}")
        print()
        
        # Get existing picks
        picks = await client.get_draft_picks(draft_id)
        print(f"Total picks made: {len(picks)}")
        
        if picks:
            print("\nExisting picks:")
            players = await client.get_all_players()
            
            for pick in picks[:20]:  # Show first 20
                player_id = pick.get('player_id')
                if player_id and player_id in players:
                    player = players[player_id]
                    name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
                    team = player.get('team', 'FA')
                    pos = "/".join(player.get('fantasy_positions', []))
                    
                    print(f"  Pick #{pick.get('pick_no')}: {name} ({pos}) - {team}")
                    print(f"    Round: {pick.get('round')}, Roster ID: {pick.get('roster_id')}")
                    print(f"    Metadata: {pick.get('metadata', {})}")
                else:
                    print(f"  Pick #{pick.get('pick_no')}: Empty or invalid player")
                print()


if __name__ == "__main__":
    asyncio.run(check_existing_picks())