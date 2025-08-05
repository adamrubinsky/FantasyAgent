# Fantasy Football Assistant - API Integration Guide

## Table of Contents
1. [Yahoo Fantasy Sports API](#yahoo-fantasy-sports-api)
2. [Sleeper API](#sleeper-api)
3. [FantasyPros MCP Integration](#fantasypros-mcp-integration)
4. [AgentCore Gateway Setup](#agentcore-gateway-setup)
5. [Error Handling & Rate Limits](#error-handling--rate-limits)

---

## Yahoo Fantasy Sports API

### Initial Setup

```python
# requirements.txt
yfpy==13.0.0
yahoo-oauth==2.0
python-dotenv==1.0.0
```

### OAuth Configuration

```python
# yahoo_auth.py
import os
from pathlib import Path
from yfpy import YahooFantasySportsQuery
from yahoo_oauth import OAuth2
import json

class YahooAuthManager:
    def __init__(self):
        self.auth_dir = Path.home() / '.fantasy_football' / 'auth'
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        
        # Load credentials from environment
        self.client_id = os.getenv('YAHOO_CLIENT_ID')
        self.client_secret = os.getenv('YAHOO_CLIENT_SECRET')
        
    def authenticate(self):
        """Handle OAuth2 flow for Yahoo"""
        oauth = OAuth2(
            self.client_id,
            self.client_secret,
            from_file=self.auth_dir / 'oauth2.json'
        )
        
        if not oauth.token_is_valid():
            # This will open browser for authorization
            oauth.refresh_access_token()
            
        return oauth
    
    def get_query_manager(self, league_id, game_code='nfl', season=2025):
        """Get authenticated query manager for a league"""
        auth = self.authenticate()
        
        return YahooFantasySportsQuery(
            auth_dir=self.auth_dir,
            league_id=league_id,
            game_code=game_code,
            game_id=season,  # This changes each year
            yahoo_consumer_key=self.client_id,
            yahoo_consumer_secret=self.client_secret
        )
```

### Real-time Draft Data

```python
# yahoo_draft_client.py
import asyncio
from typing import Dict, List, Optional
import aiohttp

class YahooDraftClient:
    def __init__(self, query_manager):
        self.query = query_manager
        self.draft_results_cache = {}
        
    async def get_draft_status(self) -> Dict:
        """Check if draft is active and get current pick"""
        league = self.query.get_league_metadata()
        
        return {
            'draft_status': league.draft_status,
            'current_pick': league.current_week,  # During draft, this is pick number
            'my_team_id': self._get_my_team_id()
        }
    
    async def get_available_players(self, position: Optional[str] = None) -> List[Dict]:
        """Get all available players in the draft"""
        # Get all players
        players = self.query.get_league_players(
            player_count_limit=500,  # Adjust based on league size
            player_status='A'  # Available only
        )
        
        available = []
        for player in players:
            player_data = {
                'player_id': player.player_id,
                'name': player.name.full,
                'team': player.editorial_team_abbr,
                'position': player.primary_position,
                'rank': player.rank,
                'adp': player.average_draft_position
            }
            
            if not position or player.primary_position == position:
                available.append(player_data)
                
        # Sort by rank
        return sorted(available, key=lambda x: x.get('rank', 999))
    
    async def get_draft_results(self) -> List[Dict]:
        """Get all picks made so far"""
        draft_results = self.query.get_league_draft_results()
        
        picks = []
        for result in draft_results:
            picks.append({
                'pick_number': result.pick,
                'round': result.round,
                'team_key': result.team_key,
                'player_key': result.player_key,
                'player_name': self._get_player_name(result.player_key)
            })
            
        return sorted(picks, key=lambda x: x['pick_number'])
    
    async def make_draft_pick(self, player_key: str) -> bool:
        """Submit a draft pick"""
        try:
            # This is a POST request through yfpy
            self.query.post_draft_pick(player_key)
            return True
        except Exception as e:
            print(f"Draft pick failed: {e}")
            return False
    
    def _get_my_team_id(self) -> str:
        """Get the user's team ID"""
        teams = self.query.get_league_teams()
        for team in teams:
            if team.is_owned_by_current_login:
                return team.team_id
        return None
```

### WebSocket Integration for Live Updates

```python
# yahoo_websocket.py
import websocket
import json
import threading
from typing import Callable

class YahooDraftWebSocket:
    def __init__(self, league_id: str, on_pick_callback: Callable):
        self.league_id = league_id
        self.on_pick = on_pick_callback
        self.ws = None
        self.running = False
        
    def connect(self):
        """Connect to Yahoo's draft websocket"""
        # Note: Yahoo doesn't have official WebSocket API
        # This is a polling-based alternative
        self.running = True
        self.poll_thread = threading.Thread(target=self._poll_draft)
        self.poll_thread.start()
    
    def _poll_draft(self):
        """Poll for draft updates every 5 seconds"""
        import time
        last_pick = 0
        
        while self.running:
            try:
                # Get current draft state
                current_picks = self._get_draft_picks()
                
                if len(current_picks) > last_pick:
                    # New pick detected
                    new_pick = current_picks[-1]
                    self.on_pick(new_pick)
                    last_pick = len(current_picks)
                    
            except Exception as e:
                print(f"Polling error: {e}")
                
            time.sleep(5)  # Poll every 5 seconds
    
    def disconnect(self):
        """Stop polling"""
        self.running = False
        if self.poll_thread:
            self.poll_thread.join()
```

---

## Sleeper API

### Basic Client Setup

```python
# sleeper_client.py
import aiohttp
import asyncio
from typing import Dict, List, Optional

class SleeperClient:
    BASE_URL = "https://api.sleeper.app/v1"
    
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
    
    async def get_user(self, username: str) -> Dict:
        """Get user information"""
        async with self.session.get(f"{self.BASE_URL}/user/{username}") as resp:
            return await resp.json()
    
    async def get_leagues(self, user_id: str, sport: str = "nfl", season: int = 2025) -> List[Dict]:
        """Get all leagues for a user"""
        url = f"{self.BASE_URL}/user/{user_id}/leagues/{sport}/{season}"
        async with self.session.get(url) as resp:
            return await resp.json()
    
    async def get_draft(self, draft_id: str) -> Dict:
        """Get draft information"""
        async with self.session.get(f"{self.BASE_URL}/draft/{draft_id}") as resp:
            return await resp.json()
    
    async def get_draft_picks(self, draft_id: str) -> List[Dict]:
        """Get all picks in a draft"""
        async with self.session.get(f"{self.BASE_URL}/draft/{draft_id}/picks") as resp:
            return await resp.json()
    
    async def get_players(self) -> Dict:
        """Get all NFL players (large payload ~5MB)"""
        async with self.session.get(f"{self.BASE_URL}/players/nfl") as resp:
            return await resp.json()
```

### Draft Integration

```python
# sleeper_draft.py
from datetime import datetime
import asyncio

class SleeperDraftManager:
    def __init__(self, client: SleeperClient):
        self.client = client
        self.players_cache = {}
        self.draft_state = {}
        
    async def initialize(self, draft_id: str):
        """Load draft and player data"""
        # Load all players (do this once)
        if not self.players_cache:
            self.players_cache = await self.client.get_players()
            
        # Get draft info
        self.draft_state = await self.client.get_draft(draft_id)
        
    async def get_available_players(self, position: Optional[str] = None) -> List[Dict]:
        """Get players still available in draft"""
        # Get all picks made
        picks = await self.client.get_draft_picks(self.draft_state['draft_id'])
        picked_players = {pick['player_id'] for pick in picks if pick['player_id']}
        
        available = []
        for player_id, player in self.players_cache.items():
            if player_id not in picked_players and player.get('active'):
                if not position or position in player.get('fantasy_positions', []):
                    available.append({
                        'player_id': player_id,
                        'name': f"{player.get('first_name', '')} {player.get('last_name', '')}",
                        'team': player.get('team'),
                        'positions': player.get('fantasy_positions', []),
                        'rank': player.get('search_rank', 999)
                    })
        
        return sorted(available, key=lambda x: x['rank'])
    
    async def monitor_draft(self, callback):
        """Monitor draft for updates"""
        last_pick_count = 0
        
        while True:
            picks = await self.client.get_draft_picks(self.draft_state['draft_id'])
            
            if len(picks) > last_pick_count:
                # New picks detected
                new_picks = picks[last_pick_count:]
                for pick in new_picks:
                    await callback(pick)
                last_pick_count = len(picks)
            
            # Check if draft is complete
            if self.draft_state['status'] == 'complete':
                break
                
            await asyncio.sleep(3)  # Check every 3 seconds
```

---

## FantasyPros MCP Integration

### MCP Server Setup

```python
# fantasypros_mcp.py
from mcp import Server, Tool
import aiohttp
from typing import Dict, List

class FantasyProsMCPServer:
    def __init__(self):
        self.server = Server("fantasypros-mcp")
        self.setup_tools()
        
    def setup_tools(self):
        @self.server.tool()
        async def get_rankings(position: str, scoring: str = "PPR") -> Dict:
            """Get expert consensus rankings"""
            # Note: FantasyPros requires API key for direct access
            # This is a mock implementation
            return {
                "position": position,
                "scoring": scoring,
                "rankings": [
                    {"rank": 1, "player": "Christian McCaffrey", "tier": 1},
                    {"rank": 2, "player": "Austin Ekeler", "tier": 1},
                    # ... more players
                ]
            }
        
        @self.server.tool()
        async def get_projections(player_name: str, week: int = 0) -> Dict:
            """Get player projections"""
            return {
                "player": player_name,
                "week": week or "season",
                "projections": {
                    "points": 285.5,
                    "rushing_yards": 1200,
                    "receiving_yards": 450,
                    "touchdowns": 12
                }
            }
        
        @self.server.tool()
        async def get_draft_strategy(league_type: str, pick_position: int) -> Dict:
            """Get draft strategy recommendations"""
            strategies = {
                "PPR": {
                    "early": "RB/WR heavy, wait on QB",
                    "middle": "Best player available",
                    "late": "Zero RB strategy viable"
                }
            }
            
            return {
                "league_type": league_type,
                "pick_position": pick_position,
                "strategy": strategies.get(league_type, {})
            }
```

---

## AgentCore Gateway Setup

### Converting APIs to MCP Tools

```python
# agentcore_gateway_config.py
import boto3
from typing import Dict, List

class AgentCoreGatewayManager:
    def __init__(self):
        self.agentcore = boto3.client('bedrock-agentcore')
        
    async def setup_yahoo_mcp_wrapper(self):
        """Create MCP wrapper for Yahoo API"""
        config = {
            "tool_name": "yahoo_fantasy",
            "description": "Access Yahoo Fantasy Sports data",
            "authentication": {
                "type": "oauth2",
                "client_id": "${YAHOO_CLIENT_ID}",
                "client_secret": "${YAHOO_CLIENT_SECRET}"
            },
            "endpoints": [
                {
                    "name": "get_my_team",
                    "path": "/teams",
                    "method": "GET",
                    "returns": "Team roster and information"
                },
                {
                    "name": "get_available_players",
                    "path": "/players/available",
                    "method": "GET",
                    "parameters": ["position", "limit"],
                    "returns": "List of available players"
                },
                {
                    "name": "submit_draft_pick",
                    "path": "/draft/pick",
                    "method": "POST",
                    "parameters": ["player_id"],
                    "returns": "Confirmation of draft pick"
                }
            ]
        }
        
        response = self.agentcore.create_gateway_tool(
            ToolName='yahoo_fantasy',
            ToolConfiguration=config,
            Protocol='MCP'
        )
        
        return response['ToolArn']
    
    async def setup_sleeper_mcp_wrapper(self):
        """Create MCP wrapper for Sleeper API"""
        config = {
            "tool_name": "sleeper_fantasy",
            "description": "Access Sleeper Fantasy Football data",
            "authentication": {
                "type": "none"  # Sleeper is public
            },
            "endpoints": [
                {
                    "name": "get_league_info",
                    "path": "/league/{league_id}",
                    "method": "GET",
                    "returns": "League settings and information"
                },
                {
                    "name": "get_rosters",
                    "path": "/league/{league_id}/rosters",
                    "method": "GET",
                    "returns": "All rosters in the league"
                },
                {
                    "name": "get_draft_picks",
                    "path": "/draft/{draft_id}/picks",
                    "method": "GET",
                    "returns": "All picks in the draft"
                }
            ]
        }
        
        response = self.agentcore.create_gateway_tool(
            ToolName='sleeper_fantasy',
            ToolConfiguration=config,
            Protocol='MCP'
        )
        
        return response['ToolArn']
```

### Unified API Interface

```python
# unified_api_client.py
from typing import Dict, List, Optional
import asyncio

class UnifiedFantasyAPIClient:
    """Unified interface for all fantasy platforms via MCP"""
    
    def __init__(self, agentcore_runtime):
        self.runtime = agentcore_runtime
        self.tools = {}
        
    async def initialize(self):
        """Register all MCP tools"""
        self.tools['yahoo'] = await self.runtime.load_tool('yahoo_fantasy')
        self.tools['sleeper'] = await self.runtime.load_tool('sleeper_fantasy')
        self.tools['fantasypros'] = await self.runtime.load_tool('fantasypros_mcp')
        
    async def get_available_players(self, platform: str, **kwargs) -> List[Dict]:
        """Get available players from any platform"""
        tool = self.tools.get(platform)
        if not tool:
            raise ValueError(f"Unknown platform: {platform}")
            
        if platform == 'yahoo':
            return await tool.get_available_players(**kwargs)
        elif platform == 'sleeper':
            # Sleeper requires different approach
            players = await tool.get_players()
            draft_picks = await tool.get_draft_picks(kwargs.get('draft_id'))
            # Filter logic here
            return self._filter_available_sleeper(players, draft_picks)
            
    async def get_expert_rankings(self, position: str, scoring: str = "PPR") -> List[Dict]:
        """Get rankings from FantasyPros"""
        return await self.tools['fantasypros'].get_rankings(
            position=position,
            scoring=scoring
        )
    
    async def submit_pick(self, platform: str, player_id: str) -> bool:
        """Submit a draft pick to the platform"""
        tool = self.tools.get(platform)
        
        if platform == 'yahoo':
            return await tool.submit_draft_pick(player_id=player_id)
        elif platform == 'sleeper':
            # Sleeper doesn't have API for picks
            raise NotImplementedError("Sleeper pick submission requires app")
```

---

## Error Handling & Rate Limits

### Rate Limit Manager

```python
# rate_limiter.py
import asyncio
import time
from functools import wraps

class RateLimiter:
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = []
        self.lock = asyncio.Lock()
        
    async def acquire(self):
        """Wait if necessary to respect rate limit"""
        async with self.lock:
            now = time.time()
            # Remove calls older than 1 minute
            self.calls = [t for t in self.calls if now - t < 60]
            
            if len(self.calls) >= self.calls_per_minute:
                # Need to wait
                sleep_time = 60 - (now - self.calls[0]) + 0.1
                await asyncio.sleep(sleep_time)
                # Recursive call after waiting
                return await self.acquire()
            
            self.calls.append(now)

def rate_limited(limiter: RateLimiter):
    """Decorator for rate-limited API calls"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await limiter.acquire()
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage example
yahoo_limiter = RateLimiter(calls_per_minute=60)
sleeper_limiter = RateLimiter(calls_per_minute=100)

class APIClient:
    @rate_limited(yahoo_limiter)
    async def yahoo_api_call(self, endpoint: str):
        # Make API call
        pass
```

### Error Handling

```python
# error_handling.py
import logging
from typing import Optional, Dict, Any
from enum import Enum

class APIError(Exception):
    """Base API error"""
    pass

class AuthenticationError(APIError):
    """Authentication failed"""
    pass

class RateLimitError(APIError):
    """Rate limit exceeded"""
    pass

class DraftNotActiveError(APIError):
    """Draft is not currently active"""
    pass

class APIErrorHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.retry_config = {
            'max_retries': 3,
            'backoff_factor': 2,
            'retry_on': [500, 502, 503, 504]
        }
    
    async def handle_api_call(self, func, *args, **kwargs):
        """Wrapper for API calls with error handling"""
        retries = 0
        last_error = None
        
        while retries < self.retry_config['max_retries']:
            try:
                return await func(*args, **kwargs)
                
            except aiohttp.ClientResponseError as e:
                if e.status == 401:
                    raise AuthenticationError("Invalid credentials")
                elif e.status == 429:
                    # Rate limited
                    wait_time = int(e.headers.get('Retry-After', 60))
                    self.logger.warning(f"Rate limited, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                elif e.status in self.retry_config['retry_on']:
                    # Retryable error
                    wait_time = self.retry_config['backoff_factor'] ** retries
                    self.logger.warning(f"Retryable error {e.status}, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    retries += 1
                    last_error = e
                else:
                    # Non-retryable error
                    raise APIError(f"API error: {e.status} - {e.message}")
                    
            except asyncio.TimeoutError:
                self.logger.error("API call timed out")
                retries += 1
                last_error = "Timeout"
                
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                raise
        
        # Max retries exceeded
        raise APIError(f"Max retries exceeded. Last error: {last_error}")
```

### Integration Example

```python
# main_api_integration.py
async def main():
    """Example of using all APIs together"""
    
    # Initialize clients
    yahoo_auth = YahooAuthManager()
    yahoo_query = yahoo_auth.get_query_manager(league_id="12345")
    yahoo_client = YahooDraftClient(yahoo_query)
    
    async with SleeperClient() as sleeper:
        sleeper_draft = SleeperDraftManager(sleeper)
        await sleeper_draft.initialize(draft_id="67890")
        
        # Initialize AgentCore Gateway
        gateway = AgentCoreGatewayManager()
        unified_client = UnifiedFantasyAPIClient(gateway)
        await unified_client.initialize()
        
        # Get available players from both platforms
        yahoo_players = await yahoo_client.get_available_players(position="RB")
        sleeper_players = await sleeper_draft.get_available_players(position="RB")
        
        # Get expert rankings
        rankings = await unified_client.get_expert_rankings(
            position="RB",
            scoring="PPR"
        )
        
        # Combine and analyze
        print(f"Yahoo: {len(yahoo_players)} RBs available")
        print(f"Sleeper: {len(sleeper_players)} RBs available")
        print(f"Top ranked available: {rankings[0]}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Testing & Development

### Mock API Server

```python
# mock_api_server.py
from aiohttp import web
import json

class MockFantasyAPIServer:
    """Mock server for development/testing"""
    
    def __init__(self):
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        self.app.router.add_get('/players/available', self.get_available_players)
        self.app.router.add_post('/draft/pick', self.submit_pick)
        self.app.router.add_get('/draft/status', self.get_draft_status)
        
    async def get_available_players(self, request):
        """Mock available players endpoint"""
        position = request.query.get('position')
        
        mock_players = [
            {
                "player_id": "CMC2023",
                "name": "Christian McCaffrey",
                "position": "RB",
                "team": "SF",
                "rank": 1
            },
            # Add more mock players
        ]
        
        if position:
            mock_players = [p for p in mock_players if p['position'] == position]
            
        return web.json_response(mock_players)
    
    async def submit_pick(self, request):
        """Mock pick submission"""
        data = await request.json()
        return web.json_response({
            "success": True,
            "player_id": data.get('player_id'),
            "pick_number": 15
        })
    
    def run(self, port=8080):
        web.run_app(self.app, port=port)
```

---

## Best Practices

1. **Always use rate limiting** - Respect API limits to avoid bans
2. **Cache player data** - The full player list rarely changes during a draft
3. **Handle authentication refresh** - OAuth tokens expire, handle gracefully
4. **Use async operations** - Draft monitoring requires concurrent operations
5. **Implement circuit breakers** - Fail fast if APIs are down
6. **Log all API calls** - Essential for debugging during live drafts
7. **Test with mock data** - Don't waste API calls during development
8. **Store credentials securely** - Use AWS Secrets Manager or environment variables