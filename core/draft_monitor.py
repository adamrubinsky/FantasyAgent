"""
Draft Monitor for all platforms
Handles real-time draft monitoring for Sleeper, Yahoo Snake, and Yahoo Auction
"""

import asyncio
import aiohttp
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from .sleeper_player_cache import sleeper_player_cache

logger = logging.getLogger(__name__)


class DraftMonitor:
    """Base class for draft monitoring"""
    
    def __init__(self):
        self.connected_drafts = {}  # Store draft connections by platform
        self.draft_cache = {}  # Cache draft data to reduce API calls
        self.cache_ttl = 30  # Cache for 30 seconds
        self.last_fetch_time = {}
        # Auction-specific tracking
        self._last_auction_pick_count = {}  # Track pick counts by draft_id
        self._last_auction_sale_time = {}   # Track sale times by draft_id
        
    async def connect(self, platform: str, url: str, draft_slot: Optional[int] = None, 
                      team_name: Optional[str] = None) -> Dict[str, Any]:
        """Connect to a draft based on platform"""
        
        # Extract draft ID from URL
        draft_id = self._extract_draft_id(platform, url)
        if not draft_id:
            return {"status": "error", "message": "Invalid draft URL"}
        
        # Store connection info with team identification
        self.connected_drafts[platform] = {
            "url": url,
            "draft_id": draft_id,
            "connected_at": datetime.now().isoformat(),
            "platform": platform,
            "draft_slot": draft_slot,  # User's draft position (1-12)
            "team_name": team_name     # User's team name for auction
        }
        
        logger.info(f"Connected to {platform} draft: {draft_id}, slot: {draft_slot}, team: {team_name}")
        
        return {
            "status": "success",
            "draft_id": draft_id,
            "platform": platform,
            "draft_slot": draft_slot,
            "team_name": team_name
        }
    
    def _extract_draft_id(self, platform: str, url: str) -> Optional[str]:
        """Extract draft ID from URL based on platform"""
        
        if platform in ["sleeper", "sleeper-auction"]:
            # Sleeper URL: https://sleeper.com/draft/nfl/123456789
            match = re.search(r'sleeper\.com/draft/nfl/(\d+)', url)
            if match:
                return match.group(1)
                
        elif platform == "yahoo-snake":
            # Yahoo URLs can be in MANY formats:
            # Mock draft: https://football.fantasysports.yahoo.com/draftclient/f1/1246753/8?auth=...
            # Live draft: https://football.fantasysports.yahoo.com/f1/123456/draft
            # League page: https://football.fantasysports.yahoo.com/f1/123456
            # Team page: https://football.fantasysports.yahoo.com/f1/123456/5
            # Draft results: https://football.fantasysports.yahoo.com/f1/123456/draftresults
            # Mobile: https://football.fantasysports.yahoo.com/m/f1/123456
            
            # Extract league ID - it's always after /f1/ (or /f2/, etc.)
            # This regex looks for /f{number}/{league_id} pattern anywhere in URL
            patterns = [
                r'/draftclient/f\d+/(\d+)',  # Draft client URL
                r'/f\d+/(\d+)',               # Standard league/team URL
                r'/m/f\d+/(\d+)',             # Mobile URL
                r'league_id=(\d+)',           # Query parameter format
                r'/league/(\d+)',             # Alternative format
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    league_id = match.group(1)
                    logger.info(f"Extracted Yahoo league ID: {league_id} from URL: {url}")
                    return league_id
            
            # If no pattern matches, log the URL for debugging
            logger.warning(f"Could not extract league ID from Yahoo URL: {url}")
        
        return None
    
    async def get_draft_status(self, platform: str, url: str = None) -> Dict[str, Any]:
        """Get current draft status for a platform"""
        
        if platform not in self.connected_drafts:
            return {"status": "error", "message": "Not connected to draft"}
        
        draft_info = self.connected_drafts[platform]
        
        # Platform-specific status fetching
        if platform == "sleeper":
            return await self._get_sleeper_status(draft_info["draft_id"])
        elif platform == "sleeper-auction":
            return await self._get_sleeper_auction_status(draft_info["draft_id"])
        elif platform == "yahoo-snake":
            return await self._get_yahoo_snake_status(draft_info["draft_id"])
        
        return {"status": "error", "message": "Unknown platform"}
    
    async def _get_sleeper_status(self, draft_id: str) -> Dict[str, Any]:
        """Get Sleeper draft status"""
        
        try:
            # Sleeper API endpoints
            draft_url = f"https://api.sleeper.app/v1/draft/{draft_id}"
            picks_url = f"https://api.sleeper.app/v1/draft/{draft_id}/picks"
            
            # Create session with SSL verification disabled (macOS certificate issue)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Get draft info
                async with session.get(draft_url) as resp:
                    if resp.status != 200:
                        return {"status": "error", "message": "Failed to fetch draft info"}
                    draft_data = await resp.json()
                
                # Get picks
                async with session.get(picks_url) as resp:
                    if resp.status != 200:
                        picks = []
                    else:
                        picks = await resp.json()
            
            # Extract relevant info
            current_pick = len(picks) + 1
            total_roster_spots = draft_data.get("settings", {}).get("slots_wr", 0) + \
                               draft_data.get("settings", {}).get("slots_rb", 0) + \
                               draft_data.get("settings", {}).get("slots_qb", 0) + \
                               draft_data.get("settings", {}).get("slots_te", 0) + \
                               draft_data.get("settings", {}).get("slots_flex", 0) + \
                               draft_data.get("settings", {}).get("slots_super_flex", 0) + \
                               draft_data.get("settings", {}).get("slots_k", 0) + \
                               draft_data.get("settings", {}).get("slots_def", 0) + \
                               draft_data.get("settings", {}).get("slots_bn", 0)
            
            teams = draft_data.get("settings", {}).get("teams", 12)
            current_round = ((current_pick - 1) // teams) + 1
            
            # Determine if it's user's turn using draft_slot
            draft_info = self.connected_drafts.get("sleeper", {})
            user_slot = draft_info.get("draft_slot")
            my_turn = False
            
            if user_slot:
                # Snake draft logic - odd rounds go 1->12, even rounds go 12->1
                if current_round % 2 == 1:  # Odd round
                    current_drafter = ((current_pick - 1) % teams) + 1
                else:  # Even round
                    current_drafter = teams - ((current_pick - 1) % teams)
                my_turn = (current_drafter == user_slot)
            
            # Get recent picks
            recent_picks = []
            for pick in picks[-5:]:  # Last 5 picks
                recent_picks.append({
                    "player_id": pick.get("player_id"),
                    "picked_by": pick.get("picked_by"),
                    "pick_no": pick.get("pick_no"),
                    "round": pick.get("round"),
                    "metadata": pick.get("metadata", {})
                })
            
            # Get user's roster (all picks by user's draft slot or user ID)
            my_roster = []
            if user_slot:
                # Check if user_slot is a number (draft position) or string (user ID)
                user_id = None
                
                # If it's a number between 1-12, it's a draft slot
                try:
                    slot_num = int(user_slot) if isinstance(user_slot, str) else user_slot
                    if 1 <= slot_num <= 12:
                        # It's a draft slot - find the corresponding user ID
                        slot_to_user = {}
                        for pick in picks[:12]:  # First round picks tell us slot assignments
                            pick_no = pick.get("pick_no", 0)
                            if pick_no > 0 and pick_no <= 12:
                                slot_to_user[pick_no] = pick.get("picked_by")
                        user_id = slot_to_user.get(slot_num)
                        logger.info(f"Draft slot {slot_num} maps to user ID: {user_id}")
                    else:
                        # Number too large to be a slot, treat as user ID
                        user_id = str(user_slot)
                except (ValueError, TypeError):
                    # Not a number, treat as user ID string
                    user_id = str(user_slot)
                    logger.info(f"Using direct user ID: {user_id}")
                
                # Now build roster for that user
                if user_id:
                    for pick in picks:
                        if pick.get("picked_by") == user_id:
                            player_id = pick.get("player_id")
                            # Try to get player info from metadata first (already in the pick)
                            metadata = pick.get("metadata", {})
                            if metadata and metadata.get("first_name"):
                                my_roster.append({
                                    "id": player_id,
                                    "name": f"{metadata.get('first_name', '')} {metadata.get('last_name', '')}".strip(),
                                    "position": metadata.get("position", ""),
                                    "team": metadata.get("team", ""),
                                    "pick": pick.get("pick_no")
                                })
                    
                    logger.info(f"Found {len(my_roster)} players for user {user_id}")
            
            # Get all drafted player names for filtering
            drafted_player_names = []
            for pick in picks:
                metadata = pick.get("metadata", {})
                if metadata and metadata.get("first_name"):
                    name = f"{metadata.get('first_name', '')} {metadata.get('last_name', '')}".strip()
                    if name:
                        drafted_player_names.append(name)
            
            # Also get drafted player IDs for backward compatibility
            drafted_ids = set(pick.get("player_id") for pick in picks if pick.get("player_id"))
            
            # For completed drafts, we'll leave available_players empty 
            # The agent should understand the draft is complete
            available_players = []
            
            # If draft is not complete, we could fetch available players
            # But for now, let's focus on getting the draft picks working
            
            return {
                "status": "success",
                "draftStatus": {
                    "currentPick": current_pick,
                    "round": current_round,
                    "totalPicks": teams * total_roster_spots,
                    "teams": teams,
                    "myTurn": my_turn,
                    "userSlot": user_slot
                },
                "recentPicks": recent_picks,
                "roster": my_roster,
                "draftedPlayerIds": list(drafted_ids),
                "draftedPlayerNames": drafted_player_names,  # All drafted player names
                "draftType": "SUPERFLEX" if draft_data.get("settings", {}).get("slots_super_flex", 0) > 0 else "STANDARD",
                # CRITICAL: Add these for CrewAI context
                "draftPicks": picks,  # All draft picks
                "availablePlayers": available_players  # Players not yet drafted
            }
            
        except Exception as e:
            logger.error(f"Sleeper draft status error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _fetch_yahoo_player_name(self, session, player_key: str, headers: Dict) -> Optional[str]:
        """Fetch player name from Yahoo API using player key"""
        try:
            player_url = f"https://fantasysports.yahooapis.com/fantasy/v2/player/{player_key}"
            async with session.get(player_url, headers=headers) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    
                    # Parse player name from XML
                    import re
                    
                    # Try different name patterns
                    name_patterns = [
                        r'<name>\s*<full>(.*?)</full>',
                        r'<full>(.*?)</full>',
                        r'<player_name>(.*?)</player_name>',
                    ]
                    
                    for pattern in name_patterns:
                        match = re.search(pattern, content)
                        if match:
                            return match.group(1).strip()
                    
                    logger.warning(f"Could not parse name for player {player_key}")
                else:
                    logger.warning(f"Failed to fetch player {player_key}: {resp.status}")
        except Exception as e:
            logger.error(f"Error fetching player {player_key}: {e}")
        return None
    
    async def _get_yahoo_snake_status(self, draft_id: str) -> Dict[str, Any]:
        """Get Yahoo snake draft status with caching to avoid rate limits"""
        
        # Check cache first (30 second TTL to avoid 999 errors)
        cache_key = f"yahoo-snake-{draft_id}"
        if cache_key in self.draft_cache:
            cached_time = self.last_fetch_time.get(cache_key, 0)
            if (datetime.now().timestamp() - cached_time) < self.cache_ttl:
                logger.info(f"Using cached Yahoo data (age: {int(datetime.now().timestamp() - cached_time)}s)")
                return self.draft_cache[cache_key]
        
        try:
            # Use token manager to get valid token (auto-refreshes if needed)
            from core.yahoo_token_manager import token_manager
            
            # This will automatically refresh if token is expired or expiring soon
            access_token = token_manager.get_valid_token()
            
            if not access_token:
                logger.error("Failed to get valid Yahoo token - will be auto-refreshed on next attempt")
                return self._get_yahoo_mock_status(draft_id)
            
            # Yahoo Fantasy API endpoints
            # Use 'nfl' instead of game ID for better compatibility
            league_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/nfl.l.{draft_id}"
            draft_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/nfl.l.{draft_id}/draftresults"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/xml'  # Yahoo returns XML by default
            }
            
            # Disable SSL for macOS
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Get draft results
                async with session.get(draft_url, headers=headers) as resp:
                    if resp.status == 200:
                        # Parse XML response (Yahoo doesn't return JSON for fantasy API)
                        content = await resp.text()
                        
                        # For now, log what we get and return enhanced mock data
                        logger.info(f"Yahoo API response received, length: {len(content)}")
                        
                        # Parse draft picks from XML (more robust parsing)
                        all_picks = []
                        current_pick = 1
                        
                        # Look for draft result entries in XML
                        import re
                        
                        # First try to find draft results
                        picks_pattern = r'<draft_result>(.*?)</draft_result>'
                        picks_matches = re.findall(picks_pattern, content, re.DOTALL)
                        
                        # Cache for player names to avoid redundant API calls
                        player_name_cache = {}
                        
                        if picks_matches:
                            logger.info(f"Found {len(picks_matches)} draft results")
                            
                            # First pass: collect player keys that need names
                            player_keys_to_fetch = []
                            draft_pick_data = []
                            
                            for i, pick_xml in enumerate(picks_matches):
                                # Extract player key first
                                player_key_match = re.search(r'<player_key>(.*?)</player_key>', pick_xml)
                                player_key = player_key_match.group(1) if player_key_match else None
                                
                                # Extract other draft data
                                team_match = re.search(r'<team_key>.*?\.t\.(\d+)</team_key>', pick_xml)
                                pick_match = re.search(r'<pick>(\d+)</pick>', pick_xml)
                                round_match = re.search(r'<round>(\d+)</round>', pick_xml)
                                
                                if player_key and pick_match:
                                    pick_info = {
                                        'player_key': player_key,
                                        'team': int(team_match.group(1)) if team_match else 0,
                                        'pick': int(pick_match.group(1)),
                                        'round': int(round_match.group(1)) if round_match else 0
                                    }
                                    draft_pick_data.append(pick_info)
                                    
                                    # Add to list if we need to fetch the name
                                    if player_key not in player_name_cache:
                                        player_keys_to_fetch.append(player_key)
                                    
                                    current_pick = max(current_pick, int(pick_match.group(1)) + 1)
                            
                            # Fetch player names (batch if needed, limiting API calls)
                            logger.info(f"Need to fetch {len(player_keys_to_fetch)} player names")
                            
                            # BATCH fetch player names to reduce API calls
                            # Fetch enough players to get all roster names (but limit for rate limits)
                            for i, player_key in enumerate(player_keys_to_fetch):
                                player_name = await self._fetch_yahoo_player_name(session, player_key, headers)
                                if player_name:
                                    player_name_cache[player_key] = player_name
                                    logger.info(f"Fetched: {player_key} -> {player_name}")
                                else:
                                    # Use player key as fallback name
                                    player_name_cache[player_key] = player_key
                                
                                # Longer delay to avoid rate limiting (exponential backoff)
                                delay = min(0.5 * (1.5 ** i), 5.0)  # Start at 0.5s, max 5s
                                await asyncio.sleep(delay)
                            
                            # Build final picks list with names
                            for pick_info in draft_pick_data:
                                player_key = pick_info['player_key']
                                player_name = player_name_cache.get(player_key, player_key)
                                
                                all_picks.append({
                                    'player': player_name,
                                    'player_key': player_key,
                                    'position': '',  # Will be fetched with player details if needed
                                    'team': pick_info['team'],
                                    'pick': pick_info['pick'],
                                    'round': pick_info['round']
                                })
                        else:
                            # Try alternative parsing for different XML structures
                            # Pattern 1: Player blocks with draft info
                            player_pattern = r'<player>(.*?)</player>'
                            player_matches = re.findall(player_pattern, content, re.DOTALL)
                            
                            for player_xml in player_matches[:100]:  # Limit to first 100 to avoid parsing entire roster
                                # Check if this has draft pick info
                                if '<pick>' in player_xml or 'draft_round' in player_xml:
                                    player_name = None
                                    
                                    # Try to extract name
                                    name_patterns = [
                                        r'<name>\s*<full>(.*?)</full>',
                                        r'<name>(.*?)</name>',
                                        r'<full>(.*?)</full>'
                                    ]
                                    
                                    for pattern in name_patterns:
                                        name_match = re.search(pattern, player_xml)
                                        if name_match:
                                            player_name = name_match.group(1).strip()
                                            break
                                    
                                    pick_match = re.search(r'<pick>(\d+)</pick>', player_xml)
                                    round_match = re.search(r'<draft_round>(\d+)</draft_round>', player_xml)
                                    team_match = re.search(r'<draft_team>(\d+)</draft_team>', player_xml)
                                    pos_match = re.search(r'<display_position>(.*?)</display_position>', player_xml)
                                    
                                    if player_name and (pick_match or round_match):
                                        pick_num = int(pick_match.group(1)) if pick_match else 0
                                        round_num = int(round_match.group(1)) if round_match else 0
                                        
                                        # Calculate pick from round if not provided
                                        if round_num and not pick_num:
                                            pick_num = (round_num - 1) * 10 + 1  # Estimate
                                        
                                        all_picks.append({
                                            'player': player_name,
                                            'position': pos_match.group(1) if pos_match else "",
                                            'team': int(team_match.group(1)) if team_match else 0,
                                            'pick': pick_num,
                                            'round': round_num
                                        })
                                        if pick_num:
                                            current_pick = max(current_pick, pick_num + 1)
                        
                        logger.info(f"Parsed {len(all_picks)} picks, current pick: {current_pick}")
                        
                        # Get user's draft slot
                        draft_info = self.connected_drafts.get("yahoo-snake", {})
                        user_slot = draft_info.get("draft_slot", 5)
                        teams = 10
                        
                        # Calculate current round and turn
                        current_round = ((current_pick - 1) // teams) + 1
                        
                        # Snake draft logic for turn
                        my_turn = False
                        if current_round % 2 == 1:  # Odd round
                            current_drafter = ((current_pick - 1) % teams) + 1
                        else:  # Even round
                            current_drafter = teams - ((current_pick - 1) % teams)
                        my_turn = (current_drafter == user_slot)
                        
                        # Get user's picks
                        my_picks = [p for p in all_picks if p['team'] == user_slot]
                        
                        # Format roster for UI compatibility
                        roster = []
                        for pick in my_picks:
                            roster.append({
                                "name": pick['player'],
                                "position": pick.get('position', ''),
                                "pick": pick['pick']
                            })
                        
                        # Get drafted player names for filtering
                        drafted_player_names = [p['player'] for p in all_picks if p.get('player')]
                        
                        logger.info(f"Yahoo draft: {len(all_picks)} total picks, {len(roster)} on my roster")
                        
                        # Cache the successful result
                        result = {
                            "status": "success",
                            "draftStatus": {
                                "currentPick": current_pick,
                                "round": current_round,
                                "totalPicks": teams * 16,
                                "teams": teams,
                                "myTurn": my_turn,
                                "userSlot": user_slot
                            },
                            "allPicks": all_picks,
                            "myRoster": my_picks,
                            "roster": roster,  # Formatted for UI
                            "recentPicks": all_picks[-5:] if all_picks else [],
                            "draftedPlayerNames": drafted_player_names,  # For filtering available players
                            "message": "Connected to Yahoo API"
                        }
                        
                        # Store in cache
                        self.draft_cache[cache_key] = result
                        self.last_fetch_time[cache_key] = datetime.now().timestamp()
                        logger.info(f"Cached Yahoo draft data for {self.cache_ttl}s")
                        
                        return result
                    
                    elif resp.status == 401:
                        logger.error("Yahoo token expired, need to refresh")
                        # Try to use cached data if available
                        if cache_key in self.draft_cache:
                            logger.info("Using stale cache due to auth error")
                            return self.draft_cache[cache_key]
                        return self._get_yahoo_mock_status(draft_id)
                    elif resp.status == 999:
                        logger.error("Yahoo rate limit (999) - using cache or mock data")
                        # Use cached data if available, even if stale
                        if cache_key in self.draft_cache:
                            logger.info("Using stale cache due to rate limit")
                            return self.draft_cache[cache_key]
                        return self._get_yahoo_mock_status(draft_id)
                    else:
                        logger.error(f"Yahoo API error: {resp.status}")
                        # Try cache first
                        if cache_key in self.draft_cache:
                            logger.info("Using stale cache due to API error")
                            return self.draft_cache[cache_key]
                        return self._get_yahoo_mock_status(draft_id)
                        
        except Exception as e:
            logger.error(f"Yahoo API error: {e}")
            return self._get_yahoo_mock_status(draft_id)
    
    def _get_yahoo_mock_status(self, draft_id: str) -> Dict[str, Any]:
        """Fallback mock data for Yahoo when API is blocked"""
        draft_info = self.connected_drafts.get("yahoo-snake", {})
        user_slot = draft_info.get("draft_slot", 10)  # Use actual slot provided
        
        # Provide reasonable mock data based on typical draft progress
        import random
        current_pick = random.randint(1, 40)  # Simulate early draft
        teams = 10
        current_round = ((current_pick - 1) // teams) + 1
        
        # Snake draft logic for turn
        my_turn = False
        if current_round % 2 == 1:  # Odd round
            current_drafter = ((current_pick - 1) % teams) + 1
        else:  # Even round
            current_drafter = teams - ((current_pick - 1) % teams)
        my_turn = (current_drafter == user_slot)
        
        return {
            "status": "success",
            "draftStatus": {
                "currentPick": current_pick,
                "round": current_round,
                "totalPicks": 160,
                "teams": teams,
                "myTurn": my_turn,
                "userSlot": user_slot
            },
            "allPicks": [],
            "myRoster": [],
            "roster": [],  # Empty roster for agent
            "recentPicks": [],
            "availablePlayers": [],  # Empty - agent will fetch from FantasyPros
            "message": "Using FantasyPros data (Yahoo API temporarily blocked)"
        }
    
    async def _get_sleeper_auction_status(self, draft_id: str) -> Dict[str, Any]:
        """Get Sleeper auction draft status"""
        
        # Ensure player cache is loaded
        await sleeper_player_cache.ensure_loaded()
        
        try:
            # Sleeper API endpoints for auction
            draft_url = f"https://api.sleeper.app/v1/draft/{draft_id}"
            picks_url = f"https://api.sleeper.app/v1/draft/{draft_id}/picks"
            
            # Create session with SSL verification disabled (macOS certificate issue)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Get draft info
                async with session.get(draft_url) as resp:
                    if resp.status != 200:
                        return {"status": "error", "message": "Failed to fetch draft info"}
                    draft_data = await resp.json()
                
                # Get picks (purchased players in auction)
                async with session.get(picks_url) as resp:
                    if resp.status != 200:
                        picks = []
                    else:
                        picks = await resp.json()
            
            # Get user's team info
            draft_info = self.connected_drafts.get("sleeper-auction", {})
            user_team = draft_info.get("team_name")
            
            # Parse auction-specific data
            draft_type = draft_data.get("type", "snake")
            if draft_type != "auction":
                # It's actually a snake draft, not auction
                return {"status": "error", "message": "This is not an auction draft"}
            
            # Get draft settings
            settings = draft_data.get("settings", {})
            budget = settings.get("budget", 200)  # Default $200
            teams = settings.get("teams", 12)
            
            # Log what we're getting from Sleeper with timestamp
            from datetime import datetime
            now = datetime.now().strftime("%H:%M:%S")
            logger.info(f"[{now}] Sleeper auction draft type: {draft_type}")
            logger.info(f"[{now}] Sleeper auction picks count: {len(picks)}")
            
            # Track if we just had a sale (new pick added)
            # draft_id is passed as parameter to this function
            last_pick_count = self._last_auction_pick_count.get(draft_id, 0)
            just_sold = len(picks) > last_pick_count
            self._last_auction_pick_count[draft_id] = len(picks)
            
            logger.info(f"[{now}] Last pick count: {last_pick_count}, Current: {len(picks)}, Just sold: {just_sold}")
            
            if just_sold and picks:
                latest = picks[-1]
                player_name = f"{latest.get('metadata', {}).get('first_name', '')} {latest.get('metadata', {}).get('last_name', '')}".strip()
                logger.info(f"[{now}] JUST SOLD: {player_name} to team {latest.get('draft_slot')} for ${latest.get('metadata', {}).get('amount', 0)}")
            
            # Check for current nomination - log all metadata to see what's available
            metadata = draft_data.get("metadata", {})
            logger.info(f"[{now}] Draft metadata keys: {list(metadata.keys())[:10]}")  # First 10 keys
            
            # Check various possible fields
            current_nomination = metadata.get("current_nomination")
            nominated_player = metadata.get("nominated_player")
            player_up = metadata.get("player_up")
            
            if current_nomination:
                logger.info(f"[{now}] Current nomination: {current_nomination}")
            if nominated_player:
                logger.info(f"[{now}] Nominated player: {nominated_player}")
            if player_up:
                logger.info(f"[{now}] Player up: {player_up}")
            
            if picks and len(picks) > 0:
                latest_pick = picks[-1]
                logger.info(f"[{now}] Latest pick: Player {latest_pick.get('player_id')} for ${latest_pick.get('metadata', {}).get('amount', 0)}")
            
            # Calculate spent budgets per team
            team_budgets = {i: budget for i in range(1, teams + 1)}
            team_rosters = {i: [] for i in range(1, teams + 1)}
            
            for pick in picks:
                team_id = pick.get("draft_slot")  # In auction, use draft_slot not picked_by
                amount = int(pick.get("metadata", {}).get("amount", "1"))  # Amount might be string
                player_id = pick.get("player_id")
                player_name = f"{pick.get('metadata', {}).get('first_name', '')} {pick.get('metadata', {}).get('last_name', '')}".strip()
                position = pick.get('metadata', {}).get('position', '')
                
                logger.info(f"Processing pick: Team {team_id} bought {player_name} for ${amount}")
                
                if team_id and team_id in team_budgets:
                    team_budgets[team_id] -= amount
                    team_rosters[team_id].append({
                        "player_id": player_id,
                        "name": player_name,
                        "position": position,
                        "price": amount
                    })
            
            # Get current nomination (last pick metadata might have it)
            current_player = None
            current_bid = 0
            high_bidder = None
            
            # Check last_picked field for current nomination
            last_picked = draft_data.get("last_picked")
            if last_picked:
                logger.info(f"Auction last_picked: {last_picked}")
                # This might be the current player up for auction
                current_player = last_picked
            
            # Get current player from metadata
            current_player_name = None
            current_player_id = None
            current_player_position = None
            
            if draft_data.get("metadata"):
                # Current nomination info might be in draft metadata
                logger.info(f"Draft metadata: {draft_data['metadata']}")
                
                # Try to get nominated player ID
                nominated_player_id = draft_data["metadata"].get("nominated_player_id")
                
                # If we just had a sale, clear any stale nomination
                if just_sold and nominated_player_id:
                    logger.info(f"[{now}] Sale just happened - checking if nomination is stale")
                    # Give a 2-second grace period for API to update
                    import time
                    current_time = time.time()
                    last_sale_time = self._last_auction_sale_time.get(draft_id, 0)
                    if current_time - last_sale_time < 2:
                        logger.info(f"[{now}] Within 2s of last sale - treating as no nomination")
                        nominated_player_id = None
                    self._last_auction_sale_time[draft_id] = current_time
                
                if nominated_player_id:
                    # Check if this player has already been purchased
                    player_already_sold = False
                    for pick in picks:
                        if pick.get("player_id") == nominated_player_id:
                            player_already_sold = True
                            sold_to = pick.get("draft_slot")
                            sold_for = pick.get("metadata", {}).get("amount", 0)
                            logger.info(f"[{now}] Nominated player {nominated_player_id} was already sold to team {sold_to} for ${sold_for}")
                            break
                    
                    if not player_already_sold and not just_sold:
                        current_player_id = nominated_player_id
                        # Get player name from cache
                        current_player_name = sleeper_player_cache.get_player_name(nominated_player_id)
                        
                        # Also get player position if available
                        player_info = sleeper_player_cache.get_player_info(nominated_player_id)
                        if player_info:
                            current_player_position = player_info.get("position")
                        
                        logger.info(f"[{now}] Nominated player: {current_player_name} (ID: {nominated_player_id})")
                    else:
                        # Player was already sold, no current nomination
                        logger.info(f"[{now}] No active nomination (previous player was sold or sale just happened)")
                        current_player_id = None
                        current_player_name = None
                
                current_player = current_player_name or draft_data["metadata"].get("current_nomination") or current_player
                
                # Get current bid info
                current_bid = int(draft_data["metadata"].get("highest_offer", 0))
                offering_slot = draft_data["metadata"].get("offering_slot")
                high_bidder = int(offering_slot) if offering_slot else None
            
            # Find user's team ID based on team name or slot number
            user_team_name = draft_info.get("team_name", "1")
            user_team_id = None
            
            # First check if user provided a slot number directly
            if user_team_name.isdigit():
                user_team_id = int(user_team_name)
                logger.info(f"User provided slot number directly: {user_team_id}")
            else:
                # Check draft_order for username mapping (Sleeper auction)
                draft_order = draft_data.get("draft_order")
                if draft_order:
                    logger.info(f"Draft order mapping: {draft_order}")
                    # draft_order is a dict like {"username": slot_number}
                    if user_team_name in draft_order:
                        user_team_id = draft_order[user_team_name]
                        logger.info(f"Found user {user_team_name} at slot {user_team_id}")
                    else:
                        # Try case-insensitive match
                        for username, slot in draft_order.items():
                            if username.lower() == user_team_name.lower():
                                user_team_id = slot
                                logger.info(f"Found user {user_team_name} at slot {user_team_id} (case-insensitive)")
                                break
                
                # If still not found, try parsing the team name
                if user_team_id is None:
                    try:
                        if "team" in user_team_name.lower():
                            # Extract number from "Team X" format
                            import re
                            match = re.search(r'\d+', user_team_name)
                            user_team_id = int(match.group()) if match else 1
                        else:
                            # Default to slot 1 if we can't determine
                            logger.warning(f"Could not determine slot for user '{user_team_name}', defaulting to slot 1")
                            user_team_id = 1
                    except:
                        user_team_id = 1
            
            logger.info(f"User team mapping: '{user_team_name}' -> Team {user_team_id}")
            
            # Get user's budget and roster
            my_budget = team_budgets.get(user_team_id, budget)
            my_roster = team_rosters.get(user_team_id, [])
            
            logger.info(f"User team {user_team_id}: Budget=${my_budget}, Roster={my_roster}")
            
            # Calculate averages
            avg_budget = sum(team_budgets.values()) / len(team_budgets)
            
            # Recent purchases (last 5)
            recent_purchases = []
            for pick in picks[-5:]:
                metadata = pick.get("metadata", {})
                amount = metadata.get("amount", 1)
                first_name = metadata.get("first_name", "")
                last_name = metadata.get("last_name", "")
                player_name = f"{first_name} {last_name}".strip() or f"Player {pick.get('player_id', '')}"
                position = metadata.get("position", "")
                team_slot = pick.get("draft_slot")
                
                recent_purchases.append({
                    "player_id": pick.get("player_id"),
                    "player_name": player_name,
                    "position": position,
                    "price": amount,
                    "team": team_slot
                })
            
            # Build list of all drafted players for the agent
            drafted_players = []
            for pick in picks:
                metadata = pick.get("metadata", {})
                player_name = f"{metadata.get('first_name', '')} {metadata.get('last_name', '')}".strip()
                if player_name:
                    drafted_players.append({
                        "player_id": pick.get("player_id"),
                        "name": player_name,
                        "position": metadata.get("position", ""),
                        "price": int(metadata.get("amount", 0)),
                        "team": pick.get("draft_slot")
                    })
            
            return {
                "status": "success",
                "draftType": "auction",
                "draftStatus": {
                    "currentPlayer": current_player,
                    "currentBid": current_bid,
                    "highBidder": high_bidder,
                    "isMyBid": high_bidder == user_team_id,
                    "myBudget": my_budget,
                    "avgBudget": avg_budget,
                    "totalBudget": budget,
                    "teams": teams,
                    "userTeam": user_team,
                    "picksComplete": len(picks),
                    "totalSlots": teams * 16  # Typical roster size
                },
                "myRoster": my_roster,
                "recentPurchases": recent_purchases,
                "teamBudgets": team_budgets,
                "draftedPlayers": drafted_players
            }
            
        except Exception as e:
            logger.error(f"Sleeper auction status error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_proactive_recommendation(self, platform: str, draft_status: Dict) -> Optional[Dict]:
        """Generate proactive recommendations based on draft status"""
        
        if platform == "sleeper":
            # Check if it's user's turn or almost user's turn (snake draft only)
            if draft_status.get("draftStatus", {}).get("myTurn"):
                return {
                    "title": "It's Your Pick!",
                    "content": "Based on available players and your roster needs, consider targeting a WR or RB with pass-catching upside.",
                    "action": "Draft Garrett Wilson",
                    "actionText": "Get Recommendation"
                }
        
        elif platform == "yahoo-snake":
            current_pick = draft_status.get("draftStatus", {}).get("currentPick", 0)
            next_pick = draft_status.get("draftStatus", {}).get("nextPick", 0)
            
            if next_pick - current_pick <= 3:
                return {
                    "title": "Your Pick Coming Up",
                    "content": f"You pick in {next_pick - current_pick} selections. Start planning for a Full PPR target.",
                    "action": None,
                    "actionText": None
                }
        
        elif platform == "sleeper-auction":
            # For auction, ALWAYS show proactive analysis
            logger.info("Getting proactive analysis for auction draft")
            
            # Check if there's a current player up for auction
            current_player = draft_status.get("draftStatus", {}).get("currentPlayer")
            
            # If no player is currently nominated, show waiting message
            if not current_player:
                logger.info("No active nomination - waiting for next player")
                my_budget = draft_status.get("draftStatus", {}).get("myBudget", 200)
                my_roster = draft_status.get("myRoster", [])
                roster_spots_left = 16 - len(my_roster)
                
                # Build helpful waiting message
                content = "⏳ Waiting for next nomination...\n\n"
                content += f"💰 Budget: ${my_budget}\n"
                content += f"📋 Roster spots left: {roster_spots_left}\n"
                
                # Add position needs
                position_counts = {}
                for p in my_roster:
                    pos = p.get("position", "")
                    position_counts[pos] = position_counts.get(pos, 0) + 1
                
                needs = []
                if position_counts.get("RB", 0) < 2:
                    needs.append("RB")
                if position_counts.get("WR", 0) < 2:
                    needs.append("WR")
                if position_counts.get("QB", 0) < 1:
                    needs.append("QB")
                if position_counts.get("TE", 0) < 1:
                    needs.append("TE")
                
                if needs:
                    content += f"🎯 Priority needs: {', '.join(needs)}\n"
                
                # Add strategy reminder
                stars_acquired = sum(1 for p in my_roster if p.get("price", 0) >= 40)
                if stars_acquired < 3 and my_budget >= 100:
                    content += "\n💡 Strategy: Still looking for elite players"
                elif stars_acquired >= 3:
                    content += "\n💡 Strategy: Focus on value picks now"
                
                return {
                    "title": "Auction Draft",
                    "content": content,
                    "action": None,
                    "actionText": None
                }
            
            # If there's a player up for auction, show max bid analysis
            if current_player:
                logger.info(f"Player up for auction: {current_player}")
                
                # Try to get actual analysis from the agent
                try:
                    from platforms.sleeper.agents.sleeper_auction_crew_fast import SleeperAuctionCrewFast
                    from platforms.sleeper.agents.auction_data_provider import SleeperAuctionDataProvider
                    import asyncio
                    
                    agent = SleeperAuctionCrewFast()
                    data_provider = SleeperAuctionDataProvider()
                    
                    # Build context for analysis
                    my_budget = draft_status.get("draftStatus", {}).get("myBudget", 200)
                    current_bid = draft_status.get("draftStatus", {}).get("currentBid", 0)
                    my_roster = draft_status.get("myRoster", [])
                    roster_spots_left = 16 - len(my_roster)
                    
                    # Get player info - current_player is the name, we might have the ID stored
                    player_id = draft_status.get("draftStatus", {}).get("currentPlayerId")  
                    if not player_id:
                        # Try to extract ID from metadata if available
                        metadata = draft_data.get("metadata", {}) if 'draft_data' in locals() else {}
                        player_id = metadata.get("nominated_player_id")
                    
                    player_info = sleeper_player_cache.get_player_info(player_id) if player_id else None
                    
                    # Get actual auction values from rankings
                    actual_auction_value = None
                    player_position = "WR"  # Default
                    
                    try:
                        # Fetch rankings with auction values (we're already in async context)
                        rankings_data = await data_provider.get_rankings_with_values("HALF")
                        
                        if rankings_data and "auction_values" in rankings_data:
                            auction_values = rankings_data["auction_values"]
                            
                            # Try to get value by player name first (pre-calculated values use names as keys)
                            if current_player and current_player in auction_values:
                                actual_auction_value = auction_values[current_player]
                                logger.info(f"Found pre-calculated auction value for {current_player}: ${actual_auction_value}")
                            # Fall back to player_id lookup if name lookup fails
                            elif player_id and player_id in auction_values:
                                actual_auction_value = auction_values[player_id]
                                logger.info(f"Found auction value by ID for {current_player}: ${actual_auction_value}")
                            
                            # Also try to find player info from rankings
                            if "rankings" in rankings_data:
                                for p in rankings_data["rankings"]:
                                    if p.get("name") == current_player:
                                        player_position = p.get("position", "WR")
                                        if not actual_auction_value:
                                            # Try to get value from player dict
                                            actual_auction_value = p.get("base_auction_value", 0)
                                            if actual_auction_value:
                                                logger.info(f"Found auction value in player data for {current_player}: ${actual_auction_value}")
                                        break
                    except Exception as e:
                        logger.error(f"Could not fetch auction values: {e}")
                    
                    # Use position-based defaults if we can't find actual value
                    default_values = {
                        "RB": 25,  # RBs have wide range
                        "WR": 25,  # WRs similar to RBs
                        "QB": 12,  # QBs cheaper in 4PT TD
                        "TE": 10,  # Most TEs are cheap
                        "DEF": 1,  # Never pay for defense
                        "K": 1     # No kickers in this league
                    }
                    
                    if player_info:
                        player_position = player_info.get("position", player_position)
                        player_dict = {
                            "name": current_player,
                            "position": player_position,
                            "auction_value": actual_auction_value or default_values.get(player_position, 15)
                        }
                    else:
                        # Default if we can't find player info
                        player_dict = {
                            "name": current_player,
                            "position": player_position,
                            "auction_value": actual_auction_value or default_values.get(player_position, 15)
                        }
                    
                    # Start with the actual auction value from rankings
                    base_auction_value = player_dict.get("auction_value", 20)
                    
                    # Calculate what we can absolutely afford
                    max_spendable = max(1, my_budget - roster_spots_left + 1)
                    
                    # Adjust based on YOUR specific situation
                    adjusted_max_bid = base_auction_value  # Start with market value
                    
                    # Budget adjustment based on YOUR situation
                    avg_dollars_per_spot = my_budget / roster_spots_left if roster_spots_left > 0 else 1
                    
                    # If you have more than $12 per roster spot, you're doing well
                    if avg_dollars_per_spot > 12:  # Rich - can pay premiums
                        adjusted_max_bid = int(base_auction_value * 1.1)  # 10% premium
                    elif avg_dollars_per_spot > 8:  # Comfortable - pay fair value
                        adjusted_max_bid = base_auction_value  # Pay market value
                    elif avg_dollars_per_spot > 5:  # Getting tight - need small discounts
                        adjusted_max_bid = int(base_auction_value * 0.9)  # 10% discount
                    else:  # Very tight - only bargains
                        adjusted_max_bid = int(base_auction_value * 0.75)  # 25% discount
                    
                    # Stars & Scrubs strategy adjustment
                    stars_acquired = sum(1 for p in my_roster if p.get("price", 0) >= 40)
                    if stars_acquired < 3 and my_budget >= 140:  # Still need stars
                        if base_auction_value >= 50:  # This is a star player
                            adjusted_max_bid = int(base_auction_value * 1.1)  # Pay up for stars
                    elif stars_acquired >= 3:  # Have your stars
                        if base_auction_value > 20:  # Don't need more expensive players
                            adjusted_max_bid = min(adjusted_max_bid, 10)  # Only bargain hunting now
                    
                    # Never exceed what you can actually afford
                    max_affordable = min(adjusted_max_bid, max_spendable)
                    
                    # Check if we need this position
                    position_counts = {}
                    for p in my_roster:
                        pos = p.get("position", "")
                        position_counts[pos] = position_counts.get(pos, 0) + 1
                    
                    player_pos = player_dict.get("position", "")
                    position_need = "high"
                    
                    # Position need adjustments
                    if player_pos == "WR":
                        if position_counts.get("WR", 0) >= 3:
                            position_need = "low"
                            max_affordable = min(max_affordable, 5)  # Only $1-5 for depth
                        elif position_counts.get("WR", 0) == 0:
                            position_need = "critical"
                            # Might pay slightly over value for first starter
                            max_affordable = int(max_affordable * 1.05)
                    elif player_pos == "RB":
                        if position_counts.get("RB", 0) >= 3:
                            position_need = "low" 
                            max_affordable = min(max_affordable, 5)  # Only $1-5 for depth
                        elif position_counts.get("RB", 0) == 0:
                            position_need = "critical"
                            max_affordable = int(max_affordable * 1.05)
                    elif player_pos == "QB":
                        if position_counts.get("QB", 0) >= 1:
                            position_need = "none"
                            max_affordable = 1  # Already have a QB
                        else:
                            # Cap QB value at $20 due to 4PT passing TDs
                            max_affordable = min(max_affordable, 20)
                    elif player_pos == "TE":
                        if position_counts.get("TE", 0) >= 1:
                            position_need = "low"
                            max_affordable = min(max_affordable, 3)  # Only need cheap backup
                        else:
                            # If it's an elite TE (value > 25), might be worth it
                            if base_auction_value < 25:
                                max_affordable = min(max_affordable, 15)  # Non-elite TE cap
                    
                    # Build recommendation with reasoning
                    content = f"**Max Bid: ${max_affordable}** "
                    content += f"(Market: ${base_auction_value})\n"
                    content += f"Current bid: ${current_bid} | "
                    
                    if max_affordable <= current_bid:
                        content += "⛔ Over your limit\n"
                    elif current_bid < max_affordable * 0.75:
                        content += f"✅ Good value\n"  
                    elif current_bid < max_affordable:
                        content += "⚠️ Approaching max\n"
                    else:
                        content += "❌ Too expensive\n"
                    
                    # Add situational context
                    content += f"\nBudget: ${my_budget} | Spots: {roster_spots_left}\n"
                    
                    # Explain the reasoning
                    if stars_acquired < 3 and base_auction_value >= 50:
                        content += "🎯 Elite player - pay up for stars"
                    elif position_need == "none":
                        content += f"✋ Already have {player_pos}"
                    elif position_need == "low":
                        content += f"📊 Low need at {player_pos}"
                    elif position_need == "critical":
                        content += f"🚨 Need {player_pos} starter"
                    else:
                        content += f"📈 Fair value for roster need"
                    
                    return {
                        "title": f"{current_player}",
                        "content": content,
                        "action": None,
                        "actionText": None
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to get player analysis: {e}", exc_info=True)
                
                # Fallback to simple message
                return {
                    "title": f"Player Up: {current_player}",
                    "content": f"Budget: ${draft_status.get('draftStatus', {}).get('myBudget', 200)}\nUse the chat to get detailed analysis.",
                    "action": None,
                    "actionText": None
                }
            
            # Otherwise show general strategy
            try:
                from platforms.sleeper.agents.sleeper_auction_crew_fast import SleeperAuctionCrewFast
                agent = SleeperAuctionCrewFast()
                
                # Build proper context
                context = {
                    "my_budget": draft_status.get("draftStatus", {}).get("myBudget", 200),
                    "avg_budget": draft_status.get("draftStatus", {}).get("avgBudget", 150),
                    "my_roster": draft_status.get("myRoster", []),
                    "picks_complete": draft_status.get("draftStatus", {}).get("picksComplete", 0),
                    "roster_spots_left": 16 - len(draft_status.get("myRoster", [])),
                    "stars_acquired": 0
                }
                
                logger.info(f"Auction context: {context}")
                
                # Count expensive players as stars
                for player in draft_status.get("myRoster", []):
                    if player.get("price", 0) > 35:
                        context["stars_acquired"] += 1
                
                # For auction drafts, skip the agent and return quick analysis
                if self.platform_type == "sleeper-auction":
                    # Already have all the data we need from above calculations
                    result = {
                        "title": f"Player Up: {current_player}",
                        "content": content,
                        "timing": "immediate",
                        "action": None,
                        "actionText": None
                    }
                    logger.info(f"Quick auction analysis generated - returning immediately")
                    return result
                else:
                    # Get the actual analysis from the agent (snake draft)
                    analysis = agent.get_proactive_analysis(context)
                    logger.info(f"Got proactive analysis from agent: {analysis}")
                    
                    # Format for UI (convert insights list to content string)
                    if "insights" in analysis:
                        content = "\n".join(analysis["insights"])
                        result = {
                            "title": analysis.get("title", "Draft Strategy"),
                            "content": content,
                            "action": None,
                            "actionText": None
                        }
                        logger.info(f"Returning proactive recommendation: {result}")
                        return result
                    return analysis
                
            except Exception as e:
                logger.error(f"Failed to get proactive analysis: {e}", exc_info=True)
                # Fallback to simple message
                my_budget = draft_status.get("draftStatus", {}).get("myBudget", 200)
                return {
                    "title": "Auction Strategy",
                    "content": f"Budget: ${my_budget}. Focus on Stars & Scrubs strategy.",
                    "action": None,
                    "actionText": None
                }
        
        return None


# Global instance
draft_monitor = DraftMonitor()