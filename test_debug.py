#!/usr/bin/env python3
"""
Quick debug test to see what's happening with draft monitoring
"""

import asyncio
import os
from api.sleeper_client import SleeperClient
from core.draft_monitor import DraftMonitor
from dotenv import load_dotenv

load_dotenv('.env.local')

async def test_draft_monitoring():
    """Test what happens when we try to initialize draft monitoring"""
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    print(f"Testing with username: {username}")
    print(f"Testing with league_id: {league_id}")
    
    if not username or not league_id:
        print("❌ Missing username or league_id in .env.local")
        return
    
    # Test SleeperClient first
    print("\n🔍 Testing SleeperClient...")
    try:
        async with SleeperClient(username, league_id) as client:
            # Test basic user info
            user_info = await client.get_user()
            print(f"✅ User info: {user_info.get('display_name', 'Unknown')} (ID: {user_info.get('user_id', 'Unknown')})")
            
            # Test league info
            try:
                league_info = await client.get_league_info()
                print(f"✅ League info: {league_info.get('name', 'Unknown')} (Draft ID: {league_info.get('draft_id', 'None')})")
                
                draft_id = league_info.get('draft_id')
                if draft_id:
                    # Test draft info
                    draft_info = await client.get_draft_info(draft_id)
                    print(f"✅ Draft status: {draft_info.get('status', 'unknown')}")
                    
                    # Test draft picks
                    picks = await client.get_draft_picks(draft_id)
                    print(f"✅ Draft picks found: {len(picks)}")
                    
                    if picks:
                        print("First few picks:")
                        for i, pick in enumerate(picks[:3]):
                            print(f"  Pick {pick.get('pick_no', '?')}: Player {pick.get('player_id', 'Unknown')} to Roster {pick.get('roster_id', '?')}")
                else:
                    print("⚠️ No draft_id found - might be a completed league")
                    
            except Exception as e:
                print(f"⚠️ League/draft error: {e}")
                
    except Exception as e:
        print(f"❌ SleeperClient error: {e}")
        return
    
    # Test DraftMonitor
    print("\n🔍 Testing DraftMonitor...")
    try:
        async with DraftMonitor(username, league_id) as monitor:
            success = await monitor.initialize_draft()
            if success:
                print(f"✅ Draft monitor initialized successfully")
                print(f"   Draft ID: {monitor.draft_id}")
                print(f"   User roster ID: {monitor.user_roster_id}")
                print(f"   Current pick: {monitor.current_pick}")
                print(f"   Total picks: {monitor.total_picks}")
                print(f"   Picks made: {len(monitor.picks_history)}")
            else:
                print("❌ Draft monitor failed to initialize")
                
    except Exception as e:
        print(f"❌ DraftMonitor error: {e}")

if __name__ == "__main__":
    asyncio.run(test_draft_monitoring())