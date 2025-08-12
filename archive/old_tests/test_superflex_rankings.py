#!/usr/bin/env python3
"""Test FantasyPros OP (SUPERFLEX) rankings integration"""

import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append('.')

from core.official_fantasypros import OfficialFantasyProsMCP

async def test_superflex_rankings():
    """Test that FantasyPros OP rankings are working correctly for SUPERFLEX"""
    
    # Load environment variables
    load_dotenv('.env.local')
    api_key = os.getenv('FANTASYPROS_API_KEY')
    
    if not api_key:
        print("❌ FANTASYPROS_API_KEY not found in .env.local")
        return
    
    print("=" * 60)
    print("Testing FantasyPros SUPERFLEX (OP) Rankings")
    print("=" * 60)
    
    client = OfficialFantasyProsMCP(api_key)
    
    # Test 1: Get SUPERFLEX rankings explicitly
    print("\n1. Testing explicit SUPERFLEX rankings (position='OP')...")
    rankings = await client.get_rankings(
        sport="NFL",
        position="OP",  # This is the key for SUPERFLEX!
        scoring="HALF",
        limit=200  # Get more players for better analysis
    )
    
    if rankings:
        print(f"✅ Successfully fetched {len(rankings)} players with OP rankings")
        
        # Check top 10 players
        print("\nTop 10 SUPERFLEX Rankings:")
        print("-" * 40)
        for i, player in enumerate(rankings[:10], 1):
            name = player.get('player_name', 'Unknown')
            pos = player.get('player_position_id', 'N/A')
            team = player.get('player_team_id', 'N/A')
            rank = player.get('rank_ecr', 'N/A')
            print(f"{i:2}. {name:20} {pos:3} {team:3} (Rank: {rank})")
        
        # Verify QBs are properly valued (should dominate top 5)
        top_5_positions = [p.get('player_position_id', '') for p in rankings[:5]]
        qb_count = top_5_positions.count('QB')
        
        print(f"\n📊 Top 5 Analysis:")
        print(f"   - QBs in top 5: {qb_count}/5")
        if qb_count >= 4:
            print("   ✅ SUPERFLEX rankings confirmed! QBs properly valued")
        else:
            print("   ⚠️  Warning: Expected more QBs in top 5 for SUPERFLEX")
        
        # Find Tyreek Hill to verify he's around #47
        tyreek = next((p for p in rankings if 'Tyreek' in p.get('player_name', '')), None)
        if tyreek:
            tyreek_rank = tyreek.get('rank_ecr', 'N/A')
            print(f"\n🏈 Tyreek Hill Check:")
            print(f"   - Rank: #{tyreek_rank}")
            if isinstance(tyreek_rank, (int, float)) and 40 <= tyreek_rank <= 55:
                print(f"   ✅ Correct SUPERFLEX ranking (expected ~#47)")
            else:
                print(f"   ⚠️  Unexpected ranking (expected ~#47)")
    else:
        print("❌ Failed to fetch rankings")
    
    # Test 2: Verify default behavior (should also use OP)
    print("\n2. Testing default rankings (no position specified)...")
    default_rankings = await client.get_rankings(
        sport="NFL",
        scoring="HALF",
        limit=200
        # No position specified - should default to OP
    )
    
    if default_rankings:
        print(f"✅ Default fetched {len(default_rankings)} players")
        
        # Check if it matches SUPERFLEX
        if len(default_rankings) == len(rankings):
            first_match = default_rankings[0].get('player_name') == rankings[0].get('player_name')
            if first_match:
                print("   ✅ Default correctly uses SUPERFLEX (OP) rankings")
            else:
                print("   ⚠️  Default rankings don't match SUPERFLEX")
    
    # Test 3: Compare with standard rankings (position='ALL')
    print("\n3. Testing standard rankings for comparison (position='ALL')...")
    standard_rankings = await client.get_rankings(
        sport="NFL",
        position="ALL",  # Standard rankings
        scoring="HALF",
        limit=200
    )
    
    if standard_rankings:
        print(f"✅ Standard fetched {len(standard_rankings)} players")
        
        # Check top 5 for comparison
        print("\nTop 5 Standard Rankings (for comparison):")
        print("-" * 40)
        for i, player in enumerate(standard_rankings[:5], 1):
            name = player.get('player_name', 'Unknown')
            pos = player.get('player_position_id', 'N/A')
            print(f"{i:2}. {name:20} {pos:3}")
        
        # Compare QB presence
        std_top_5_positions = [p.get('player_position_id', '') for p in standard_rankings[:5]]
        std_qb_count = std_top_5_positions.count('QB')
        print(f"\n   - QBs in standard top 5: {std_qb_count}/5")
        print(f"   - Difference: SUPERFLEX has {qb_count - std_qb_count} more QBs in top 5")
    
    print("\n" + "=" * 60)
    print("SUPERFLEX Rankings Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_superflex_rankings())