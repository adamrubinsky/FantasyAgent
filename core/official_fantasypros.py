"""
Official FantasyPros API Integration
Direct connection to FantasyPros API for live data
"""

import asyncio
import aiohttp
import json
import os
import ssl
import time
from typing import Dict, List, Optional, Any
from pathlib import Path


class OfficialFantasyProsMCP:
    """
    Direct client for the official FantasyPros API
    
    Features:
    - Live rankings from FantasyPros API
    - Real ADP data
    - Player projections
    - News and updates
    
    Rate Limits:
    - 1 request per second
    - 100 requests per day
    - Smart caching required!
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('FANTASYPROS_API_KEY')
        self.base_url = "https://api.fantasypros.com/public/v2/json"
        self.cache_dir = Path(__file__).parent.parent / "data"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Long cache TTL due to rate limits (100/day)
        self.cache_ttl = 4 * 3600  # 4 hours (use ~6 requests max per day)
        
        # Last request time for rate limiting (1/second)
        self.last_request_time = 0
        
        # SSL context for development
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
    async def is_server_available(self) -> bool:
        """Check if the FantasyPros API is available with our key"""
        try:
            if not self.api_key:
                return False
            
            # Test the API with a simple request
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                headers = {
                    'x-api-key': self.api_key,
                    'User-Agent': 'FantasyAgent/1.0'
                }
                
                test_url = f"{self.base_url}/nfl/2025/consensus-rankings"
                params = {'position': 'QB', 'scoring': 'HALF', 'limit': 1}
                
                async with session.get(test_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        print("✅ FantasyPros API is active and working!")
                        return True
                    else:
                        print(f"❌ FantasyPros API returned status {response.status}")
                        return False
            
        except Exception as e:
            print(f"⚠️ FantasyPros API check failed: {e}")
            return False
    
    async def _rate_limit_wait(self):
        """Ensure we don't exceed 1 request per second"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < 1.0:
            wait_time = 1.0 - time_since_last
            print(f"⏱️ Rate limiting: waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    async def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached data if still valid"""
        cache_file = self.cache_dir / f"fantasypros_{cache_key}.json"
        
        if cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < self.cache_ttl:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    print(f"📍 Using cached FantasyPros data ({cache_key}, {cache_age/3600:.1f}h old)")
                    return data
        
        return None
    
    async def _cache_data(self, cache_key: str, data: Dict[str, Any]):
        """Cache data to disk"""
        cache_file = self.cache_dir / f"fantasypros_{cache_key}.json"
        
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"💾 Cached FantasyPros data ({cache_key})")
    
    async def _make_api_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Make a direct API request to FantasyPros"""
        try:
            await self._rate_limit_wait()
            
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                headers = {
                    'x-api-key': self.api_key,
                    'User-Agent': 'FantasyAgent/1.0'
                }
                
                url = f"{self.base_url}/{endpoint}"
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        error_text = await response.text()
                        print(f"❌ API request failed: {response.status} - {error_text}")
                        return None
            
        except Exception as e:
            print(f"❌ API request failed: {e}")
            return None
    
    async def get_rankings(self, 
                          sport: str = "NFL", 
                          position: str = "ALL", 
                          scoring: str = "HALF", 
                          limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        Get player rankings from official FantasyPros API
        
        Args:
            sport: Sport type (NFL)
            position: Position filter (ALL, QB, RB, WR, TE, etc.)
            scoring: Scoring format (STD, HALF, PPR)
            limit: Max players to return
            
        Returns:
            Dict with rankings data or None if failed
        """
        cache_key = f"rankings_{sport}_{position}_{scoring}_{limit}"
        
        # Try cache first
        cached = await self._get_cached_data(cache_key)
        if cached:
            return cached
        
        # Try official API
        print(f"🌐 Fetching live rankings from FantasyPros API...")
        
        endpoint = f"nfl/2025/consensus-rankings"
        
        # CRITICAL: Use 'OP' for SUPERFLEX rankings, 'DRAFT' type for draft rankings
        params = {
            "scoring": scoring,
            "type": "DRAFT",  # Always use DRAFT type for draft rankings
            "week": 0         # Season-long rankings
        }
        
        # Map position parameter correctly for SUPERFLEX
        if position == "ALL" or position == "SUPERFLEX":
            # Use 'OP' (Offensive Player) for SUPERFLEX rankings
            params["position"] = "OP"  # This gives proper SUPERFLEX rankings!
        elif position:
            params["position"] = position
        else:
            params["position"] = "OP"  # Default to SUPERFLEX rankings
        
        result = await self._make_api_request(endpoint, params)
        
        if result:
            # Extract players from FantasyPros API response structure
            if isinstance(result, dict) and 'players' in result:
                players_data = result['players']
                print(f"✅ Extracted {len(players_data)} players from FantasyPros API")
                await self._cache_data(cache_key, players_data)
                return players_data
            else:
                print(f"❌ Unexpected API response structure: {list(result.keys()) if isinstance(result, dict) else type(result)}")
                await self._cache_data(cache_key, result)
                return result
        
        return None
    
    async def get_players(self, sport: str = "NFL", player_ids: List[str] = None) -> Optional[Dict[str, Any]]:
        """Get player information from official FantasyPros API"""
        cache_key = f"players_{sport}_{len(player_ids) if player_ids else 'all'}"
        
        # Try cache first  
        cached = await self._get_cached_data(cache_key)
        if cached:
            return cached
        
        print(f"🌐 Fetching player data from FantasyPros API...")
        
        endpoint = f"nfl/players"
        params = {}
        if player_ids:
            params["player_ids"] = ",".join(player_ids)
        
        result = await self._make_api_request(endpoint, params)
        
        if result:
            await self._cache_data(cache_key, result)
            return result
        
        return None
    
    async def get_projections(self, 
                             sport: str = "NFL", 
                             season: int = 2025, 
                             week: int = None,
                             position: str = "ALL") -> Optional[Dict[str, Any]]:
        """Get player projections from official FantasyPros API"""
        cache_key = f"projections_{sport}_{season}_{week}_{position}"
        
        # Try cache first
        cached = await self._get_cached_data(cache_key)  
        if cached:
            return cached
        
        print(f"🌐 Fetching projections from FantasyPros API...")
        
        endpoint = f"nfl/{season}/projections"
        params = {
            "position": position if position != "ALL" else None
        }
        if week:
            params["week"] = week
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        result = await self._make_api_request(endpoint, params)
        
        if result:
            await self._cache_data(cache_key, result)
            return result
        
        return None
    
    async def get_news(self, sport: str = "NFL", limit: int = 10) -> Optional[Dict[str, Any]]:
        """Get fantasy news from official FantasyPros API"""
        cache_key = f"news_{sport}_{limit}"
        
        # Try cache first (shorter TTL for news)
        cache_file = self.cache_dir / f"fantasypros_{cache_key}.json"
        if cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < 1800:  # 30 minutes for news
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    print(f"📍 Using cached news data ({cache_age/60:.1f}m old)")
                    return data
        
        print(f"🌐 Fetching news from FantasyPros API...")
        
        endpoint = f"nfl/news"
        params = {
            "limit": limit
        }
        
        result = await self._make_api_request(endpoint, params)
        
        if result:
            await self._cache_data(cache_key, result)
            return result
        
        return None


# Test function
async def test_official_mcp():
    """Test the official FantasyPros MCP server"""
    client = OfficialFantasyProsMCP()
    
    print("🧪 Testing Official FantasyPros MCP Integration")
    print("=" * 50)
    
    # Check if server is available
    available = await client.is_server_available()
    print(f"Server available: {available}")
    
    if available:
        # Test rankings
        rankings = await client.get_rankings(position="QB", limit=10)
        if rankings:
            print("✅ Rankings API working")
        else:
            print("❌ Rankings API failed")
        
        # Test players
        players = await client.get_players()
        if players:
            print("✅ Players API working")
        else:
            print("❌ Players API failed")
        
        # Test projections
        projections = await client.get_projections(position="QB")
        if projections:
            print("✅ Projections API working")
        else:
            print("❌ Projections API failed")


if __name__ == "__main__":
    asyncio.run(test_official_mcp())