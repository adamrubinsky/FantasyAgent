"""
Sleeper Player Cache - Local cache for player ID to name mappings
Player IDs never change, so we can cache them indefinitely
"""

import json
import os
import aiohttp
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SleeperPlayerCache:
    """Cache for Sleeper player data"""
    
    def __init__(self):
        self.players: Dict[str, dict] = {}
        self.cache_file = "/tmp/sleeper_players_cache.json"
        self.last_update = None
        self.cache_ttl_days = 7  # Refresh weekly for new players
        
    async def ensure_loaded(self):
        """Ensure player data is loaded"""
        # Check if we have data in memory
        if self.players and self.last_update:
            # Check if cache is still fresh (within TTL)
            if datetime.now() - self.last_update < timedelta(days=self.cache_ttl_days):
                return
        
        # Try to load from file cache first
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self.players = cache_data.get("players", {})
                    cache_time = cache_data.get("timestamp", 0)
                    self.last_update = datetime.fromtimestamp(cache_time)
                    
                    # Check if file cache is fresh
                    if datetime.now() - self.last_update < timedelta(days=self.cache_ttl_days):
                        logger.info(f"Loaded {len(self.players)} players from file cache")
                        return
            except Exception as e:
                logger.error(f"Failed to load player cache file: {e}")
        
        # If we get here, need to fetch from API
        await self.fetch_players()
    
    async def fetch_players(self):
        """Fetch all players from Sleeper API"""
        try:
            logger.info("Fetching Sleeper player database...")
            
            # Create session with SSL verification disabled (macOS certificate issue)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Sleeper provides all players in a single endpoint
                url = "https://api.sleeper.app/v1/players/nfl"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        self.players = await resp.json()
                        self.last_update = datetime.now()
                        
                        # Save to file cache
                        try:
                            cache_data = {
                                "players": self.players,
                                "timestamp": self.last_update.timestamp()
                            }
                            with open(self.cache_file, 'w') as f:
                                json.dump(cache_data, f)
                            logger.info(f"Cached {len(self.players)} players to file")
                        except Exception as e:
                            logger.error(f"Failed to save player cache: {e}")
                        
                        logger.info(f"Loaded {len(self.players)} players from Sleeper API")
                    else:
                        logger.error(f"Failed to fetch players: HTTP {resp.status}")
                        
        except Exception as e:
            logger.error(f"Failed to fetch Sleeper players: {e}")
            # Even if fetch fails, continue with empty cache
            self.players = {}
    
    def get_player_name(self, player_id: str) -> str:
        """Get player name from ID"""
        if player_id in self.players:
            player = self.players[player_id]
            first_name = player.get("first_name", "")
            last_name = player.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip()
            return full_name if full_name else f"Player {player_id}"
        return f"Player {player_id}"
    
    def get_player_info(self, player_id: str) -> Optional[dict]:
        """Get full player info from ID"""
        return self.players.get(player_id)
    
    def search_player(self, name: str) -> Optional[str]:
        """Search for player ID by name"""
        name_lower = name.lower()
        for player_id, player in self.players.items():
            first_name = player.get("first_name", "").lower()
            last_name = player.get("last_name", "").lower()
            full_name = f"{first_name} {last_name}"
            
            if name_lower in full_name or full_name in name_lower:
                return player_id
        return None

# Global instance
sleeper_player_cache = SleeperPlayerCache()