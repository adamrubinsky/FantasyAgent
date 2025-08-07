#!/usr/bin/env python3
"""
Debug roster ID assignment
"""

import asyncio
import os
from api.sleeper_client import SleeperClient
from dotenv import load_dotenv

load_dotenv('.env.local')

async def debug_roster():
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    async with SleeperClient(username, league_id) as client:
        # Get user info
        user_info = await client.get_user()
        user_id = user_info.get('user_id')
        print(f"User: {user_info.get('display_name')} (ID: {user_id})")
        
        # Get league rosters to find correct roster_id
        try:
            rosters = await client.get_league_rosters()
            print(f"\nFound {len(rosters)} rosters:")
            for roster in rosters:
                owner_id = roster.get('owner_id')
                roster_id = roster.get('roster_id')
                print(f"  Roster {roster_id}: Owner {owner_id} {'<-- YOU' if owner_id == user_id else ''}")
                
        except Exception as e:
            print(f"Could not get rosters: {e}")
        
        # Get league info and check draft
        league_info = await client.get_league_info()
        draft_id = league_info.get('draft_id')
        print(f"\nLeague: {league_info.get('name')}")
        print(f"Draft ID: {draft_id}")
        
        if draft_id:
            # Get draft info
            draft_info = await client.get_draft_info(draft_id)
            draft_order = draft_info.get('draft_order', {})
            print(f"\nDraft order: {draft_order}")
            
            # Get picks and see what roster_ids are in them
            picks = await client.get_draft_picks(draft_id)
            roster_ids_with_picks = set(pick.get('roster_id') for pick in picks if pick.get('roster_id'))
            print(f"\nRoster IDs with picks: {sorted(roster_ids_with_picks)}")
            
            # Show a few sample picks
            print(f"\nFirst 5 picks:")
            for pick in picks[:5]:
                print(f"  Pick {pick.get('pick_no', '?')}: Player {pick.get('player_id', '?')} to Roster {pick.get('roster_id', '?')}")

if __name__ == "__main__":
    asyncio.run(debug_roster())