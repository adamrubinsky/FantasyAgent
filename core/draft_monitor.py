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

logger = logging.getLogger(__name__)


class DraftMonitor:
    """Base class for draft monitoring"""
    
    def __init__(self):
        self.connected_drafts = {}  # Store draft connections by platform
        
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
            # Yahoo URL: https://football.fantasysports.yahoo.com/f1/123456/draft
            match = re.search(r'yahoo\.com/f\d+/(\d+)', url)
            if match:
                return match.group(1)
        
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
                "draftType": "SUPERFLEX" if draft_data.get("settings", {}).get("slots_super_flex", 0) > 0 else "STANDARD"
            }
            
        except Exception as e:
            logger.error(f"Sleeper draft status error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _get_yahoo_snake_status(self, draft_id: str) -> Dict[str, Any]:
        """Get Yahoo snake draft status"""
        
        # Note: Yahoo doesn't have a public API for draft status
        # In production, you'd need to use web scraping or OAuth
        # For now, return mock data
        
        # Get user's draft slot for Yahoo Snake
        draft_info = self.connected_drafts.get("yahoo-snake", {})
        user_slot = draft_info.get("draft_slot")
        
        # Mock data with user slot logic
        current_pick = 25
        teams = 10
        current_round = 3
        
        # Determine if it's user's turn (snake draft logic)
        my_turn = False
        if user_slot:
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
                "nextPick": 28,
                "totalPicks": 160,
                "teams": teams,
                "myTurn": my_turn,
                "userSlot": user_slot
            },
            "recentPicks": [
                {"player": "Justin Jefferson", "team": 3, "pick": 21},
                {"player": "Davante Adams", "team": 4, "pick": 22},
                {"player": "Travis Kelce", "team": 5, "pick": 23},
                {"player": "Stefon Diggs", "team": 6, "pick": 24}
            ],
            "message": "Yahoo API integration pending - using mock data"
        }
    
    async def _get_sleeper_auction_status(self, draft_id: str) -> Dict[str, Any]:
        """Get Sleeper auction draft status"""
        
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
            
            # Log what we're getting from Sleeper
            logger.info(f"Sleeper auction draft type: {draft_type}")
            logger.info(f"Sleeper auction picks count: {len(picks)}")
            logger.info(f"Draft data keys: {draft_data.keys()}")
            if picks:
                logger.info(f"Sample pick: {picks[0]}")
            
            # Calculate spent budgets per team
            team_budgets = {i: budget for i in range(1, teams + 1)}
            team_rosters = {i: [] for i in range(1, teams + 1)}
            
            for pick in picks:
                team_id = pick.get("picked_by")
                amount = pick.get("metadata", {}).get("amount", 1)
                player_id = pick.get("player_id")
                
                if team_id and team_id in team_budgets:
                    team_budgets[team_id] -= amount
                    team_rosters[team_id].append({
                        "player_id": player_id,
                        "price": amount
                    })
            
            # Get current nomination (last pick metadata might have it)
            current_player = None
            current_bid = 0
            high_bidder = None
            
            if draft_data.get("metadata"):
                # Current nomination info might be in draft metadata
                current_player = draft_data["metadata"].get("current_nomination")
                current_bid = draft_data["metadata"].get("current_bid", 0)
                high_bidder = draft_data["metadata"].get("high_bidder")
            
            # Find user's team ID based on team name
            # For mock drafts, try to match team name to a number or use it directly
            user_team_name = draft_info.get("team_name", "1")
            
            # Try to parse team number from name (e.g., "Team 1" or just "1")
            try:
                if user_team_name.isdigit():
                    user_team_id = int(user_team_name)
                elif "team" in user_team_name.lower():
                    # Extract number from "Team X" format
                    import re
                    match = re.search(r'\d+', user_team_name)
                    user_team_id = int(match.group()) if match else 1
                else:
                    # Default to team 1 if can't parse
                    user_team_id = 1
            except:
                user_team_id = 1
            
            logger.info(f"User team mapping: '{user_team_name}' -> Team {user_team_id}")
            
            # Get user's budget and roster
            my_budget = team_budgets.get(user_team_id, budget)
            my_roster = team_rosters.get(user_team_id, [])
            
            # Calculate averages
            avg_budget = sum(team_budgets.values()) / len(team_budgets)
            
            # Recent purchases (last 5)
            recent_purchases = []
            for pick in picks[-5:]:
                amount = pick.get("metadata", {}).get("amount", 1)
                recent_purchases.append({
                    "player_id": pick.get("player_id"),
                    "price": amount,
                    "team": pick.get("picked_by")
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
                "teamBudgets": team_budgets
            }
            
        except Exception as e:
            logger.error(f"Sleeper auction status error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_proactive_recommendation(self, platform: str, draft_status: Dict) -> Optional[Dict]:
        """Generate proactive recommendations based on draft status"""
        
        if platform in ["sleeper", "sleeper-auction"]:
            # Check if it's user's turn or almost user's turn
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
            my_budget = draft_status.get("draftStatus", {}).get("myBudget", 200)
            avg_budget = draft_status.get("draftStatus", {}).get("avgBudget", 200)
            picks_complete = draft_status.get("draftStatus", {}).get("picksComplete", 0)
            
            # Recommend nomination strategy based on draft phase
            if picks_complete < 50:  # Early phase
                return {
                    "title": "Nomination Strategy",
                    "content": f"You have ${my_budget} (avg: ${avg_budget:.0f}). Nominate expensive QBs ($25-40) to drain budgets.",
                    "action": "Nominate a QB",
                    "actionText": "See QB Options"
                }
            elif my_budget > avg_budget + 20:  # Budget advantage
                return {
                    "title": "Budget Advantage!",
                    "content": f"You have ${my_budget} vs avg ${avg_budget:.0f}. Target a stud RB/WR now!",
                    "action": "Target elite player",
                    "actionText": "Show Top Available"
                }
            else:  # Value hunting phase
                return {
                    "title": "Value Hunting Mode",
                    "content": f"With ${my_budget} left, look for $1-5 sleepers and handcuffs.",
                    "action": "Find value picks",
                    "actionText": "Show Sleepers"
                }
        
        return None


# Global instance
draft_monitor = DraftMonitor()