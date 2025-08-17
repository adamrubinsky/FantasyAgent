"""
Yahoo Fantasy Football API Client
Handles OAuth authentication and API interactions with Yahoo Fantasy Sports
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Yahoo OAuth and API imports
from yahoo_oauth import OAuth2
from yfpy import YahooFantasySportsQuery

logger = logging.getLogger(__name__)


class YahooFantasyClient:
    """
    Client for interacting with Yahoo Fantasy Football API
    Requires OAuth2 authentication
    """
    
    BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"
    
    def __init__(self, 
                 client_id: str = None,
                 client_secret: str = None,
                 league_id: str = None,
                 game_id: str = "nfl",  # NFL game ID for Yahoo
                 auth_dir: Path = None):
        """
        Initialize Yahoo Fantasy client
        
        Args:
            client_id: Yahoo App Client ID
            client_secret: Yahoo App Client Secret  
            league_id: Yahoo league ID
            game_id: Sport type (default "nfl")
            auth_dir: Directory to store OAuth tokens
        """
        self.client_id = client_id or os.getenv('YAHOO_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('YAHOO_CLIENT_SECRET')
        self.league_id = league_id or os.getenv('YAHOO_LEAGUE_ID')
        self.game_id = game_id
        
        # Setup auth directory for OAuth tokens
        if auth_dir is None:
            auth_dir = Path(__file__).parent.parent / "data" / "yahoo_auth"
        self.auth_dir = Path(auth_dir)
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        
        # OAuth and session management
        self.oauth = None
        self.session = None
        self.yfpy_query = None
        
        # Caching
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes default
        
    def _init_oauth(self):
        """Initialize OAuth2 connection"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Yahoo API credentials required. Set YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET")
            
        # Create OAuth2 object for Yahoo
        self.oauth = OAuth2(
            self.client_id,
            self.client_secret,
            redirect_uri="oob",  # Out of band for CLI apps
            base_url=self.BASE_URL
        )
        
    async def authenticate(self):
        """
        Authenticate with Yahoo OAuth2
        This will open a browser for initial auth if needed
        """
        if not self.oauth:
            self._init_oauth()
            
        # Check if we have valid tokens
        if not self.oauth.token_is_valid():
            print("🔐 Yahoo authentication required...")
            print("A browser will open for authentication.")
            # This will handle the OAuth flow
            self.oauth.refresh_access_token()
            
        print("✅ Yahoo authentication successful")
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        await self.authenticate()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    # -----------------
    # Draft Methods
    # -----------------
    
    async def get_draft_status(self, league_id: str = None) -> Dict[str, Any]:
        """
        Get current draft status and metadata
        
        Returns:
            Dict with draft status, current pick, time remaining, etc.
        """
        league_id = league_id or self.league_id
        cache_key = f"draft_status_{league_id}"
        
        # Check cache with short TTL for draft data
        if cached := self._check_cache(cache_key, ttl=10):  # 10 second cache
            return cached
            
        # Make API call
        endpoint = f"/league/nfl.l.{league_id}/draftresults"
        data = await self._make_request(endpoint)
        
        # Parse draft status
        status = {
            "is_draft_complete": data.get("draft_complete", False),
            "current_pick": data.get("current_pick"),
            "current_round": data.get("current_round"),
            "time_remaining": data.get("time_remaining"),
            "on_the_clock": data.get("on_the_clock_team"),
            "draft_type": data.get("draft_type", "snake")
        }
        
        self._update_cache(cache_key, status)
        return status
        
    async def get_available_players(self, 
                                   position: str = None,
                                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get list of available (undrafted) players
        
        Args:
            position: Filter by position (QB, RB, WR, TE, etc.)
            limit: Max number of players to return
            
        Returns:
            List of available players with rankings and projections
        """
        cache_key = f"available_{position}_{limit}"
        
        if cached := self._check_cache(cache_key, ttl=60):  # 1 minute cache
            return cached
            
        # Build query parameters
        params = {
            "format": "json",
            "count": limit
        }
        if position:
            params["position"] = position
            
        endpoint = f"/league/nfl.l.{self.league_id}/players;status=A"
        data = await self._make_request(endpoint, params=params)
        
        # Parse player data
        players = []
        for player_data in data.get("players", []):
            player = self._parse_player_data(player_data)
            players.append(player)
            
        # Sort by rank
        players.sort(key=lambda x: x.get("rank", 999))
        
        self._update_cache(cache_key, players)
        return players[:limit]
        
    async def get_user_team(self, team_key: str = None) -> Dict[str, Any]:
        """
        Get user's current drafted team
        
        Returns:
            Dict with roster by position
        """
        if not team_key:
            # Get user's team key
            user_data = await self._make_request(f"/users;use_login=1/teams")
            team_key = user_data.get("team_key")
            
        endpoint = f"/team/{team_key}/roster"
        data = await self._make_request(endpoint)
        
        # Organize by position
        roster = {
            "QB": [],
            "RB": [],
            "WR": [],
            "TE": [],
            "K": [],
            "DEF": []
        }
        
        for player in data.get("players", []):
            pos = player.get("position")
            if pos in roster:
                roster[pos].append(player)
                
        return roster
        
    async def make_pick(self, player_key: str) -> Dict[str, Any]:
        """
        Make a draft pick (when it's your turn)
        
        Args:
            player_key: Yahoo player key to draft
            
        Returns:
            Confirmation of pick
        """
        endpoint = f"/league/nfl.l.{self.league_id}/draft/pick"
        
        data = {
            "player_key": player_key
        }
        
        result = await self._make_request(endpoint, method="POST", data=data)
        return result
        
    # -----------------
    # Helper Methods
    # -----------------
    
    async def _make_request(self, 
                          endpoint: str, 
                          method: str = "GET",
                          params: Dict = None,
                          data: Dict = None) -> Dict[str, Any]:
        """Make authenticated request to Yahoo API"""
        if not self.oauth or not self.oauth.token_is_valid():
            await self.authenticate()
            
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.oauth.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Yahoo API error for {endpoint}: {e}")
            raise
            
    def _parse_player_data(self, data: Dict) -> Dict[str, Any]:
        """Parse Yahoo player data into standard format"""
        return {
            "player_key": data.get("player_key"),
            "name": data.get("name", {}).get("full"),
            "position": data.get("display_position"),
            "team": data.get("editorial_team_abbr"),
            "rank": data.get("rank", 999),
            "projected_points": data.get("projected_points"),
            "average_draft_position": data.get("average_draft_position"),
            "percent_owned": data.get("percent_owned"),
            "status": data.get("status")
        }
        
    def _check_cache(self, key: str, ttl: int = None) -> Optional[Any]:
        """Check if cached data exists and is fresh"""
        if key not in self.cache:
            return None
            
        entry = self.cache[key]
        ttl = ttl or self.cache_ttl
        
        if datetime.now() - entry["time"] < timedelta(seconds=ttl):
            return entry["data"]
        return None
        
    def _update_cache(self, key: str, data: Any):
        """Update cache with new data"""
        self.cache[key] = {
            "data": data,
            "time": datetime.now()
        }


# Simpler client using yfpy library
class YFPYClient:
    """
    Alternative client using the yfpy library for easier setup
    This handles OAuth complexity automatically
    """
    
    def __init__(self, auth_dir: Path = None):
        """Initialize with yfpy library"""
        self.auth_dir = auth_dir or Path(__file__).parent.parent / "data" / "yahoo_auth"
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        
        # Will be initialized on first use
        self.query = None
        self.league_id = os.getenv('YAHOO_LEAGUE_ID')
        
    def _init_query(self):
        """Initialize YFPY query object"""
        if self.query:
            return
            
        # Create auth file if it doesn't exist
        auth_file = self.auth_dir / "oauth2.json"
        if not auth_file.exists():
            auth_data = {
                "consumer_key": os.getenv('YAHOO_CLIENT_ID'),
                "consumer_secret": os.getenv('YAHOO_CLIENT_SECRET')
            }
            auth_file.write_text(json.dumps(auth_data))
            
        self.query = YahooFantasySportsQuery(
            auth_dir=str(self.auth_dir),
            league_id=self.league_id,
            game_code="nfl"
        )
        
    async def get_available_players(self, position: str = None) -> List[Dict]:
        """Get available players using yfpy"""
        self._init_query()
        
        # This is synchronous in yfpy, wrap in executor
        loop = asyncio.get_event_loop()
        players = await loop.run_in_executor(
            None,
            self.query.get_league_players,
            {"status": "A"}  # Available only
        )
        
        # Filter by position if specified
        if position:
            players = [p for p in players if p.display_position == position]
            
        return players