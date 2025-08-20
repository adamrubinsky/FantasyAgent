"""
FantasyPros Integration for Yahoo Leagues
Fetches league-specific rankings and projections
"""

import os
import requests
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json


class FantasyProsYahooClient:
    """
    FantasyPros client optimized for Yahoo league settings
    Handles different scoring formats and bonus structures
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('FANTASYPROS_API_KEY')
        if not self.api_key:
            raise ValueError("FantasyPros API key required")
        
        self.base_url = "https://api.fantasypros.com/public/v2/json/nfl"
        self.current_year = datetime.now().year
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour cache
        
    async def get_rankings_for_league(self, 
                                     league_type: str,
                                     position: str = "ALL",
                                     week: int = 0) -> List[Dict]:
        """
        Get rankings specific to league scoring settings
        
        Args:
            league_type: "yahoo_snake_ppr" or "yahoo_auction_half"
            position: Position filter or "ALL"
            week: 0 for season-long, 1-17 for weekly
        """
        # Map league types to FantasyPros parameters
        scoring_map = {
            "yahoo_snake_ppr": "PPR",      # Full PPR for League 2
            "yahoo_auction_half": "HALF",   # Half PPR for League 3
            "sleeper_superflex": "OP"       # SUPERFLEX (Offensive Player)
        }
        
        scoring = scoring_map.get(league_type, "HALF")
        
        # Check cache
        cache_key = f"{league_type}_{position}_{week}"
        if cached := self._check_cache(cache_key):
            return cached
        
        # Build request
        url = f"{self.base_url}/{self.current_year}/consensus-rankings"
        
        params = {
            'position': position if position != "ALL" else "OP",
            'scoring': scoring,
            'type': 'DRAFT',
            'week': week
        }
        
        headers = {
            'x-api-key': self.api_key,
            'User-Agent': 'FantasyAgent/1.0'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                rankings = self._parse_rankings(data, league_type)
                self._update_cache(cache_key, rankings)
                return rankings
            else:
                print(f"❌ FantasyPros API error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Failed to fetch rankings: {e}")
            return []
    
    def _parse_rankings(self, data: Dict, league_type: str) -> List[Dict]:
        """Parse and adjust rankings for specific league scoring"""
        rankings = []
        
        for player_data in data.get('players', []):
            player = {
                "name": player_data.get('player_name', 'Unknown'),
                "position": player_data.get('player_position_id', 'Unknown'),
                "team": player_data.get('player_team_id', 'Unknown'),
                "rank_ecr": player_data.get('rank_ecr', 999),
                "rank_ave": float(player_data.get('rank_ave', 999)),
                "rank_std": float(player_data.get('rank_std', 0)),
                "bye_week": player_data.get('player_bye_week', 0)
            }
            
            # League-specific adjustments
            if league_type == "yahoo_snake_ppr":
                # Boost WRs and pass-catching RBs for Full PPR
                player["ppr_boost"] = self._calculate_ppr_boost(player)
                player["adjusted_rank"] = self._adjust_rank_for_ppr(player)
                
                # QB boost for 6PT passing TDs
                if player["position"] == "QB":
                    player["qb_boost"] = 0.15  # 15% boost for 6PT TDs
                    player["adjusted_rank"] *= 0.85  # Lower rank = better
                    
            elif league_type == "yahoo_auction_half":
                # Half PPR - balanced approach
                player["auction_value"] = self._calculate_auction_value(player)
                
                # QB devalue for 4PT passing TDs
                if player["position"] == "QB":
                    player["qb_penalty"] = 0.20  # 20% value reduction
                    player["auction_value"] *= 0.80
            
            rankings.append(player)
        
        # Re-sort by adjusted rankings
        if league_type == "yahoo_snake_ppr":
            rankings.sort(key=lambda x: x.get("adjusted_rank", x["rank_ecr"]))
        
        return rankings
    
    async def get_projections_with_bonuses(self, 
                                          league_type: str,
                                          players: List[str]) -> Dict:
        """
        Get projections and calculate bonus points
        
        League 2 bonuses:
        - Passing: +3 at 300y, +2 at 350y, +1 at 400y
        - Rushing: +3 at 90y, +2 at 130y, +1 at 170y  
        - Receiving: +3 at 100y, +2 at 140y, +1 at 180y
        """
        # Fetch base projections
        url = f"{self.base_url}/{self.current_year}/projections"
        
        scoring = "PPR" if "ppr" in league_type else "HALF"
        
        params = {
            'scoring': scoring,
            'type': 'SEASON'
        }
        
        headers = {
            'x-api-key': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                projections = {}
                
                for player_data in data.get('players', []):
                    name = player_data.get('player_name')
                    if name not in players:
                        continue
                    
                    proj = {
                        "pass_yards": player_data.get('passing_yards', 0),
                        "pass_tds": player_data.get('passing_tds', 0),
                        "rush_yards": player_data.get('rushing_yards', 0),
                        "rush_tds": player_data.get('rushing_tds', 0),
                        "rec_yards": player_data.get('receiving_yards', 0),
                        "rec_tds": player_data.get('receiving_tds', 0),
                        "receptions": player_data.get('receptions', 0)
                    }
                    
                    # Calculate bonuses for League 2
                    if league_type == "yahoo_snake_ppr":
                        proj["bonus_points"] = self._calculate_bonuses(proj)
                        proj["total_projected"] = self._calculate_total_points(proj, league_type)
                    
                    projections[name] = proj
                
                return projections
            
        except Exception as e:
            print(f"Failed to fetch projections: {e}")
            return {}
    
    def _calculate_ppr_boost(self, player: Dict) -> float:
        """Calculate PPR boost for pass-catching players"""
        pos = player["position"]
        
        # Position-based PPR boost factors
        if pos == "WR":
            return 1.25  # 25% boost for WRs
        elif pos == "RB":
            # Would check reception projections in real implementation
            # For now, use heuristic based on known pass-catchers
            pass_catchers = ["McCaffrey", "Ekeler", "Kamara", "White", "Gibbs"]
            if any(name in player["name"] for name in pass_catchers):
                return 1.15  # 15% boost for pass-catching RBs
            return 1.05  # 5% boost for standard RBs
        elif pos == "TE":
            return 1.10  # 10% boost for TEs
        return 1.0
    
    def _adjust_rank_for_ppr(self, player: Dict) -> float:
        """Adjust rank for Full PPR scoring"""
        base_rank = player["rank_ecr"]
        ppr_boost = player.get("ppr_boost", 1.0)
        
        # Lower rank is better, so divide by boost
        return base_rank / ppr_boost
    
    def _calculate_auction_value(self, player: Dict) -> int:
        """Calculate auction dollar value"""
        rank = player["rank_ecr"]
        
        # Simple value curve for $200 budget
        if rank <= 5:
            return 55 + (5 - rank) * 5  # $55-75
        elif rank <= 15:
            return 35 + (15 - rank) * 2  # $35-55
        elif rank <= 30:
            return 20 + (30 - rank)  # $20-35
        elif rank <= 50:
            return 10 + (50 - rank) // 2  # $10-20
        elif rank <= 100:
            return 3 + (100 - rank) // 10  # $3-10
        elif rank <= 150:
            return 1 + (150 - rank) // 25  # $1-3
        else:
            return 1
    
    def _calculate_bonuses(self, proj: Dict) -> float:
        """Calculate bonus points for League 2"""
        bonus = 0
        
        # Per game averages (assuming 17 games)
        pass_ypg = proj["pass_yards"] / 17
        rush_ypg = proj["rush_yards"] / 17
        rec_ypg = proj["rec_yards"] / 17
        
        # Passing bonuses
        if pass_ypg >= 400:
            bonus += 17 * 1  # +1 per game
        if pass_ypg >= 350:
            bonus += 17 * 2  # +2 per game
        if pass_ypg >= 300:
            bonus += 17 * 3  # +3 per game
            
        # Rushing bonuses
        if rush_ypg >= 170:
            bonus += 17 * 1
        if rush_ypg >= 130:
            bonus += 17 * 2
        if rush_ypg >= 90:
            bonus += 17 * 3
            
        # Receiving bonuses
        if rec_ypg >= 180:
            bonus += 17 * 1
        if rec_ypg >= 140:
            bonus += 17 * 2
        if rec_ypg >= 100:
            bonus += 17 * 3
        
        return bonus
    
    def _calculate_total_points(self, proj: Dict, league_type: str) -> float:
        """Calculate total projected points for specific league"""
        total = 0
        
        if league_type == "yahoo_snake_ppr":
            # Full PPR with 6PT passing TDs
            total += proj["pass_yards"] / 25  # 25 yards per point
            total += proj["pass_tds"] * 6     # 6 points per TD
            total += proj["rush_yards"] / 10
            total += proj["rush_tds"] * 6
            total += proj["rec_yards"] / 10
            total += proj["rec_tds"] * 6
            total += proj["receptions"] * 1   # Full PPR
            total += proj.get("bonus_points", 0)
            
        elif league_type == "yahoo_auction_half":
            # Half PPR with 4PT passing TDs
            total += proj["pass_yards"] / 25
            total += proj["pass_tds"] * 4     # 4 points per TD
            total += proj["rush_yards"] / 10
            total += proj["rush_tds"] * 6
            total += proj["rec_yards"] / 10
            total += proj["rec_tds"] * 6
            total += proj["receptions"] * 0.5  # Half PPR
        
        return total
    
    async def get_return_specialists(self) -> List[str]:
        """Get players with return value for League 2"""
        # Known return specialists for 2025
        return [
            "Deebo Samuel",
            "Tyreek Hill",
            "Rashid Shaheed",
            "KaVontae Turpin",
            "Jaylen Waddle",
            "Mecole Hardman",
            "Richie James",
            "Rondale Moore"
        ]
    
    def _check_cache(self, key: str) -> Optional[Any]:
        """Check cache with TTL"""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry["time"] < timedelta(seconds=self.cache_ttl):
                return entry["data"]
        return None
    
    def _update_cache(self, key: str, data: Any):
        """Update cache"""
        self.cache[key] = {
            "data": data,
            "time": datetime.now()
        }


# Singleton instance
_fp_client = None

def get_fantasypros_client() -> FantasyProsYahooClient:
    """Get or create FantasyPros client singleton"""
    global _fp_client
    if _fp_client is None:
        _fp_client = FantasyProsYahooClient()
    return _fp_client


# Test function
async def test_fantasypros_integration():
    """Test FantasyPros integration for Yahoo leagues"""
    print("\n" + "="*60)
    print("TESTING FANTASYPROS YAHOO INTEGRATION")
    print("="*60)
    
    client = get_fantasypros_client()
    
    # Test League 2 (Full PPR) rankings
    print("\n--- League 2: Full PPR Rankings ---")
    rankings = await client.get_rankings_for_league("yahoo_snake_ppr", "WR")
    
    if rankings:
        print("Top 5 WRs for Full PPR:")
        for i, player in enumerate(rankings[:5], 1):
            print(f"{i}. {player['name']} - Rank: {player.get('adjusted_rank', player['rank_ecr']):.1f}")
            if 'ppr_boost' in player:
                print(f"   PPR Boost: {player['ppr_boost']:.2f}x")
    
    # Test League 3 (Auction Half PPR) values
    print("\n--- League 3: Auction Values (Half PPR) ---")
    rankings = await client.get_rankings_for_league("yahoo_auction_half", "RB")
    
    if rankings:
        print("Top 5 RB Auction Values:")
        for i, player in enumerate(rankings[:5], 1):
            value = player.get('auction_value', 0)
            print(f"{i}. {player['name']} - ${value}")
    
    # Test return specialists
    print("\n--- Return Specialists (League 2 Bonus) ---")
    specialists = await client.get_return_specialists()
    print(f"Players with return value: {', '.join(specialists[:5])}")


if __name__ == "__main__":
    # Load environment
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    load_dotenv()
    
    asyncio.run(test_fantasypros_integration())