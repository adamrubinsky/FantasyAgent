#!/usr/bin/env python3
"""Quick test of data retrieval for live draft"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.mcp_integration import MCPClient
from core.official_fantasypros import OfficialFantasyProsMCP

async def test_data():
    print("Testing data retrieval...")
    
    # Test 1: Direct FantasyPros API
    print("\n1. Testing direct FantasyPros API...")
    fp_client = OfficialFantasyProsMCP()
    if await fp_client.is_server_available():
        rankings = await fp_client.get_rankings(position="QB", limit=5)
        if rankings:
            print("✅ FantasyPros API working!")
            players = rankings.get('players', [])
            for p in players[:3]:
                print(f"  - {p.get('name', 'Unknown')} - Rank: {p.get('rank', 'N/A')}")
        else:
            print("❌ No data returned from FantasyPros API")
    else:
        print("❌ FantasyPros API not available")
    
    # Test 2: MCP Client
    print("\n2. Testing MCP Client...")
    try:
        async with MCPClient() as mcp:
            rankings = await mcp.get_rankings(limit=5)
            if rankings:
                print("✅ MCP Client working!")
                if isinstance(rankings, dict) and 'players' in rankings:
                    for p in rankings['players'][:3]:
                        print(f"  - {p.get('name', 'Unknown')}")
            else:
                print("❌ No data from MCP Client")
    except Exception as e:
        print(f"❌ MCP Client error: {e}")
    
    # Test 3: Search for specific players
    print("\n3. Testing player search...")
    test_players = ["Joe Burrow", "Jalen Hurts"]
    try:
        async with MCPClient() as mcp:
            projections = await mcp.get_projections(test_players)
            if projections and 'players' in projections:
                print("✅ Player projections working!")
                for name, data in projections['players'].items():
                    print(f"  - {name}: {data.get('fantasy_points', 'N/A')} points")
            else:
                print("❌ No projections found")
    except Exception as e:
        print(f"❌ Projections error: {e}")

if __name__ == "__main__":
    asyncio.run(test_data())