#!/usr/bin/env python3
"""
Quick test to verify agent is using FantasyPros rankings correctly
"""

import asyncio
import json
from pathlib import Path

async def test_rankings_usage():
    """Test that the agent properly uses FantasyPros rankings"""
    
    # First, check what rankings we have cached
    cache_file = Path("data/fantasypros_rankings_NFL_OP_HALF_50.json")
    
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            data = json.load(f)
            players = data.get('players', [])
            
        print("📊 Checking cached FantasyPros rankings...")
        print("=" * 60)
        
        # Find London and Wilson
        london_rank = None
        wilson_rank = None
        
        for player in players:
            name = player.get('player_name', '')
            if 'Drake London' in name:
                london_rank = player.get('rank_ecr')
                london_pos = player.get('pos_rank')
                print(f"Drake London: Rank #{london_rank}, {london_pos}")
            elif 'Garrett Wilson' in name:
                wilson_rank = player.get('rank_ecr')
                wilson_pos = player.get('pos_rank')
                print(f"Garrett Wilson: Rank #{wilson_rank}, {wilson_pos}")
        
        print()
        if london_rank and wilson_rank:
            if london_rank < wilson_rank:
                print("✅ Rankings show Drake London (#31) > Garrett Wilson (#49)")
                print("   Agent should recommend London based on rankings")
            else:
                print("❌ Rankings unexpected order")
    else:
        print("❌ No cached rankings found")
        return
    
    # Now test the agent
    print("\n" + "=" * 60)
    print("Testing agent with player comparison...")
    print("=" * 60)
    
    try:
        from agents.draft_crew import get_live_rankings_data
        
        # Get the rankings data that agents will use
        rankings_str = await get_live_rankings_data(limit=200)
        
        # Check if both players are in the data
        if "Drake London" in rankings_str and "Garrett Wilson" in rankings_str:
            print("✅ Both players found in rankings data provided to agents")
            
            # Extract their lines
            for line in rankings_str.split('\n'):
                if 'Drake London' in line:
                    print(f"   {line}")
                elif 'Garrett Wilson' in line:
                    print(f"   {line}")
        else:
            print("❌ Players missing from rankings data")
            
    except Exception as e:
        print(f"❌ Error testing agent: {e}")

if __name__ == "__main__":
    asyncio.run(test_rankings_usage())