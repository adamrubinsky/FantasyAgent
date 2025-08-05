"""
Fantasy Football Draft Assistant - Sleeper API Client
Handles all interactions with the Sleeper Fantasy Football platform API
"""

import aiohttp
import asyncio
import json
import os
import ssl
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class SleeperClient:
    """
    Client for interacting with Sleeper Fantasy Football API
    No authentication required - all endpoints are public
    """
    
    BASE_URL = "https://api.sleeper.app/v1"
    
    def __init__(self, username: str = None, league_id: str = None):
        self.username = username or os.getenv('SLEEPER_USERNAME')
        self.league_id = league_id or os.getenv('SLEEPER_LEAGUE_ID')
        self.session = None
        self.players_cache = {}
        self.cache_dir = Path(__file__).parent.parent / "data"
        self.cache_dir.mkdir(exist_ok=True)
        
    async def __aenter__(self):
        """Async context manager entry"""
        # For development - disable SSL verification (common Mac issue)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        self.session = aiohttp.ClientSession(connector=connector)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, endpoint: str) -> Dict[str, Any]:
        """
        Make HTTP request to Sleeper API with comprehensive error handling
        
        This is the core method that all other API calls use. It handles:
        - Building the full URL from base URL + endpoint
        - Making async HTTP GET request using aiohttp
        - Converting response to JSON automatically
        - Proper error handling with meaningful messages
        
        Args:
            endpoint: API endpoint path (without base URL, e.g., "/user/adamrubinsky")
            
        Returns:
            Dict containing the parsed JSON API response
            
        Raises:
            Exception: If API request fails for any reason (network, HTTP error, etc.)
        """
        # Construct full URL by combining base URL with specific endpoint
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            # Use async context manager to make HTTP GET request
            # This ensures the connection is properly closed after use
            async with self.session.get(url) as response:
                # Check if HTTP status is success (200-299), raise exception if not
                response.raise_for_status()
                # Parse JSON response body and return as Python dictionary
                return await response.json()
        except aiohttp.ClientError as e:
            # Catch any HTTP client errors (network issues, HTTP errors, etc.)
            # Re-raise as our own exception with context about which endpoint failed
            raise Exception(f"Sleeper API request failed for {endpoint}: {e}")
    
    async def get_user(self, username: str = None) -> Dict[str, Any]:
        """
        Get user information by username
        
        Args:
            username: Sleeper username (defaults to instance username)
            
        Returns:
            Dict containing user information including user_id
        """
        username = username or self.username
        if not username:
            raise ValueError("Username required")
            
        return await self._make_request(f"/user/{username}")
    
    async def get_user_leagues(self, user_id: str, sport: str = "nfl", season: int = 2025) -> List[Dict[str, Any]]:
        """
        Get all leagues for a specific user
        
        Args:
            user_id: Sleeper user ID
            sport: Sport type (default: "nfl")
            season: Season year (default: 2025)
            
        Returns:
            List of league dictionaries
        """
        return await self._make_request(f"/user/{user_id}/leagues/{sport}/{season}")
    
    async def get_league_info(self, league_id: str = None) -> Dict[str, Any]:
        """
        Get league information and settings
        
        Args:
            league_id: League ID (defaults to instance league_id)
            
        Returns:
            Dict containing league information
        """
        league_id = league_id or self.league_id
        if not league_id:
            raise ValueError("League ID required")
            
        return await self._make_request(f"/league/{league_id}")
    
    async def get_league_rosters(self, league_id: str = None) -> List[Dict[str, Any]]:
        """
        Get all rosters in a league
        
        Args:
            league_id: League ID (defaults to instance league_id)
            
        Returns:
            List of roster dictionaries
        """
        league_id = league_id or self.league_id
        if not league_id:
            raise ValueError("League ID required")
            
        return await self._make_request(f"/league/{league_id}/rosters")
    
    async def get_draft_info(self, draft_id: str) -> Dict[str, Any]:
        """
        Get draft information
        
        Args:
            draft_id: Draft ID
            
        Returns:
            Dict containing draft information
        """
        return await self._make_request(f"/draft/{draft_id}")
    
    async def get_draft_picks(self, draft_id: str) -> List[Dict[str, Any]]:
        """
        Get all picks made in a draft
        
        Args:
            draft_id: Draft ID
            
        Returns:
            List of pick dictionaries
        """
        return await self._make_request(f"/draft/{draft_id}/picks")
    
    async def get_all_players(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get all NFL players from Sleeper API (large ~5MB payload)
        
        This method is critical for the draft assistant because:
        1. We need the full player database to filter available players
        2. The payload is huge (~5MB, 11,000+ players) so we cache it
        3. Player data rarely changes during a season, so daily cache is fine
        4. Each player has fantasy_positions, team, rank, etc. that we need
        
        Caching Strategy:
        - Cache file stored in data/players_cache.json
        - Cache expires after 24 hours (86400 seconds)
        - force_refresh parameter bypasses cache for fresh data
        - Cache includes all player metadata: positions, teams, rankings, etc.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data from API
            
        Returns:
            Dict of all NFL players keyed by player_id (e.g., "4881" -> {player data})
            Each player dict contains: first_name, last_name, team, fantasy_positions, 
            search_rank, years_exp, age, injury_status, etc.
        """
        # Define path to our local cache file in the data directory
        cache_file = self.cache_dir / "players_cache.json"
        
        # Check if we should use cached data instead of making API call
        if not force_refresh and cache_file.exists():
            # Calculate how old our cached file is by comparing timestamps
            cache_age = datetime.now().timestamp() - cache_file.stat().st_mtime
            
            # If cache is less than 24 hours old, use cached data
            if cache_age < 86400:  # 24 hours in seconds
                # Load cached player data from JSON file
                with open(cache_file, 'r') as f:
                    self.players_cache = json.load(f)
                    print(f"Loaded {len(self.players_cache)} players from cache")
                    return self.players_cache
        
        # Cache is stale or force_refresh requested - fetch fresh data from API
        print("Fetching fresh player data from Sleeper API...")
        # Make API call to get all NFL players (this is the big 5MB download)
        players_data = await self._make_request("/players/nfl")
        
        # Save the fresh data to cache file for next time
        with open(cache_file, 'w') as f:
            json.dump(players_data, f)
        
        # Store in instance variable for quick access
        self.players_cache = players_data
        print(f"Cached {len(players_data)} players")
        
        return players_data
    
    async def get_available_players(self, draft_id: str, position: str = None) -> List[Dict[str, Any]]:
        """
        Get players still available in the draft - THIS IS THE KEY METHOD FOR DRAFT DAY
        
        This method is crucial during the draft because it tells us who we can actually pick.
        It combines the full player database with current draft picks to show only available players.
        
        Process:
        1. Load full NFL player database (~11,000 players)
        2. Get all picks made so far in this draft
        3. Filter out already-drafted players
        4. Optionally filter by position (QB, RB, WR, TE for SUPERFLEX)
        5. Sort by Sleeper's search rank (lower = better)
        6. Return clean list of available players with key info
        
        Critical for SUPERFLEX leagues:
        - QBs will have very high rankings (2-4) due to SUPERFLEX value
        - Position filtering is essential to see top QBs separately
        
        Args:
            draft_id: The specific draft ID (found in league info)
            position: Optional filter by position ("QB", "RB", "WR", "TE", etc.)
            
        Returns:
            List of player dictionaries, each containing:
            - player_id: Unique Sleeper player identifier
            - name: Full name (first + last)
            - team: NFL team abbreviation (BUF, BAL, etc.)
            - positions: List of fantasy positions (["QB"] or ["RB", "WR"])
            - rank: Sleeper's search rank (lower is better, 1-999)
            - years_exp: Years of NFL experience
            - age: Player's age
            - injury_status: Current injury status if any
        """
        # Step 1: Get the complete NFL player database (cached for performance)
        players = await self.get_all_players()
        
        # Step 2: Get all picks made in this draft so far
        picks = await self.get_draft_picks(draft_id)
        
        # Step 3: Create a set of already-drafted player IDs for fast lookup
        # Using set comprehension for O(1) lookup instead of O(n) list search
        # Only include picks that actually have a player_id (some might be empty)
        drafted_player_ids = {pick['player_id'] for pick in picks if pick.get('player_id')}
        
        # Step 4: Filter through all players to find available ones
        available = []  # Will store our final list of available players
        
        # Loop through every player in the NFL database
        for player_id, player_data in players.items():
            # Check if this player is still available
            # Conditions: not drafted AND currently active in NFL
            if player_id not in drafted_player_ids and player_data.get('active', True):
                
                # Step 5: Apply position filter if specified
                # Get player's fantasy positions (could be multiple like RB/WR)
                positions = player_data.get('fantasy_positions') or []
                
                # If position filter specified, check if player matches
                # If no filter specified, include all positions
                if not position or position in positions:
                    
                    # Step 6: Build clean player info dictionary with key data
                    player_info = {
                        'player_id': player_id,  # Unique identifier
                        
                        # Combine first and last name, handle missing names gracefully
                        'name': f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip(),
                        
                        'team': player_data.get('team'),  # NFL team (BUF, KC, etc.)
                        'positions': positions,  # List of fantasy positions
                        
                        # Search rank from Sleeper (1 is best, 999 is unranked)
                        'rank': player_data.get('search_rank', 999),
                        
                        'years_exp': player_data.get('years_exp', 0),  # NFL experience
                        'age': player_data.get('age'),  # Current age
                        'injury_status': player_data.get('injury_status')  # Injury info
                    }
                    available.append(player_info)
        
        # Step 7: Sort by rank with None value handling
        # Lower rank = better player (Josh Allen = rank 2, backup QB = rank 300+)
        # Handle None values by treating them as rank 999 (unranked)
        available.sort(key=lambda x: x['rank'] if x['rank'] is not None else 999)
        
        return available
    
    async def find_draft_id_for_league(self, league_id: str = None) -> Optional[str]:
        """
        Find the draft ID for a league (useful helper method)
        
        Args:
            league_id: League ID (defaults to instance league_id)
            
        Returns:
            Draft ID if found, None otherwise
        """
        league_info = await self.get_league_info(league_id)
        return league_info.get('draft_id')


# Test functions for development
async def test_sleeper_connection():
    """Test basic Sleeper API connectivity"""
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    if not username or not league_id:
        print("❌ Please set SLEEPER_USERNAME and SLEEPER_LEAGUE_ID in .env file")
        return False
    
    async with SleeperClient(username=username, league_id=league_id) as client:
        try:
            # Test 1: Get user info
            print(f"Testing Sleeper API with username: {username}")
            user = await client.get_user()
            print(f"✅ User found: {user.get('display_name')} (ID: {user.get('user_id')})")
            
            # Test 2: Get league info
            print(f"\nTesting league access with ID: {league_id}")
            league = await client.get_league_info()
            print(f"✅ League found: {league.get('name')} ({league.get('total_rosters')} teams)")
            print(f"   Draft status: {league.get('status')}")
            print(f"   Scoring: {league.get('scoring_settings', {}).get('rec', 'Standard')} PPR")
            
            # Test 3: Check if league has draft
            draft_id = league.get('draft_id')
            if draft_id:
                print(f"   Draft ID: {draft_id}")
                
                # Test 4: Get draft info
                draft_info = await client.get_draft_info(draft_id)
                print(f"   Draft type: {draft_info.get('type')}")
                print(f"   Draft status: {draft_info.get('status')}")
                
                # Test 5: Get any existing picks
                picks = await client.get_draft_picks(draft_id)
                print(f"   Picks made so far: {len(picks)}")
                
            else:
                print("   No draft found for this league")
            
            # Test 6: Load player data
            print(f"\nTesting player data cache...")
            players = await client.get_all_players()
            print(f"✅ Loaded {len(players)} total NFL players")
            
            # Show some sample players
            sample_players = list(players.values())[:3]
            for player in sample_players:
                name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
                positions = ', '.join(player.get('fantasy_positions', []))
                team = player.get('team', 'FA')
                print(f"   Sample: {name} ({positions}) - {team}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing Sleeper API: {e}")
            return False


if __name__ == "__main__":
    # Run test when script is executed directly
    import dotenv
    dotenv.load_dotenv('.env.local')  # Load local credentials first
    dotenv.load_dotenv()              # Fallback to .env
    
    asyncio.run(test_sleeper_connection())