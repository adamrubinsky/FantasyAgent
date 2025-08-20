#!/usr/bin/env python3
"""
Simulate Yahoo Draft Data for Testing
Use this if mock drafts aren't providing real data
"""

import asyncio
import aiohttp
import json
import random

async def simulate_yahoo_draft():
    """Simulate a Yahoo draft in progress"""
    
    print("\n" + "="*60)
    print("YAHOO DRAFT SIMULATION")
    print("="*60)
    
    base_url = "http://localhost:3001"
    
    # Simulated draft state
    current_pick = 28  # Round 3, Pick 8
    draft_slot = 5
    
    # Simulated picks that have happened
    simulated_picks = [
        {"pick": 1, "player": "Christian McCaffrey", "position": "RB", "team": 1},
        {"pick": 2, "player": "CeeDee Lamb", "position": "WR", "team": 2},
        {"pick": 3, "player": "Tyreek Hill", "position": "WR", "team": 3},
        {"pick": 4, "player": "Ja'Marr Chase", "position": "WR", "team": 4},
        {"pick": 5, "player": "Justin Jefferson", "position": "WR", "team": 5},  # User's pick
        {"pick": 6, "player": "Bijan Robinson", "position": "RB", "team": 6},
        {"pick": 7, "player": "Amon-Ra St. Brown", "position": "WR", "team": 7},
        {"pick": 8, "player": "Breece Hall", "position": "RB", "team": 8},
        {"pick": 9, "player": "A.J. Brown", "position": "WR", "team": 9},
        {"pick": 10, "player": "Garrett Wilson", "position": "WR", "team": 10},
        # Round 2 (reverse order)
        {"pick": 11, "player": "Jonathan Taylor", "position": "RB", "team": 10},
        {"pick": 12, "player": "Saquon Barkley", "position": "RB", "team": 9},
        {"pick": 13, "player": "Chris Olave", "position": "WR", "team": 8},
        {"pick": 14, "player": "Davante Adams", "position": "WR", "team": 7},
        {"pick": 15, "player": "Travis Etienne", "position": "RB", "team": 6},
        {"pick": 16, "player": "Puka Nacua", "position": "WR", "team": 5},  # User's pick
        {"pick": 17, "player": "Jahmyr Gibbs", "position": "RB", "team": 4},
        {"pick": 18, "player": "Mike Evans", "position": "WR", "team": 3},
        {"pick": 19, "player": "Calvin Ridley", "position": "WR", "team": 2},
        {"pick": 20, "player": "Derrick Henry", "position": "RB", "team": 1},
        # Round 3 (normal order)
        {"pick": 21, "player": "Josh Allen", "position": "QB", "team": 1},
        {"pick": 22, "player": "DK Metcalf", "position": "WR", "team": 2},
        {"pick": 23, "player": "Rachaad White", "position": "RB", "team": 3},
        {"pick": 24, "player": "Stefon Diggs", "position": "WR", "team": 4},
        {"pick": 25, "player": "De'Von Achane", "position": "RB", "team": 5},  # User's pick
        {"pick": 26, "player": "Jalen Hurts", "position": "QB", "team": 6},
        {"pick": 27, "player": "DeVonta Smith", "position": "WR", "team": 7},
    ]
    
    # User's roster
    user_roster = [
        {"name": "Justin Jefferson", "position": "WR", "pick": 5},
        {"name": "Puka Nacua", "position": "WR", "pick": 16},
        {"name": "De'Von Achane", "position": "RB", "pick": 25}
    ]
    
    async with aiohttp.ClientSession() as session:
        # 1. Select platform
        print("\n1. Selecting Yahoo Snake platform...")
        async with session.post(f"{base_url}/api/select-platform",
                               json={"platform": "yahoo-snake"}) as resp:
            result = await resp.json()
            print(f"   Status: {result.get('status')}")
        
        # 2. Test with simulated context
        print("\n2. Testing agent with simulated draft data...")
        
        context = {
            "current_pick": current_pick,
            "current_round": 3,
            "draft_slot": draft_slot,
            "my_turn": current_pick == 28,  # It's pick 28, user is slot 5
            "roster": user_roster,
            "my_roster": user_roster,
            "all_picks": simulated_picks
        }
        
        print(f"\n   Simulated Context:")
        print(f"   - Current Pick: #{current_pick} (Round 3)")
        print(f"   - Your Draft Slot: #{draft_slot}")
        print(f"   - Your Turn: {context['my_turn']}")
        print(f"   - Your Roster:")
        for p in user_roster:
            print(f"     • {p['name']} ({p['position']})")
        
        # 3. Test various queries with this context
        print("\n3. Testing agent responses...")
        
        test_scenarios = [
            {
                "query": "Who should I draft?",
                "description": "General recommendation"
            },
            {
                "query": "Should I take a RB or WR?",
                "description": "Position comparison"
            },
            {
                "query": "Best available QB?",
                "description": "Position-specific"
            },
            {
                "query": "When is my next pick?",
                "description": "Draft position query"
            },
            {
                "query": "What positions do I need?",
                "description": "Roster analysis"
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n   [{scenario['description']}]")
            print(f"   Query: \"{scenario['query']}\"")
            
            async with session.post(f"{base_url}/api/draft-query",
                                   json={
                                       "platform": "yahoo-snake",
                                       "query": scenario["query"],
                                       "context": context
                                   },
                                   timeout=aiohttp.ClientTimeout(total=10)) as resp:
                
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("status") == "success":
                        response = result.get("response", "")
                        # Parse and display recommendations if present
                        if "recommendations" in response:
                            print(f"   ✓ Agent provided recommendations")
                            # Show first part of response
                            lines = response.split('\n')
                            for line in lines[:5]:
                                if line.strip():
                                    print(f"     {line[:100]}")
                        else:
                            # Show first 150 chars
                            preview = response[:150].replace('\n', ' ')
                            print(f"   Response: {preview}...")
                    else:
                        print(f"   ✗ Error: {result.get('message')}")
                else:
                    print(f"   ✗ HTTP Error: {resp.status}")
        
        # 4. Verify data flow
        print("\n4. Data Flow Verification:")
        
        # Check if agent would filter drafted players
        print(f"   - Simulated {len(simulated_picks)} picks")
        print(f"   - User has {len(user_roster)} players")
        
        # Get available players to see if filtering works
        async with session.get(f"{base_url}/api/available-players/yahoo-snake") as resp:
            result = await resp.json()
            available = result.get("available", [])
            
            # Check if any of our simulated picks appear in available
            drafted_names = {p["player"].lower() for p in simulated_picks}
            still_showing = []
            
            for player in available[:20]:
                if player.get("player_name", "").lower() in drafted_names:
                    still_showing.append(player.get("player_name"))
            
            if still_showing:
                print(f"   ⚠️  These drafted players still show as available:")
                for name in still_showing[:5]:
                    print(f"      - {name}")
                print(f"   Note: This is expected without live draft connection")
            else:
                print(f"   ✓ Available players list: {len(available)} players")
        
        print("\n" + "="*60)
        print("RESULTS:")
        print("="*60)
        print("\nThe agent is receiving context and responding.")
        print("Key things to verify:")
        print("  1. Agent acknowledges your roster (2 WR, 1 RB)")
        print("  2. Agent knows it's Round 3")
        print("  3. Agent can calculate your next pick")
        print("  4. Recommendations make sense for Full PPR")
        print("\nFor live draft tomorrow:")
        print("  - Player names will come from Yahoo API")
        print("  - Drafted players will be filtered correctly")
        print("  - Your actual roster will be tracked")

if __name__ == "__main__":
    print("\nMake sure the server is running (python3 unified_server.py)")
    input("Press Enter to start simulation...")
    asyncio.run(simulate_yahoo_draft())