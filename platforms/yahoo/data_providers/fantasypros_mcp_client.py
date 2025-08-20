"""
FantasyPros MCP Client for Yahoo Leagues
Uses the MCP server for rankings and projections
"""

import os
import json
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from core.mcp_integration import MCPClient


class FantasyProsMCPForYahoo:
    """
    FantasyPros MCP client adapted for Yahoo league scoring
    Uses MCP server tools: get_rankings and get_projections
    """
    
    def __init__(self):
        self.mcp_client = MCPClient()
        self.cache = {}
        
    async def get_rankings_for_yahoo_league(self,
                                           league_num: int,
                                           position: str = "ALL") -> List[Dict]:
        """
        Get rankings for specific Yahoo league
        
        Args:
            league_num: 2 for Snake PPR, 3 for Auction Half-PPR
            position: Position filter (ALL, QB, RB, WR, TE)
        """
        # Map league to scoring type
        scoring_map = {
            2: "PPR",   # League 2: Full PPR
            3: "HALF"   # League 3: Half PPR
        }
        
        scoring = scoring_map.get(league_num, "HALF")
        
        # Use MCP tool to get rankings
        try:
            result = await self.mcp_client.call_tool(
                "get_rankings",
                {
                    "sport": "NFL",
                    "position": position,
                    "scoring": scoring
                }
            )
            
            if result and "players" in result:
                rankings = self._process_rankings_for_yahoo(result["players"], league_num)
                return rankings
            
        except Exception as e:
            print(f"Error fetching rankings via MCP: {e}")
            
        return []
    
    async def get_projections_for_yahoo(self,
                                       week: int = 0,
                                       position: str = "ALL") -> Dict:
        """
        Get player projections via MCP
        
        Args:
            week: 0 for season-long, 1-17 for weekly
            position: Position filter
        """
        try:
            result = await self.mcp_client.call_tool(
                "get_projections",
                {
                    "sport": "NFL",
                    "season": datetime.now().year,
                    "week": week,
                    "position": position
                }
            )
            
            if result and "projections" in result:
                return self._process_projections(result["projections"])
            
        except Exception as e:
            print(f"Error fetching projections via MCP: {e}")
            
        return {}
    
    def _process_rankings_for_yahoo(self, players: List[Dict], league_num: int) -> List[Dict]:
        """
        Process and adjust rankings for Yahoo league specifics
        
        League 2 (Full PPR) adjustments:
        - Boost WRs and pass-catching RBs more
        - QB boost for 6PT passing TDs
        - Return specialist bonus
        
        League 3 (Half PPR) adjustments:
        - Balanced RB/WR approach
        - QB penalty for 4PT passing TDs
        - Calculate auction values
        """
        processed = []
        
        for player in players:
            # Extract player data from MCP response
            p = {
                "name": player.get("player_name", "Unknown"),
                "position": player.get("player_position_id", "??"),
                "team": player.get("player_team_id", "??"),
                "rank": player.get("rank_ecr", 999),
                "adp": player.get("rank_ave", 999),
                "bye_week": player.get("player_bye_week", 0)
            }
            
            if league_num == 2:  # Full PPR adjustments
                # WR premium in Full PPR
                if p["position"] == "WR":
                    p["ppr_boost"] = 1.20  # 20% boost
                    p["adjusted_rank"] = p["rank"] * 0.83  # Better rank
                    
                # Pass-catching RB bonus
                elif p["position"] == "RB":
                    # Check if known pass-catcher
                    pass_catchers = ["McCaffrey", "Ekeler", "Kamara", "White", "Gibbs", "Swift"]
                    if any(name in p["name"] for name in pass_catchers):
                        p["ppr_boost"] = 1.15
                        p["adjusted_rank"] = p["rank"] * 0.87
                    else:
                        p["adjusted_rank"] = p["rank"]
                        
                # QB boost for 6PT passing TDs
                elif p["position"] == "QB":
                    p["qb_boost"] = 1.15  # 15% value boost
                    p["adjusted_rank"] = p["rank"] * 0.90  # Better rank
                    
                # Return specialist bonus
                return_guys = ["Hill", "Samuel", "Shaheed", "Waddle", "Turpin"]
                if any(name in p["name"] for name in return_guys):
                    p["return_bonus"] = True
                    p["adjusted_rank"] *= 0.95  # 5% rank boost
                    
            elif league_num == 3:  # Half PPR Auction adjustments
                # Calculate auction value
                rank = p["rank"]
                if rank <= 5:
                    p["auction_value"] = 60 + (5 - rank) * 5  # $60-80
                elif rank <= 15:
                    p["auction_value"] = 35 + (15 - rank) * 2.5  # $35-60
                elif rank <= 30:
                    p["auction_value"] = 20 + (30 - rank) * 1.5  # $20-35
                elif rank <= 50:
                    p["auction_value"] = 10 + (50 - rank) * 0.5  # $10-20
                elif rank <= 100:
                    p["auction_value"] = 3 + (100 - rank) * 0.14  # $3-10
                else:
                    p["auction_value"] = max(1, 3 - (rank - 100) * 0.02)  # $1-3
                    
                # QB devalue for 4PT passing TDs
                if p["position"] == "QB":
                    p["qb_penalty"] = 0.80  # 20% value reduction
                    p["auction_value"] = int(p["auction_value"] * 0.80)
                    
                # No kicker in League 3
                if p["position"] == "K":
                    continue  # Skip kickers
                    
            processed.append(p)
        
        # Re-sort by adjusted rank for League 2
        if league_num == 2:
            processed.sort(key=lambda x: x.get("adjusted_rank", x["rank"]))
            
        return processed
    
    def _process_projections(self, projections: List[Dict]) -> Dict:
        """Process projections from MCP response"""
        processed = {}
        
        for proj in projections:
            name = proj.get("player_name")
            if name:
                processed[name] = {
                    "pass_yards": proj.get("passing_yards", 0),
                    "pass_tds": proj.get("passing_tds", 0),
                    "rush_yards": proj.get("rushing_yards", 0),
                    "rush_tds": proj.get("rushing_tds", 0),
                    "rec_yards": proj.get("receiving_yards", 0),
                    "rec_tds": proj.get("receiving_tds", 0),
                    "receptions": proj.get("receptions", 0),
                    "fantasy_points": proj.get("fantasy_points", 0)
                }
        
        return processed
    
    def calculate_yahoo_scoring(self, 
                               proj: Dict,
                               league_num: int) -> float:
        """
        Calculate fantasy points for Yahoo league scoring
        
        League 2 (Full PPR):
        - 6 PT passing TDs
        - 1 point per reception
        - Bonuses at yardage thresholds
        
        League 3 (Half PPR):
        - 4 PT passing TDs
        - 0.5 points per reception
        - Different bonus structure
        """
        points = 0
        
        if league_num == 2:  # Full PPR with bonuses
            # Passing
            points += proj["pass_yards"] / 25
            points += proj["pass_tds"] * 6  # 6 PT TDs
            
            # Rushing
            points += proj["rush_yards"] / 10
            points += proj["rush_tds"] * 6
            
            # Receiving
            points += proj["rec_yards"] / 10
            points += proj["rec_tds"] * 6
            points += proj["receptions"] * 1.0  # Full PPR
            
            # Calculate per-game bonuses (17 games)
            pass_ypg = proj["pass_yards"] / 17
            rush_ypg = proj["rush_yards"] / 17
            rec_ypg = proj["rec_yards"] / 17
            
            # Passing bonuses
            if pass_ypg >= 300:
                points += 17 * 3
            elif pass_ypg >= 350:
                points += 17 * 2
            elif pass_ypg >= 400:
                points += 17 * 1
                
            # Rushing bonuses
            if rush_ypg >= 90:
                points += 17 * 3
            elif rush_ypg >= 130:
                points += 17 * 2
            elif rush_ypg >= 170:
                points += 17 * 1
                
            # Receiving bonuses
            if rec_ypg >= 100:
                points += 17 * 3
            elif rec_ypg >= 140:
                points += 17 * 2
            elif rec_ypg >= 180:
                points += 17 * 1
                
        elif league_num == 3:  # Half PPR
            # Passing
            points += proj["pass_yards"] / 25
            points += proj["pass_tds"] * 4  # 4 PT TDs
            
            # Rushing
            points += proj["rush_yards"] / 10
            points += proj["rush_tds"] * 6
            
            # Receiving
            points += proj["rec_yards"] / 10
            points += proj["rec_tds"] * 6
            points += proj["receptions"] * 0.5  # Half PPR
            
            # Simpler bonuses for League 3
            pass_ypg = proj["pass_yards"] / 17
            rush_ypg = proj["rush_yards"] / 17
            rec_ypg = proj["rec_yards"] / 17
            
            if pass_ypg >= 300:
                points += 17 * 2
            if pass_ypg >= 400:
                points += 17 * 1
                
            if rush_ypg >= 100:
                points += 17 * 1
            if rush_ypg >= 150:
                points += 17 * 2
                
            if rec_ypg >= 125:
                points += 17 * 1
            if rec_ypg >= 150:
                points += 17 * 1
        
        return points


# Singleton instance
_mcp_client = None

def get_fantasypros_mcp_client() -> FantasyProsMCPForYahoo:
    """Get or create MCP client singleton"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = FantasyProsMCPForYahoo()
    return _mcp_client


# Test function
async def test_mcp_integration():
    """Test FantasyPros MCP integration for Yahoo"""
    print("\n" + "="*60)
    print("TESTING FANTASYPROS MCP FOR YAHOO LEAGUES")
    print("="*60)
    
    client = get_fantasypros_mcp_client()
    
    # Test League 2 (Full PPR)
    print("\n--- League 2: Full PPR Rankings (via MCP) ---")
    rankings = await client.get_rankings_for_yahoo_league(2, "WR")
    
    if rankings:
        print("Top 5 WRs for Full PPR:")
        for i, player in enumerate(rankings[:5], 1):
            rank = player.get("adjusted_rank", player["rank"])
            print(f"{i}. {player['name']} ({player['team']}) - Rank: {rank:.1f}")
            if "ppr_boost" in player:
                print(f"   PPR Boost: {player['ppr_boost']:.2f}x")
            if player.get("return_bonus"):
                print(f"   🎯 Return Specialist Bonus!")
    
    # Test League 3 (Auction Half PPR)
    print("\n--- League 3: Auction Values (Half PPR via MCP) ---")
    rankings = await client.get_rankings_for_yahoo_league(3, "RB")
    
    if rankings:
        print("Top 5 RB Auction Values:")
        for i, player in enumerate(rankings[:5], 1):
            value = player.get("auction_value", 0)
            print(f"{i}. {player['name']} ({player['team']}) - ${value:.0f}")
    
    # Test projections
    print("\n--- Projections Test (via MCP) ---")
    projections = await client.get_projections_for_yahoo(week=0, position="QB")
    
    if projections:
        print("Sample QB Projections:")
        for name in list(projections.keys())[:3]:
            proj = projections[name]
            l2_points = client.calculate_yahoo_scoring(proj, 2)
            l3_points = client.calculate_yahoo_scoring(proj, 3)
            print(f"{name}:")
            print(f"  League 2 (6PT TD): {l2_points:.1f} pts")
            print(f"  League 3 (4PT TD): {l3_points:.1f} pts")


if __name__ == "__main__":
    asyncio.run(test_mcp_integration())