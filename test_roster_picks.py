#!/usr/bin/env python3
"""
Test user roster picks
"""

import asyncio
import os
from api.sleeper_client import SleeperClient
from core.draft_monitor import DraftMonitor
from dotenv import load_dotenv

load_dotenv('.env.local')

async def test_roster_picks():
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    async with DraftMonitor(username, league_id) as monitor:
        await monitor.initialize_draft()
        
        # Get picks
        picks = await monitor.client.get_draft_picks(monitor.draft_id)
        print(f"Total picks: {len(picks)}")
        print(f"User roster ID: {monitor.user_roster_id}")
        
        # Filter user picks
        user_picks = [pick for pick in picks if pick.get('roster_id') == monitor.user_roster_id]
        print(f"User picks: {len(user_picks)}")
        
        # Show user picks
        if user_picks:
            players = await monitor.client.get_all_players()
            print("\nUser's picks:")
            for pick in user_picks:
                player_id = pick.get('player_id')
                if player_id and player_id in players:
                    player = players[player_id]
                    name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
                    positions = "/".join(player.get('fantasy_positions', []))
                    team = player.get('team', 'FA')
                    print(f"  Pick {pick.get('pick_no', '?')}: {name} ({positions}) - {team}")
                else:
                    print(f"  Pick {pick.get('pick_no', '?')}: Player {player_id} (not found)")
        else:
            print("No picks found for user")

if __name__ == "__main__":
    asyncio.run(test_roster_picks())