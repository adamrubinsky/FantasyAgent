#!/usr/bin/env python3
"""Test script to see what draft data we're getting"""

import asyncio
import json
from core.draft_monitor import draft_monitor

async def test_draft_data():
    # Get draft status
    status = await draft_monitor.get_draft_status("yahoo-snake")
    
    if status.get("status") == "success":
        print("=== DRAFT STATUS ===")
        draft_status = status.get("draftStatus", {})
        print(f"Current Pick: {draft_status.get('currentPick')}")
        print(f"Round: {draft_status.get('round')}")
        print(f"My Turn: {draft_status.get('myTurn')}")
        print(f"User Slot: {draft_status.get('userSlot')}")
        
        print("\n=== MY ROSTER ===")
        my_roster = status.get("myRoster", [])
        print(f"Total players on roster: {len(my_roster)}")
        for i, player in enumerate(my_roster, 1):
            print(f"{i}. {player}")
        
        print("\n=== FORMATTED ROSTER (for UI) ===")
        roster = status.get("roster", [])
        for i, player in enumerate(roster, 1):
            print(f"{i}. {player}")
            
        print("\n=== RECENT PICKS ===")
        recent = status.get("recentPicks", [])
        for pick in recent:
            print(f"Pick #{pick.get('pick')}: {pick.get('player')} (Team {pick.get('team')})")
            
        print("\n=== ALL PICKS (first 5) ===")
        all_picks = status.get("allPicks", [])
        for pick in all_picks[:5]:
            print(f"Pick #{pick.get('pick')}: {pick.get('player')} (Team {pick.get('team')})")
    else:
        print(f"Error: {status}")

if __name__ == "__main__":
    asyncio.run(test_draft_data())