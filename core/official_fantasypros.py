"""
Official FantasyPros MCP Server Integration
Connects to the official FantasyPros MCP server for live data
"""

import asyncio
import json
import os
import subprocess
import time
from typing import Dict, List, Optional, Any
from pathlib import Path


class OfficialFantasyProsMCP:
    """
    Client for the official FantasyPros MCP server
    
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
        self.server_path = Path(__file__).parent.parent / "external" / "fantasypros-mcp-server"
        self.cache_dir = Path(__file__).parent.parent / "data"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Long cache TTL due to rate limits (100/day)
        self.cache_ttl = 4 * 3600  # 4 hours (use ~6 requests max per day)
        
        # Last request time for rate limiting (1/second)
        self.last_request_time = 0
        
    async def is_server_available(self) -> bool:
        """Check if the official MCP server is available and configured"""
        try:
            if not self.api_key:
                return False
            
            if not self.server_path.exists():
                return False
            
            # Check if server is built
            build_path = self.server_path / "build" / "index.js"
            if not build_path.exists():
                print("🔧 Building FantasyPros MCP server...")
                result = subprocess.run(
                    ["npm", "run", "build"], 
                    cwd=self.server_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"❌ Build failed: {result.stderr}")
                    return False
                print("✅ FantasyPros MCP server built successfully")
            
            return True
            
        except Exception as e:
            print(f"⚠️ Official MCP server check failed: {e}")
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
    
    async def _run_mcp_command(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run a command against the official MCP server"""
        try:
            await self._rate_limit_wait()
            
            # For now, return None - we'll implement the actual MCP communication
            # once we verify the server works with your API key
            print(f"🔄 Would call official MCP: {tool_name} with {arguments}")
            return None
            
        except Exception as e:
            print(f"❌ Official MCP call failed: {e}")
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
        
        arguments = {
            "sport": sport,
            "position": position, 
            "scoring": scoring,
            "limit": limit
        }
        
        result = await self._run_mcp_command("get_rankings", arguments)
        
        if result:
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
        
        arguments = {"sport": sport}
        if player_ids:
            arguments["player_ids"] = player_ids
        
        result = await self._run_mcp_command("get_players", arguments)
        
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
        
        arguments = {
            "sport": sport,
            "season": season,
            "position": position
        }
        if week:
            arguments["week"] = week
        
        result = await self._run_mcp_command("get_projections", arguments)
        
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
        
        arguments = {
            "sport": sport,
            "limit": limit
        }
        
        result = await self._run_mcp_command("get_sport_news", arguments)
        
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