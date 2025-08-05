#!/usr/bin/env python3
"""
Example: League-Specific Rankings Comparison
Shows how rankings change based on different league settings
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.league_context import LeagueSettings, LeagueContextManager
from core.mcp_integration import MCPClient


async def compare_league_formats():
    """Compare rankings across different league formats"""
    
    # Define different league types
    leagues = [
        LeagueSettings(
            league_id="standard_league",
            platform="sleeper",
            league_name="Standard 12-Team PPR",
            total_teams=12,
            scoring_format="ppr",
            roster_positions=["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF"],
            superflex_spots=0
        ),
        LeagueSettings(
            league_id="superflex_league", 
            platform="sleeper",
            league_name="SUPERFLEX 12-Team Half-PPR",
            total_teams=12,
            scoring_format="half_ppr",
            roster_positions=["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "SUPER_FLEX", "K", "DEF"],
            superflex_spots=1
        ),
        LeagueSettings(
            league_id="2qb_league",
            platform="sleeper", 
            league_name="2QB 10-Team Standard",
            total_teams=10,
            scoring_format="standard",
            roster_positions=["QB", "QB", "RB", "RB", "WR", "WR", "TE", "FLEX"],
            starting_qbs=2,
            superflex_spots=0
        )
    ]
    
    print("🏈 Fantasy League Rankings Comparison")
    print("=" * 60)
    
    manager = LeagueContextManager()
    
    for league in leagues:
        print(f"\n📊 {league.league_name}")
        print(f"   Format: {league.scoring_format.upper()}")
        print(f"   Teams: {league.total_teams}")
        print(f"   QB spots: {league.total_qb_spots}")
        print(f"   SUPERFLEX: {'YES' if league.is_superflex else 'NO'}")
        
        # Calculate position scarcity
        scarcity = league.get_position_scarcity()
        print(f"   Position Values: QB({scarcity['QB']:.2f}) RB({scarcity['RB']:.2f}) WR({scarcity['WR']:.2f}) TE({scarcity['TE']:.2f})")
        
        # Set as current context
        manager.current_context = league
        
        # Get QB rankings
        async with MCPClient() as mcp:
            rankings = await mcp.get_rankings(position="QB", limit=5)
            
            print(f"   Top 5 QBs:")
            for player in rankings.get('players', [])[:5]:
                print(f"     {player['rank']}. {player['name']} (ADP: {player['adp']})")
        
        print("-" * 40)


if __name__ == "__main__":
    asyncio.run(compare_league_formats())