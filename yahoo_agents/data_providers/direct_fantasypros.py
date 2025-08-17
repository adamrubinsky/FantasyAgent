"""
Direct FantasyPros API client for Yahoo agents
Uses the same API as the unified server
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.official_fantasypros import OfficialFantasyProsMCP
from typing import List, Dict, Optional


class DirectFantasyProsClient:
    """Direct client using OfficialFantasyProsMCP with session caching"""
    
    def __init__(self):
        self.client = OfficialFantasyProsMCP()
        # Cache rankings for entire session
        self.session_cache = {
            'PPR': None,
            'HALF': None,
            'cache_time': None
        }
    
    async def get_rankings_for_yahoo_league(self, 
                                           league_num: int,
                                           position: str = "ALL") -> List[Dict]:
        """
        Get rankings for specific Yahoo league with session caching
        
        Args:
            league_num: 2 for Snake PPR, 3 for Auction Half-PPR
            position: Position filter
        """
        # Map league to scoring type
        scoring_map = {
            2: "PPR",   # League 2: Full PPR
            3: "HALF"   # League 3: Half PPR  
        }
        
        scoring = scoring_map.get(league_num, "HALF")
        
        # Check session cache first
        if self.session_cache[scoring] is not None:
            print(f"📦 Using session-cached {scoring} rankings")
            rankings = self.session_cache[scoring]
        else:
            # Fetch fresh rankings and cache for entire session
            print(f"🔄 Fetching fresh {scoring} rankings (once per session)")
            rankings = await self.client.get_rankings(
                position="ALL",  # Always get all positions for cache
                scoring=scoring,
                limit=500  # Get top 500 players for comprehensive coverage
            )
            
            if rankings:
                self.session_cache[scoring] = rankings
                print(f"✅ Cached {len(rankings)} players for {scoring} scoring")
        
        # Filter by position if requested
        if position != "ALL" and rankings:
            rankings = [p for p in rankings if p.get('player_position_id') == position]
        
        return rankings if rankings else []


# Singleton instance
_client = None

def get_direct_fantasypros_client():
    """Get singleton client instance"""
    global _client
    if _client is None:
        _client = DirectFantasyProsClient()
    return _client