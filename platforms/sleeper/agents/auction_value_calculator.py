"""
Auction Value Calculator for Sleeper League 3
Uses Value-Based Drafting (VBD) methodology with Half-PPR adjustments
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LeagueSettings:
    """League configuration for auction calculations"""
    budget: int = 200
    teams: int = 12
    roster_spots: int = 16
    scoring: str = "HALF_PPR"
    positions: Dict[str, int] = None
    
    def __post_init__(self):
        if self.positions is None:
            self.positions = {
                "QB": 1,
                "RB": 2,
                "WR": 2,
                "TE": 1,
                "FLEX": 1,  # W/R/T
                "DEF": 1,
                "BENCH": 5,
                "IR": 1
            }


class AuctionValueCalculator:
    """
    Calculate auction values using VBD methodology
    Optimized for Half-PPR scoring and Stars & Scrubs strategy
    """
    
    def __init__(self, league_settings: LeagueSettings = None):
        self.settings = league_settings or LeagueSettings()
        
        # Total auction dollars in league
        self.total_dollars = self.settings.budget * self.settings.teams
        
        # Total roster spots to fill
        self.total_roster_spots = self.settings.roster_spots * self.settings.teams
        
        # Dollars per roster spot (baseline)
        self.baseline_value = self.total_dollars / self.total_roster_spots
        
        # Position baselines (how many starters at each position)
        self.position_baselines = self._calculate_position_baselines()
        
        # Cache for calculated values
        self.value_cache = {}
    
    def _calculate_position_baselines(self) -> Dict[str, int]:
        """Calculate how many players at each position are starters"""
        baselines = {}
        teams = self.settings.teams
        
        # Starting positions across all teams
        baselines["QB"] = self.settings.positions["QB"] * teams  # 12
        baselines["RB"] = (self.settings.positions["RB"] * teams) + (teams // 2)  # 24 + 6 flex
        baselines["WR"] = (self.settings.positions["WR"] * teams) + (teams // 2)  # 24 + 6 flex
        baselines["TE"] = self.settings.positions["TE"] * teams  # 12
        baselines["DEF"] = self.settings.positions["DEF"] * teams  # 12
        
        return baselines
    
    def calculate_vbd_values(self, rankings: List[Dict]) -> Dict[str, float]:
        """
        Calculate auction values using VBD methodology
        
        Args:
            rankings: List of player dicts with rank, position, projected_points
            
        Returns:
            Dict mapping player_id to auction value
        """
        if not rankings:
            return {}
        
        # Step 1: Find replacement level at each position
        replacement_values = self._find_replacement_values(rankings)
        
        # Step 2: Calculate VBD (points above replacement) for each player
        vbd_scores = {}
        for player in rankings:
            position = player.get("position", "FLEX")
            player_id = player.get("player_id") or player.get("id")
            projected_points = player.get("projected_points", 0)
            
            if not player_id:
                continue
            
            # Calculate VBD
            replacement = replacement_values.get(position, 0)
            vbd = max(0, projected_points - replacement)
            vbd_scores[player_id] = vbd
        
        # Step 3: Convert VBD to dollar values
        auction_values = self._convert_vbd_to_dollars(vbd_scores, rankings)
        
        # Step 4: Apply Half-PPR adjustments
        auction_values = self._apply_scoring_adjustments(auction_values, rankings)
        
        # Cache the values
        self.value_cache.update(auction_values)
        
        return auction_values
    
    def _find_replacement_values(self, rankings: List[Dict]) -> Dict[str, float]:
        """Find the replacement level player at each position"""
        position_players = {}
        
        # Group players by position
        for player in rankings:
            position = player.get("position", "FLEX")
            if position not in position_players:
                position_players[position] = []
            position_players[position].append(player.get("projected_points", 0))
        
        # Sort and find replacement level
        replacement_values = {}
        for position, baseline_count in self.position_baselines.items():
            if position in position_players:
                sorted_points = sorted(position_players[position], reverse=True)
                # Replacement level is the last starter + 1
                if len(sorted_points) > baseline_count:
                    replacement_values[position] = sorted_points[baseline_count]
                else:
                    replacement_values[position] = sorted_points[-1] if sorted_points else 0
            else:
                replacement_values[position] = 0
        
        return replacement_values
    
    def _convert_vbd_to_dollars(self, vbd_scores: Dict[str, float], 
                                rankings: List[Dict]) -> Dict[str, float]:
        """Convert VBD scores to auction dollar values"""
        if not vbd_scores:
            return {}
        
        # Total VBD points
        total_vbd = sum(vbd_scores.values())
        
        # Reserve $1 for each roster spot (minimum bids)
        dollars_to_allocate = self.total_dollars - self.total_roster_spots
        
        # Allocate dollars proportionally to VBD
        auction_values = {}
        for player_id, vbd in vbd_scores.items():
            if total_vbd > 0:
                # Base value from VBD
                dollar_value = (vbd / total_vbd) * dollars_to_allocate + 1
                
                # Apply tiering for Stars & Scrubs
                dollar_value = self._apply_tiering(dollar_value, player_id, rankings)
                
                auction_values[player_id] = round(dollar_value)
            else:
                auction_values[player_id] = 1
        
        return auction_values
    
    def _apply_tiering(self, base_value: float, player_id: str, 
                       rankings: List[Dict]) -> float:
        """Apply tiering adjustments for Stars & Scrubs strategy"""
        # Find player's rank
        player_rank = None
        for player in rankings:
            if (player.get("player_id") or player.get("id")) == player_id:
                player_rank = player.get("rank", 999)
                break
        
        if player_rank is None:
            return base_value
        
        # Elite tier (top 10) - increase value for stars
        if player_rank <= 10:
            return base_value * 1.15
        # Premium tier (11-30) - slight increase
        elif player_rank <= 30:
            return base_value * 1.05
        # Mid-tier (31-60) - decrease for Stars & Scrubs
        elif player_rank <= 60:
            return base_value * 0.85
        # Value tier (61-100)
        elif player_rank <= 100:
            return base_value * 0.9
        # Scrubs (101+) - minimum values
        else:
            return max(1, base_value * 0.7)
    
    def _apply_scoring_adjustments(self, values: Dict[str, float], 
                                   rankings: List[Dict]) -> Dict[str, float]:
        """Apply Half-PPR specific adjustments"""
        adjusted = {}
        
        for player in rankings:
            player_id = player.get("player_id") or player.get("id")
            if player_id not in values:
                continue
            
            position = player.get("position", "FLEX")
            base_value = values[player_id]
            
            # Half-PPR adjustments
            if position == "RB":
                # RBs retain value in Half-PPR
                adjusted[player_id] = base_value * 1.05
            elif position == "WR":
                # WRs slightly less valuable than Full-PPR
                adjusted[player_id] = base_value * 0.98
            elif position == "TE":
                # Only elite TEs matter
                if player.get("rank", 999) <= 5:
                    adjusted[player_id] = base_value
                else:
                    adjusted[player_id] = base_value * 0.8
            elif position == "QB":
                # 4PT passing TDs reduce QB value
                adjusted[player_id] = min(base_value * 0.85, 22)
            elif position == "DEF":
                # Never pay for defense
                adjusted[player_id] = min(base_value, 2)
            else:
                adjusted[player_id] = base_value
        
        return adjusted
    
    def adjust_for_inflation(self, base_value: float, inflation_rate: float) -> float:
        """
        Adjust values based on market conditions
        
        Args:
            base_value: The calculated auction value
            inflation_rate: Market inflation (1.0 = normal, >1.0 = inflated)
        
        Returns:
            Adjusted auction value
        """
        # Simple inflation adjustment
        adjusted = base_value * inflation_rate
        
        # Cap adjustments to prevent extreme values
        if inflation_rate > 1.2:
            # In hot market, be more conservative
            adjusted = base_value * 1.15
        elif inflation_rate < 0.8:
            # In cold market, be more aggressive
            adjusted = base_value * 0.85
        
        return round(adjusted)
    
    def get_position_scarcity(self, position: str, remaining_players: List[Dict]) -> float:
        """
        Calculate scarcity multiplier for position
        
        Args:
            position: Position to check
            remaining_players: List of undrafted players
        
        Returns:
            Scarcity multiplier (1.0 = normal, >1.0 = scarce)
        """
        # Count remaining starters at position
        position_count = sum(1 for p in remaining_players 
                           if p.get("position") == position 
                           and p.get("rank", 999) <= 100)
        
        # Get baseline need
        baseline_need = self.position_baselines.get(position, 12)
        
        # Calculate scarcity
        if position_count == 0:
            return 2.0  # Extreme scarcity
        
        scarcity_ratio = baseline_need / position_count
        
        # Cap the multiplier
        return min(1.5, max(0.8, scarcity_ratio))
    
    def calculate_market_inflation(self, actual_prices: List[Dict], 
                                  projected_values: Dict[str, float]) -> float:
        """
        Calculate current market inflation based on actual vs projected
        
        Args:
            actual_prices: List of {player_id, price} for purchased players
            projected_values: Our projected values for those players
        
        Returns:
            Inflation rate (1.0 = normal, >1.0 = inflated)
        """
        if not actual_prices:
            return 1.0
        
        total_actual = 0
        total_projected = 0
        
        for purchase in actual_prices:
            player_id = purchase.get("player_id")
            actual_price = purchase.get("price", 0)
            projected = projected_values.get(player_id, actual_price)
            
            total_actual += actual_price
            total_projected += projected
        
        if total_projected == 0:
            return 1.0
        
        inflation = total_actual / total_projected
        
        # Log significant inflation
        if abs(inflation - 1.0) > 0.15:
            logger.info(f"Market inflation detected: {inflation:.2f}")
        
        return inflation
    
    def get_cached_value(self, player_id: str) -> Optional[float]:
        """Get cached auction value for a player"""
        return self.value_cache.get(player_id)
    
    def suggest_nomination_value(self, player: Dict, market_inflation: float,
                                strategy_phase: str) -> int:
        """
        Suggest opening bid for nomination
        
        Args:
            player: Player to nominate
            market_inflation: Current market inflation
            strategy_phase: Current strategy phase (STARS/VALUE/SCRUBS)
        
        Returns:
            Suggested opening bid amount
        """
        player_id = player.get("player_id") or player.get("id")
        base_value = self.get_cached_value(player_id) or 10
        
        if strategy_phase == "STARS":
            # When hunting stars, start reasonably
            if base_value > 40:
                return max(1, int(base_value * 0.6))
            else:
                # Price enforce on non-stars
                return 1
        elif strategy_phase == "VALUE":
            # Looking for deals
            if 10 < base_value < 30:
                return max(1, int(base_value * 0.5))
            else:
                return 1
        else:  # SCRUBS
            # Always start at $1 in scrub phase
            return 1