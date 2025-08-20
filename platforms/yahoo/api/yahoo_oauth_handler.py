"""
Yahoo OAuth Handler with fallback options
"""

import os
import json
import time
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class YahooOAuthHandler:
    """Handle Yahoo OAuth with multiple fallback strategies"""
    
    def __init__(self):
        self.client_id = os.getenv('YAHOO_CLIENT_ID')
        self.client_secret = os.getenv('YAHOO_CLIENT_SECRET')
        self.token_file = Path('private/yahoo_token.json')
        self.token_file.parent.mkdir(exist_ok=True)
        
        # Load existing token if available
        self.token_data = self._load_token()
        
    def _load_token(self) -> Optional[Dict]:
        """Load token from file if exists"""
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    # Check if token is still valid
                    expires_at = datetime.fromisoformat(data.get('expires_at', ''))
                    if expires_at > datetime.now():
                        logger.info("Loaded valid Yahoo token from cache")
                        return data
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")
        return None
    
    def _save_token(self, token_data: Dict):
        """Save token to file"""
        # Add expiration time (usually 1 hour for Yahoo)
        token_data['expires_at'] = (
            datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
        ).isoformat()
        
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        logger.info("Saved Yahoo token to cache")
    
    async def get_access_token(self) -> Optional[str]:
        """Get valid access token, refreshing if needed"""
        
        # Check cached token
        if self.token_data:
            return self.token_data.get('access_token')
        
        # Try to get new token (requires manual OAuth flow)
        logger.warning("No valid Yahoo token. Manual OAuth required.")
        return None
    
    async def exchange_code_for_token(self, auth_code: str) -> Optional[Dict]:
        """Exchange authorization code for access token"""
        
        token_url = "https://api.login.yahoo.com/oauth2/get_token"
        
        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': 'oob',  # Out of band for CLI apps
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    self._save_token(token_data)
                    self.token_data = token_data
                    return token_data
                else:
                    error = await resp.text()
                    logger.error(f"Token exchange failed: {error}")
                    return None
    
    async def refresh_token(self) -> Optional[Dict]:
        """Refresh expired token"""
        
        if not self.token_data or 'refresh_token' not in self.token_data:
            logger.error("No refresh token available")
            return None
        
        token_url = "https://api.login.yahoo.com/oauth2/get_token"
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.token_data['refresh_token'],
            'redirect_uri': 'oob',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    self._save_token(token_data)
                    self.token_data = token_data
                    logger.info("Successfully refreshed Yahoo token")
                    return token_data
                else:
                    error = await resp.text()
                    logger.error(f"Token refresh failed: {error}")
                    return None
    
    async def make_api_request(self, endpoint: str) -> Optional[Dict]:
        """Make authenticated API request to Yahoo"""
        
        token = await self.get_access_token()
        if not token:
            logger.error("No access token available")
            return None
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 401:
                    # Token expired, try refresh
                    logger.info("Token expired, attempting refresh...")
                    if await self.refresh_token():
                        # Retry with new token
                        return await self.make_api_request(endpoint)
                else:
                    error = await resp.text()
                    logger.error(f"API request failed: {error}")
                    return None
    
    def get_auth_url(self) -> str:
        """Get the authorization URL for manual OAuth"""
        return (
            f"https://api.login.yahoo.com/oauth2/request_auth?"
            f"client_id={self.client_id}&"
            f"redirect_uri=oob&"
            f"response_type=code&"
            f"language=en-us"
        )


class YahooManualMode:
    """Fallback mode for manual draft tracking"""
    
    def __init__(self):
        self.draft_state = {
            'current_pick': 1,
            'current_round': 1,
            'all_picks': [],
            'my_picks': [],
            'draft_slot': None
        }
    
    def set_draft_slot(self, slot: int):
        """Set user's draft position"""
        self.draft_state['draft_slot'] = slot
    
    def record_pick(self, player_name: str, team_slot: int, pick_number: int):
        """Manually record a draft pick"""
        pick = {
            'player': player_name,
            'team': team_slot,
            'pick': pick_number,
            'round': (pick_number - 1) // 10 + 1  # Assuming 10 teams
        }
        
        self.draft_state['all_picks'].append(pick)
        
        if team_slot == self.draft_state['draft_slot']:
            self.draft_state['my_picks'].append(pick)
        
        self.draft_state['current_pick'] = pick_number + 1
        self.draft_state['current_round'] = (pick_number) // 10 + 1
    
    def get_draft_status(self) -> Dict:
        """Get current draft status"""
        return {
            'status': 'success',
            'mode': 'manual',
            'draftStatus': {
                'currentPick': self.draft_state['current_pick'],
                'round': self.draft_state['current_round'],
                'myTurn': self._is_my_turn(),
                'userSlot': self.draft_state['draft_slot']
            },
            'myRoster': self.draft_state['my_picks'],
            'recentPicks': self.draft_state['all_picks'][-5:],
            'message': 'Manual mode - enter picks as they happen'
        }
    
    def _is_my_turn(self) -> bool:
        """Check if it's user's turn in snake draft"""
        if not self.draft_state['draft_slot']:
            return False
        
        current_pick = self.draft_state['current_pick']
        current_round = self.draft_state['current_round']
        slot = self.draft_state['draft_slot']
        
        # Snake draft logic
        if current_round % 2 == 1:  # Odd round
            return ((current_pick - 1) % 10) + 1 == slot
        else:  # Even round
            return 10 - ((current_pick - 1) % 10) == slot


# Test function
async def test_oauth():
    """Test Yahoo OAuth flow"""
    handler = YahooOAuthHandler()
    
    # Check if we have a valid token
    token = await handler.get_access_token()
    
    if token:
        print(f"✅ Have valid token: {token[:20]}...")
        
        # Try to get league info
        league_id = os.getenv('YAHOO_SNAKE_LEAGUE_ID', '475629')
        endpoint = f"https://fantasysports.yahooapis.com/fantasy/v2/league/nfl.l.{league_id}"
        
        result = await handler.make_api_request(endpoint)
        if result:
            print("✅ Successfully connected to Yahoo API!")
            return True
    
    print("❌ No valid token. Showing auth URL...")
    print(f"\nAuth URL: {handler.get_auth_url()}")
    print("\n1. Visit the URL above")
    print("2. Authorize the app")
    print("3. Copy the code from the URL")
    print("4. We'll exchange it for a token")
    
    return False


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_oauth())