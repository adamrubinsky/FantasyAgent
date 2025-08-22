"""
Sleeper Auction Data Provider
Integrates Sleeper API data with FantasyPros rankings and auction values
"""

import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from pathlib import Path

# Import FantasyPros client
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from core.official_fantasypros import OfficialFantasyProsMCP

logger = logging.getLogger(__name__)


class SleeperAuctionDataProvider:
    """
    Provides auction data by combining:
    1. FantasyPros rankings and auction values (primary source)
    2. Sleeper draft state and player IDs
    3. Real-time auction status
    """
    
    def __init__(self):
        self.base_url = "https://api.sleeper.app/v1"
        self.player_cache = {}
        self.rankings_cache = None
        self.auction_values_cache = None
        self.cache_timestamp = None
        self.cache_ttl = 300  # 5 minutes for rankings
        
        # Initialize FantasyPros client
        self.fantasypros = OfficialFantasyProsMCP()
        
        # Sleeper to FantasyPros player mapping
        self.player_mapping = {}
    
    async def get_rankings_with_values(self, scoring: str = "HALF") -> Dict[str, Any]:
        """
        Get rankings and calculate auction values using VBD
        Priority: 1) FantasyPros live, 2) Cached, 3) Sleeper API
        
        Returns:
            Dict with rankings and calculated auction values
        """
        # Check cache first
        if self._is_cache_valid():
            return {
                "rankings": self.rankings_cache,
                "auction_values": self.auction_values_cache
            }
        
        rankings = []
        
        # Priority 1: Try FantasyPros MCP (which returns Dict not list)
        try:
            result = await self.fantasypros.get_rankings(
                position="ALL",
                scoring=scoring,  # HALF for Half-PPR
                limit=300
            )
            
            # Extract rankings from the result
            if result:
                if isinstance(result, dict):
                    # FantasyPros returns dict with players inside
                    if 'players' in result:
                        rankings = result['players']
                    else:
                        # Maybe it's already the list
                        rankings = list(result.values()) if result else []
                elif isinstance(result, list):
                    rankings = result
                else:
                    rankings = []
                    
                if rankings:
                    logger.info(f"Got {len(rankings)} players from FantasyPros MCP")
        except Exception as e:
            logger.warning(f"FantasyPros MCP failed: {e}")
        
        # Priority 2: Try cached FantasyPros data
        if not rankings:
            rankings = await self._load_cached_fantasypros()
        
        # Priority 3: Try Sleeper API
        if not rankings:
            rankings = await self._fetch_sleeper_rankings()
        
        # If still no rankings, we have a problem
        if not rankings:
            logger.error("No rankings available from any source!")
            return {
                "rankings": [],
                "auction_values": {}
            }
        
        # Process rankings and calculate auction values using VBD
        processed_rankings = []
        for idx, player in enumerate(rankings):
            # Use the index as rank if rank is missing or 999
            provided_rank = player.get("rank", 999)
            actual_rank = idx + 1 if provided_rank == 999 else provided_rank
            
            player_data = {
                "player_id": player.get("player_id") or player.get("id"),
                "name": player.get("player_name") or player.get("name"),
                "position": str(player.get("player_position_id") or player.get("position", "")).upper(),
                "team": player.get("player_team_id") or player.get("team", ""),
                "rank": actual_rank,  # Use position in list as rank
                "tier": player.get("tier", 99),
                "projected_points": player.get("projected_points", 0),
                "bye_week": player.get("player_bye_week") or player.get("bye", 0)
            }
            processed_rankings.append(player_data)
        
        # Calculate auction values using VBD since FantasyPros doesn't provide them via MCP
        auction_values = self._calculate_vbd_auction_values(processed_rankings)
        
        # Update cache
        self.rankings_cache = processed_rankings
        self.auction_values_cache = auction_values
        self.cache_timestamp = datetime.now()
        
        return {
            "rankings": processed_rankings,
            "auction_values": auction_values
        }
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self.cache_timestamp or not self.rankings_cache:
            return False
        
        age = (datetime.now() - self.cache_timestamp).total_seconds()
        return age < self.cache_ttl
    
    async def _load_cached_fantasypros(self) -> List[Dict]:
        """Load cached FantasyPros data from file if available"""
        try:
            cache_file = Path(__file__).parent.parent.parent.parent / "data" / "fantasypros_cache.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Check if cache is from today
                    cache_date = data.get("date", "")
                    if cache_date == datetime.now().strftime("%Y-%m-%d"):
                        logger.info(f"Using cached FantasyPros data from {cache_date}")
                        return data.get("rankings", [])
        except Exception as e:
            logger.warning(f"Could not load cached FantasyPros: {e}")
        return []
    
    async def _fetch_sleeper_rankings(self) -> List[Dict]:
        """Fetch player rankings from Sleeper API as last resort"""
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Sleeper stores players in a static endpoint
                url = f"{self.base_url}/players/nfl"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        players = await resp.json()
                        
                        # Convert Sleeper format to our format
                        rankings = []
                        for player_id, player_data in players.items():
                            if player_data.get("active") and player_data.get("search_rank"):
                                rankings.append({
                                    "player_id": player_id,
                                    "name": f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}",
                                    "position": player_data.get("position", ""),
                                    "team": player_data.get("team", ""),
                                    "rank": player_data.get("search_rank", 999),
                                    "projected_points": 0  # Sleeper doesn't provide projections
                                })
                        
                        # Sort by rank
                        rankings.sort(key=lambda x: x["rank"])
                        logger.info(f"Got {len(rankings[:200])} players from Sleeper API")
                        return rankings[:200]  # Top 200 only
        except Exception as e:
            logger.error(f"Failed to fetch Sleeper rankings: {e}")
        return []
    
    def _calculate_vbd_auction_values(self, rankings: List[Dict]) -> Dict[str, int]:
        """
        Calculate auction values using simplified rank-based approach
        Since we don't have reliable projections, use rank-based values
        """
        if not rankings:
            return {}
        
        # Constants for 12-team league
        TOTAL_BUDGET = 200 * 12  # $2400 total
        TOTAL_SPOTS = 16 * 12  # 192 roster spots
        RESERVE_PER_SPOT = 1  # $1 minimum bid
        
        # Position baselines (last starter + 1)
        baselines = {
            "QB": 13,  # 12 starters + 1
            "RB": 31,  # 24 starters + 6 flex + 1
            "WR": 37,  # 24 starters + 12 flex potential + 1
            "TE": 13,  # 12 starters + 1
            "DEF": 13,  # 12 starters + 1
            "K": 13    # 12 starters + 1 (if league has kickers)
        }
        
        # Find replacement level points for each position
        replacement_values = {}
        for position, baseline_rank in baselines.items():
            position_players = [p for p in rankings if p.get("position") == position]
            if len(position_players) >= baseline_rank:
                # Use projected points if available, otherwise use rank-based estimate
                replacement_player = position_players[baseline_rank - 1]
                if replacement_player.get("projected_points", 0) > 0:
                    replacement_values[position] = replacement_player["projected_points"]
                else:
                    # Estimate points based on rank if no projections
                    replacement_values[position] = max(50, 300 - (baseline_rank * 10))
            else:
                replacement_values[position] = 50  # Low baseline
        
        # Calculate VBD for each player
        vbd_scores = {}
        total_vbd = 0
        
        for player in rankings:
            position = player.get("position", "FLEX")
            player_id = player.get("player_id")
            
            if not player_id:
                continue
            
            # Get projected points or estimate from rank
            if player.get("projected_points", 0) > 0:
                points = player["projected_points"]
            else:
                # Estimate based on rank
                rank = player.get("rank", 200)
                points = max(50, 350 - (rank * 1.5))
            
            # Calculate VBD
            replacement = replacement_values.get(position, 50)
            vbd = max(0, points - replacement)
            vbd_scores[player_id] = vbd
            total_vbd += vbd
        
        # Convert VBD to auction dollars
        dollars_to_allocate = TOTAL_BUDGET - (TOTAL_SPOTS * RESERVE_PER_SPOT)
        
        # Log VBD calculation details
        if total_vbd == 0:
            logger.warning("Total VBD is 0 - all players will get minimum value")
        else:
            logger.info(f"VBD calculation: total_vbd={total_vbd:.0f}, dollars={dollars_to_allocate}")
        
        auction_values = {}
        
        # If VBD fails, use simple rank-based values
        if total_vbd == 0:
            logger.warning("VBD calculation failed, using rank-based fallback")
            for player in rankings:
                player_id = player.get("player_id")
                if not player_id:
                    continue
                    
                rank = player.get("rank", 200)
                position = player.get("position", "FLEX")
                
                # Simple rank-based formula for auction values
                if rank <= 5:
                    base_value = 60  # Elite tier
                elif rank <= 10:
                    base_value = 50
                elif rank <= 20:
                    base_value = 40
                elif rank <= 30:
                    base_value = 30
                elif rank <= 50:
                    base_value = 20
                elif rank <= 75:
                    base_value = 12
                elif rank <= 100:
                    base_value = 8
                elif rank <= 150:
                    base_value = 4
                else:
                    base_value = 1
                
                # Position adjustments for Half-PPR
                if position == "QB":
                    base_value = min(base_value * 0.5, 20)  # 4PT TDs reduce QB value
                elif position == "TE" and rank > 5:
                    base_value = min(base_value * 0.6, 15)  # Only elite TEs valuable
                elif position == "DEF":
                    base_value = min(base_value, 2)
                elif position == "K":
                    base_value = 1
                
                auction_values[player_id] = max(1, int(base_value))
        else:
            # VBD worked, use it
            for player_id, vbd in vbd_scores.items():
                if total_vbd > 0:
                    # Base value from VBD
                    base_value = (vbd / total_vbd) * dollars_to_allocate + 1
                    
                    # Find player for position/rank adjustments
                    player = next((p for p in rankings if p.get("player_id") == player_id), None)
                    if player:
                        rank = player.get("rank", 200)
                        position = player.get("position", "FLEX")
                        
                        # Stars & Scrubs adjustments
                        if rank <= 10:
                            final_value = base_value * 1.15  # Elite tier
                        elif rank <= 30:
                            final_value = base_value * 1.05  # Premium tier
                        elif rank <= 60:
                            final_value = base_value * 0.85  # Mid-tier (deflate for scrubs)
                        else:
                            final_value = max(1, base_value * 0.7)  # Scrubs
                        
                        # Half-PPR position adjustments
                        if position == "RB" and rank <= 24:
                            final_value *= 1.05  # RBs valuable in Half-PPR
                        elif position == "WR" and rank <= 36:
                            final_value *= 0.98  # WRs slightly less than Full-PPR
                        elif position == "QB":
                            final_value = min(final_value, 20)  # Cap QB value (4PT TDs)
                        elif position == "TE" and rank > 5:
                            final_value *= 0.7  # Only elite TEs matter
                        elif position == "DEF":
                            final_value = min(final_value, 2)  # Never pay for defense
                        elif position == "K":
                            final_value = min(final_value, 1)  # No kickers in this league
                        
                        auction_values[player_id] = max(1, int(final_value))
                    else:
                        auction_values[player_id] = max(1, int(base_value))
                else:
                    auction_values[player_id] = 1
        
        return auction_values
    
    async def get_auction_status(self, draft_id: str) -> Dict[str, Any]:
        """
        Get current auction state from Sleeper
        
        Args:
            draft_id: Sleeper draft ID
            
        Returns:
            Current auction status including budgets and rosters
        """
        try:
            # Create session with SSL verification disabled (macOS issue)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Get draft info
                draft_url = f"{self.base_url}/draft/{draft_id}"
                async with session.get(draft_url) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to fetch draft info: {resp.status}")
                        return {"status": "error"}
                    draft_data = await resp.json()
                
                # Get picks (purchases in auction)
                picks_url = f"{self.base_url}/draft/{draft_id}/picks"
                async with session.get(picks_url) as resp:
                    if resp.status != 200:
                        picks = []
                    else:
                        picks = await resp.json()
            
            # Process auction data
            settings = draft_data.get("settings", {})
            budget = settings.get("budget", 200)
            teams = settings.get("teams", 12)
            
            # Calculate team budgets and rosters
            team_budgets = {i: budget for i in range(1, teams + 1)}
            team_rosters = {i: [] for i in range(1, teams + 1)}
            all_purchases = []
            
            for pick in picks:
                draft_slot = pick.get("draft_slot")
                player_id = pick.get("player_id")
                amount = pick.get("metadata", {}).get("amount", 1)
                
                if draft_slot and draft_slot <= teams:
                    team_budgets[draft_slot] -= amount
                    team_rosters[draft_slot].append({
                        "player_id": player_id,
                        "price": amount
                    })
                    
                    all_purchases.append({
                        "player_id": player_id,
                        "price": amount,
                        "team": draft_slot
                    })
            
            return {
                "status": "success",
                "budget": budget,
                "teams": teams,
                "team_budgets": team_budgets,
                "team_rosters": team_rosters,
                "all_purchases": all_purchases,
                "total_spent": sum(budget - b for b in team_budgets.values()),
                "picks_complete": len(picks)
            }
            
        except Exception as e:
            logger.error(f"Error fetching Sleeper auction status: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_player_details(self, player_id: str) -> Optional[Dict]:
        """
        Get player info with caching
        Maps Sleeper player ID to FantasyPros data
        """
        # Check cache first
        if player_id in self.player_cache:
            return self.player_cache[player_id]
        
        # Try to find in rankings
        if self.rankings_cache:
            for player in self.rankings_cache:
                # This is where we'd need Sleeper-to-FantasyPros mapping
                # For now, try to match by name (not ideal)
                if player.get("player_id") == player_id:
                    self.player_cache[player_id] = player
                    return player
        
        # If not found, create minimal entry
        return {
            "player_id": player_id,
            "name": f"Player {player_id}",
            "position": "FLEX",
            "auction_value": 1
        }
    
    def calculate_team_needs(self, rosters: Dict[int, List]) -> Dict[int, Dict]:
        """
        Analyze what each team needs based on current rosters
        
        Args:
            rosters: Dict mapping team ID to list of purchased players
            
        Returns:
            Dict mapping team ID to position needs
        """
        team_needs = {}
        
        # Required positions for each team
        required = {
            "QB": 1,
            "RB": 2,
            "WR": 2,
            "TE": 1,
            "FLEX": 1,
            "DEF": 1
        }
        
        for team_id, roster in rosters.items():
            # Count positions filled
            position_counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "DEF": 0}
            
            for player_data in roster:
                player_id = player_data.get("player_id")
                # Get player details to find position
                player = asyncio.run(self.get_player_details(player_id))
                if player:
                    position = player.get("position", "FLEX")
                    if position in position_counts:
                        position_counts[position] += 1
            
            # Calculate needs
            needs = {}
            for position, required_count in required.items():
                if position == "FLEX":
                    # Flex can be filled by RB/WR/TE
                    flex_eligible = position_counts["RB"] + position_counts["WR"] + position_counts["TE"]
                    needs["FLEX"] = max(0, 1 - max(0, flex_eligible - 4))  # After filling RB/WR requirements
                else:
                    current = position_counts.get(position, 0)
                    needs[position] = max(0, required_count - current)
            
            # Calculate urgency (positions with 0 filled)
            urgent_needs = [pos for pos, need in needs.items() if need > 0 and position_counts.get(pos, 0) == 0]
            
            team_needs[team_id] = {
                "position_counts": position_counts,
                "needs": needs,
                "urgent": urgent_needs,
                "total_players": len(roster)
            }
        
        return team_needs
    
    def get_positional_scarcity(self, available_players: List[Dict], 
                               team_needs: Dict[int, Dict]) -> Dict[str, float]:
        """
        Calculate scarcity factor for each position
        
        Args:
            available_players: List of undrafted players
            team_needs: Team needs analysis
            
        Returns:
            Dict mapping position to scarcity multiplier
        """
        # Count available starters at each position
        position_counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "DEF": 0}
        
        for player in available_players:
            position = player.get("position", "FLEX")
            rank = player.get("rank", 999)
            
            # Only count likely starters (top 100)
            if rank <= 100 and position in position_counts:
                position_counts[position] += 1
        
        # Count total need for each position
        total_needs = {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "DEF": 0}
        for team_id, needs_data in team_needs.items():
            for position, need in needs_data["needs"].items():
                if position in total_needs:
                    total_needs[position] += need
        
        # Calculate scarcity
        scarcity = {}
        for position in position_counts:
            available = position_counts[position]
            needed = total_needs[position]
            
            if available == 0:
                scarcity[position] = 2.0  # Max scarcity
            elif needed == 0:
                scarcity[position] = 0.5  # No demand
            else:
                # Scarcity increases as need/available ratio increases
                ratio = needed / available
                scarcity[position] = min(1.5, max(0.7, ratio))
        
        return scarcity
    
    async def map_sleeper_to_fantasypros(self, sleeper_id: str) -> Optional[str]:
        """
        Map Sleeper player ID to FantasyPros player ID
        This would ideally use a mapping file, but for now we'll use name matching
        """
        # In production, this would use the unified player mapping from Phase 1
        # For now, return the same ID and let name matching handle it
        return sleeper_id
    
    def calculate_market_inflation(self, purchases: List[Dict]) -> float:
        """
        Calculate market inflation based on actual vs expected prices
        
        Args:
            purchases: List of completed purchases with price
            
        Returns:
            Inflation rate (1.0 = normal, >1.0 = inflated)
        """
        if not purchases or not self.auction_values_cache:
            return 1.0
        
        total_actual = 0
        total_expected = 0
        
        for purchase in purchases:
            player_id = purchase.get("player_id")
            actual_price = purchase.get("price", 0)
            
            # Get expected value from FantasyPros
            expected_price = self.auction_values_cache.get(player_id, actual_price)
            
            total_actual += actual_price
            total_expected += expected_price
        
        if total_expected == 0:
            return 1.0
        
        inflation = total_actual / total_expected
        
        # Log significant inflation/deflation
        if inflation > 1.15:
            logger.info(f"Market is HOT: {inflation:.2f}x expected prices")
        elif inflation < 0.85:
            logger.info(f"Market is COLD: {inflation:.2f}x expected prices")
        
        return inflation