"""
Unified Rankings Manager
Handles rankings for all platforms with appropriate settings
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class UnifiedRankingsManager:
    """Manages rankings for all fantasy platforms with league-specific adjustments"""
    
    def __init__(self):
        self.cache_dir = Path("platforms/shared/data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(hours=4)  # 4-hour cache
        
        # Platform-specific settings
        self.platform_settings = {
            "sleeper": {
                "position": "OP",      # SUPERFLEX
                "scoring": "HALF",     # Half-PPR
                "type": "DRAFT",
                "teams": 12,
                "adjustments": {}      # No adjustments needed, base SUPERFLEX
            },
            "yahoo-snake": {
                "position": "ALL",     # Standard positions
                "scoring": "PPR",      # Full PPR
                "type": "DRAFT", 
                "teams": 10,
                "adjustments": {
                    "QB": 1.15,        # 15% boost for 6PT passing TDs
                    "WR": 1.25,        # 25% boost for Full PPR
                    "RB_receiving": 1.15,  # Boost pass-catching RBs
                    "return_specialists": ["Tyreek Hill", "Deebo Samuel", "Cordarrelle Patterson"]
                }
            },
            "yahoo-auction": {
                "position": "ALL",     # Standard positions
                "scoring": "HALF",     # Half-PPR
                "type": "DRAFT",
                "teams": 12,
                "adjustments": {
                    "QB": 0.80,        # 20% penalty for 4PT passing TDs
                    "RB_receiving": 1.05,  # 5% boost for pass-catchers
                    "budget": 200,
                    "no_kicker": True
                }
            }
        }
        
    async def get_rankings(self, platform: str) -> List[Dict[str, Any]]:
        """Get rankings for a specific platform with appropriate adjustments"""
        
        if platform not in self.platform_settings:
            raise ValueError(f"Unknown platform: {platform}")
            
        settings = self.platform_settings[platform]
        
        # Check cache first
        cache_file = self.cache_dir / f"rankings_{platform}.json"
        if self._is_cache_valid(cache_file):
            logger.info(f"Using cached rankings for {platform}")
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        # Fetch fresh rankings
        logger.info(f"Fetching fresh rankings for {platform}")
        rankings = await self._fetch_rankings(settings)
        
        # Apply platform-specific adjustments
        adjusted_rankings = self._apply_adjustments(rankings, settings["adjustments"])
        
        # Re-sort after adjustments
        adjusted_rankings.sort(key=lambda x: x.get("adjusted_rank", x.get("rank_ecr", 999)))
        
        # Add rank numbers
        for i, player in enumerate(adjusted_rankings, 1):
            player["platform_rank"] = i
        
        # Cache the results
        with open(cache_file, 'w') as f:
            json.dump(adjusted_rankings, f)
        
        return adjusted_rankings
    
    async def _fetch_rankings(self, settings: Dict) -> List[Dict]:
        """Fetch rankings from FantasyPros or MCP server"""
        
        try:
            # Try MCP server first
            from platforms.shared.core.mcp_integration import MCPIntegration
            mcp = MCPIntegration()
            
            rankings = await mcp.get_rankings(
                position=settings["position"],
                scoring=settings["scoring"],
                type=settings["type"]
            )
            
            if rankings:
                return rankings
                
        except Exception as e:
            logger.warning(f"MCP server unavailable: {e}")
        
        # Fallback to direct FantasyPros API
        try:
            from platforms.shared.core.official_fantasypros import OfficialFantasyProsClient
            
            client = OfficialFantasyProsClient()
            rankings = await client.get_rankings(
                position=settings["position"],
                scoring=settings["scoring"]
            )
            
            return rankings
            
        except Exception as e:
            logger.error(f"Failed to fetch rankings: {e}")
            
        # Last resort: use cached data even if stale
        cache_file = self.cache_dir / f"rankings_backup.json"
        if cache_file.exists():
            logger.warning("Using stale backup rankings")
            with open(cache_file, 'r') as f:
                return json.load(f)
                
        return []
    
    def _apply_adjustments(self, rankings: List[Dict], adjustments: Dict) -> List[Dict]:
        """Apply platform-specific scoring adjustments"""
        
        if not adjustments:
            return rankings
            
        adjusted = []
        for player in rankings:
            player_copy = player.copy()
            position = player_copy.get("player_position_id", "")
            name = player_copy.get("player_name", "")
            
            # Calculate adjustment multiplier
            multiplier = 1.0
            
            # Position-based adjustments
            if position in adjustments:
                multiplier *= adjustments[position]
            
            # WR boost for Full PPR
            if position == "WR" and "WR" in adjustments:
                multiplier = adjustments["WR"]
            
            # RB receiving boost
            if position == "RB" and "RB_receiving" in adjustments:
                # Check if player is known pass-catcher (simplified)
                pass_catchers = ["Christian McCaffrey", "Austin Ekeler", "Alvin Kamara", 
                               "Saquon Barkley", "Breece Hall", "Bijan Robinson"]
                if any(name.startswith(pc.split()[0]) for pc in pass_catchers):
                    multiplier *= adjustments["RB_receiving"]
            
            # Return specialist bonus
            if "return_specialists" in adjustments:
                if name in adjustments["return_specialists"]:
                    multiplier *= 1.10  # 10% bonus
            
            # Apply multiplier to create adjusted rank
            base_rank = player_copy.get("rank_ecr", 999)
            player_copy["adjusted_rank"] = base_rank / multiplier
            player_copy["adjustment_factor"] = multiplier
            
            # Add auction value for auction leagues
            if "budget" in adjustments:
                player_copy["auction_value"] = self._calculate_auction_value(
                    player_copy["adjusted_rank"],
                    adjustments["budget"]
                )
            
            # Skip kickers if league doesn't use them
            if adjustments.get("no_kicker") and position == "K":
                continue
                
            adjusted.append(player_copy)
            
        return adjusted
    
    def _calculate_auction_value(self, rank: float, budget: int) -> int:
        """Calculate auction dollar value based on rank"""
        
        # Simple VBD-style calculation
        if rank <= 5:
            return int(budget * 0.30)  # Top 5 get 30% of budget
        elif rank <= 10:
            return int(budget * 0.20)  # Next 5 get 20%
        elif rank <= 20:
            return int(budget * 0.12)  # Next 10 get 12%
        elif rank <= 40:
            return int(budget * 0.06)  # Next 20 get 6%
        elif rank <= 80:
            return int(budget * 0.03)  # Next 40 get 3%
        elif rank <= 150:
            return int(budget * 0.01)  # Next 70 get 1%
        else:
            return 1  # Minimum $1
    
    def _is_cache_valid(self, cache_file: Path) -> bool:
        """Check if cache file exists and is fresh"""
        
        if not cache_file.exists():
            return False
            
        # Check age
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        age = datetime.now() - file_time
        
        return age < self.cache_ttl
    
    def clear_cache(self, platform: Optional[str] = None):
        """Clear cache for a specific platform or all platforms"""
        
        if platform:
            cache_file = self.cache_dir / f"rankings_{platform}.json"
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Cleared cache for {platform}")
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("rankings_*.json"):
                cache_file.unlink()
            logger.info("Cleared all ranking caches")
    
    def get_platform_info(self, platform: str) -> Dict[str, Any]:
        """Get information about a platform's settings"""
        
        if platform not in self.platform_settings:
            return {}
            
        settings = self.platform_settings[platform]
        return {
            "platform": platform,
            "scoring": settings["scoring"],
            "teams": settings["teams"],
            "superflex": settings["position"] == "OP",
            "adjustments": settings.get("adjustments", {}),
            "cache_ttl_hours": self.cache_ttl.total_seconds() / 3600
        }