#!/usr/bin/env python3
"""
Test Yahoo Draft Integration
Verifies that draft data flows correctly to the agent
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_yahoo_integration():
    """Test the full Yahoo draft data flow"""
    
    print("\n" + "="*60)
    print("YAHOO DRAFT INTEGRATION TEST")
    print("="*60)
    
    base_url = "http://localhost:3001"
    
    async with aiohttp.ClientSession() as session:
        # 1. Select Yahoo platform
        print("\n1. Selecting Yahoo Snake platform...")
        async with session.post(f"{base_url}/api/select-platform", 
                               json={"platform": "yahoo-snake"}) as resp:
            result = await resp.json()
            print(f"   Platform selection: {result.get('status')}")
        
        # 2. Connect to mock draft (you'll need to provide a URL)
        print("\n2. Attempting to connect to Yahoo draft...")
        print("   Enter Yahoo draft URL (or 'skip' to test without connection):")
        draft_url = input("   > ").strip()
        
        if draft_url and draft_url != 'skip':
            print("   Enter your draft slot (1-10):")
            draft_slot = int(input("   > ").strip())
            
            async with session.post(f"{base_url}/api/connect-draft",
                                   json={
                                       "platform": "yahoo-snake",
                                       "url": draft_url,
                                       "draft_slot": draft_slot
                                   }) as resp:
                result = await resp.json()
                print(f"   Connection result: {result}")
                
                if result.get("status") == "success":
                    print(f"   ✓ Connected to draft ID: {result.get('draft_id')}")
                else:
                    print(f"   ✗ Failed to connect: {result.get('message')}")
        
        # 3. Get draft status to see what data we have
        print("\n3. Fetching draft status...")
        async with session.post(f"{base_url}/api/draft-status",
                               json={"platform": "yahoo-snake"}) as resp:
            status = await resp.json()
            
            if status.get("status") == "success":
                draft_data = status.get("draftStatus", {})
                print(f"   Current Pick: {draft_data.get('currentPick', 'N/A')}")
                print(f"   Round: {draft_data.get('round', 'N/A')}")
                print(f"   Your Slot: {draft_data.get('userSlot', 'N/A')}")
                print(f"   Your Turn: {draft_data.get('myTurn', False)}")
                
                # Check if we got any picks
                all_picks = status.get("allPicks", [])
                print(f"   Total Picks Found: {len(all_picks)}")
                if all_picks:
                    print(f"   Recent picks:")
                    for pick in all_picks[-3:]:
                        print(f"     - Pick {pick.get('pick')}: {pick.get('player', 'Unknown')}")
                
                roster = status.get("roster", [])
                print(f"   Your Roster: {len(roster)} players")
                for player in roster:
                    print(f"     - {player.get('name', 'Unknown')} ({player.get('position', '??')})")
            else:
                print(f"   Failed to get status: {status.get('message')}")
                draft_data = {}
        
        # 4. Test agent query with context
        print("\n4. Testing agent with draft context...")
        
        # Build context that would come from draft monitor
        test_context = {
            "current_pick": draft_data.get("currentPick", 25),
            "current_round": draft_data.get("round", 3),
            "draft_slot": draft_data.get("userSlot", 5),
            "my_turn": draft_data.get("myTurn", False),
            "roster": status.get("roster", []),
            "my_roster": status.get("roster", [])
        }
        
        print(f"\n   Context being sent to agent:")
        print(f"   - Current Pick: {test_context['current_pick']}")
        print(f"   - Round: {test_context['current_round']}")
        print(f"   - Draft Slot: {test_context['draft_slot']}")
        print(f"   - Roster Size: {len(test_context['roster'])}")
        
        # Test different queries
        test_queries = [
            "Who should I draft?",
            "Best available RB?",
            "When is my next pick?"
        ]
        
        for query in test_queries:
            print(f"\n   Query: '{query}'")
            
            start = datetime.now()
            async with session.post(f"{base_url}/api/draft-query",
                                   json={
                                       "platform": "yahoo-snake",
                                       "query": query,
                                       "context": test_context
                                   }) as resp:
                result = await resp.json()
                elapsed = int((datetime.now() - start).total_seconds() * 1000)
                
                if result.get("status") == "success":
                    response = result.get("response", "No response")
                    # Show first 200 chars of response
                    if len(response) > 200:
                        print(f"   Response: {response[:200]}...")
                    else:
                        print(f"   Response: {response}")
                    print(f"   Time: {elapsed}ms")
                else:
                    print(f"   Error: {result.get('message')}")
        
        # 5. Check if agent is using real data
        print("\n5. Verification checks:")
        
        # Check if rankings are accessible
        async with session.get(f"{base_url}/api/rankings/yahoo-snake") as resp:
            rankings = await resp.json()
            print(f"   ✓ Rankings available: {len(rankings)} players")
            if rankings:
                print(f"     Top 3: {[p.get('player_name', 'Unknown') for p in rankings[:3]]}")
        
        # Check available players (filters out drafted)
        async with session.get(f"{base_url}/api/available-players/yahoo-snake") as resp:
            result = await resp.json()
            available = result.get("available", [])
            drafted_count = result.get("totalDrafted", 0)
            print(f"   ✓ Available players: {len(available)} (Drafted: {drafted_count})")
            
        print("\n" + "="*60)
        print("SUMMARY:")
        print("="*60)
        
        # Determine if integration is working
        issues = []
        
        if not draft_data:
            issues.append("❌ No draft data received")
        elif draft_data.get("currentPick", 0) == 1 and len(all_picks) == 0:
            issues.append("⚠️  Mock draft may not have started")
        
        if len(rankings) == 0:
            issues.append("❌ No rankings data available")
            
        if drafted_count == 0 and draft_data.get("currentPick", 1) > 1:
            issues.append("⚠️  Drafted players not being tracked")
        
        if issues:
            print("Issues found:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("✅ Integration appears to be working!")
            print("   - Draft data is flowing to agent")
            print("   - Rankings are available")
            print("   - Agent is responding with context")
        
        print("\nNOTE: For best results, test with an active mock draft")
        print("      where picks have been made.")

if __name__ == "__main__":
    print("\nMake sure the server is running (python3 unified_server.py)")
    input("Press Enter when ready...")
    asyncio.run(test_yahoo_integration())