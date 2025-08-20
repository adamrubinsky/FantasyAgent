#!/usr/bin/env python3
"""
Advanced Draft Strategy Optimizer for SUPERFLEX Leagues
Implements sophisticated value detection, tier-based analysis, and decision tree logic
"""

from typing import Dict, List, Tuple, Optional, Any
import math

class DraftStrategyOptimizer:
    """
    Optimizes draft recommendations using advanced strategies:
    - SUPERFLEX-specific decision tree
    - ADP value detection
    - Tier-based drafting
    - QB-WR stacking
    - Keeper value identification
    """
    
    def __init__(self):
        # SUPERFLEX QB tiers based on consensus rankings
        self.qb_tiers = {
            "elite": [],  # Will be populated with top 4 QBs from rankings
            "tier1": [],  # QBs 5-8
            "tier2": [],  # QBs 9-15
            "tier3": [],  # QBs 16-24
            "streamers": []  # QB25+
        }
        
        # Position requirements for SUPERFLEX
        self.position_targets = {
            "QB": {"min": 2, "ideal": 3, "max": 4},
            "RB": {"min": 2, "ideal": 5, "max": 7},
            "WR": {"min": 3, "ideal": 6, "max": 8},
            "TE": {"min": 1, "ideal": 2, "max": 3},
            "K": {"min": 1, "ideal": 1, "max": 1},
            "DST": {"min": 1, "ideal": 1, "max": 2}
        }
        
    def get_round_strategy(self, round_num: int, roster_state: Dict) -> Dict[str, Any]:
        """
        Get specific strategy for current round based on SUPERFLEX decision tree
        
        Args:
            round_num: Current round number (1-16)
            roster_state: Current roster composition
            
        Returns:
            Strategy dict with priorities and rules
        """
        qb_count = roster_state.get("QB", 0)
        rb_count = roster_state.get("RB", 0)
        wr_count = roster_state.get("WR", 0)
        te_count = roster_state.get("TE", 0)
        
        strategy = {
            "round": round_num,
            "priorities": [],
            "avoid": [],
            "notes": []
        }
        
        # Round 1 Strategy
        if round_num == 1:
            strategy["priorities"] = ["Elite QB (Top 4)", "Elite RB/WR if no QB"]
            strategy["notes"].append("Take Allen/Hurts/Lamar/Mahomes if available")
            
        # Round 2 Strategy
        elif round_num == 2:
            if qb_count == 0:
                strategy["priorities"] = ["Tier 1-2 QB"]
                strategy["notes"].append("Must get QB - Herbert/Stroud/Burrow tier")
            elif qb_count == 1:
                strategy["priorities"] = ["Elite QB if available", "Top-tier RB/WR"]
                strategy["notes"].append("Secure QB2 if elite option exists")
                
        # Round 3 Strategy
        elif round_num == 3:
            if qb_count < 2:
                strategy["priorities"] = ["Tier 2-3 QB"]
                strategy["notes"].append("Last chance for quality QB2")
            else:
                strategy["priorities"] = ["Best RB/WR by tier"]
                
        # Round 4 Strategy
        elif round_num == 4:
            if qb_count < 2:
                strategy["priorities"] = ["ANY starting QB"]
                strategy["notes"].append("MUST secure QB2 - reach if necessary")
            else:
                strategy["priorities"] = ["Bell-cow RB", "Target-hog WR"]
                
        # Rounds 5-6 Strategy
        elif round_num in [5, 6]:
            strategy["priorities"] = ["High-upside RB/WR"]
            if qb_count == 2:
                strategy["priorities"].append("QB3 if injury-prone starters")
                
        # Rounds 7-9 Strategy
        elif 7 <= round_num <= 9:
            strategy["priorities"] = ["RB/WR depth"]
            if te_count == 0:
                strategy["priorities"].append("Top-8 TE if available")
            strategy["avoid"] = ["QB4 unless extreme value"]
            
        # Rounds 10-14 Strategy
        elif 10 <= round_num <= 14:
            strategy["priorities"] = [
                "RB handcuffs (own starters)",
                "Breakout WRs",
                "Rookie QBs with path to starting"
            ]
            strategy["avoid"] = ["DST", "K"]
            strategy["notes"].append("Upside only - swing for ceiling")
            
        # Round 15 Strategy
        elif round_num == 15:
            strategy["priorities"] = ["DST with easy early schedule"]
            strategy["notes"].append("Target weak opposing QBs Weeks 1-3")
            
        # Round 16 Strategy
        elif round_num == 16:
            strategy["priorities"] = ["K in high-scoring offense"]
            strategy["notes"].append("Prefer dome/home games early")
            
        return strategy
    
    def calculate_adp_value(self, player: Dict, current_pick: int) -> float:
        """
        Calculate how much value a player represents at current pick
        
        Args:
            player: Player data with ADP
            current_pick: Current pick number
            
        Returns:
            Value score (positive = falling, negative = reach)
        """
        player_adp = player.get("adp", current_pick)
        
        # Calculate picks fallen/risen
        value_differential = player_adp - current_pick
        
        # Apply logarithmic scaling for significance
        if value_differential > 0:
            # Player has fallen - good value
            value_score = math.log(1 + value_differential) * 10
        else:
            # Player is being reached for
            value_score = value_differential / 2
            
        return value_score
    
    def detect_tier_break(self, position: str, available_players: List[Dict], 
                          rankings: List[Dict]) -> Optional[str]:
        """
        Detect if we're at a tier break for a position
        
        Args:
            position: Position to check
            available_players: Currently available players
            rankings: Full rankings with tiers
            
        Returns:
            Player name if last in tier, None otherwise
        """
        # Group available players by position
        position_available = [p for p in available_players 
                             if position in p.get("positions", [])]
        
        if not position_available:
            return None
            
        # Check if top available is last in their tier
        top_player = position_available[0]
        player_tier = self._get_player_tier(top_player, rankings)
        
        # Count how many from same tier remain
        same_tier_count = sum(1 for p in position_available 
                             if self._get_player_tier(p, rankings) == player_tier)
        
        if same_tier_count == 1:
            return top_player.get("name")
            
        return None
    
    def identify_stacking_opportunities(self, roster: List[Dict], 
                                       available_players: List[Dict]) -> List[Dict]:
        """
        Find QB-WR/TE stacking opportunities
        
        Args:
            roster: Current roster
            available_players: Available players
            
        Returns:
            List of stacking candidates with bonus scores
        """
        stacking_candidates = []
        
        # Get QBs on roster
        roster_qbs = [p for p in roster if "QB" in p.get("positions", [])]
        
        for qb in roster_qbs:
            qb_team = qb.get("team")
            if not qb_team:
                continue
                
            # Find WRs/TEs from same team
            teammates = [p for p in available_players 
                        if p.get("team") == qb_team 
                        and any(pos in ["WR", "TE"] for pos in p.get("positions", []))]
            
            for teammate in teammates:
                stacking_candidates.append({
                    "player": teammate,
                    "qb": qb.get("name"),
                    "stack_bonus": 5.0  # Bonus points for stacking
                })
                
        return stacking_candidates
    
    def evaluate_keeper_value(self, player: Dict, current_round: int) -> float:
        """
        Evaluate a player's keeper value for next year
        
        Args:
            player: Player data
            current_round: Round being drafted
            
        Returns:
            Keeper value score
        """
        keeper_score = 0.0
        
        # Factors that increase keeper value
        if player.get("years_experience", 99) <= 2:  # Young player
            keeper_score += 10
            
        if current_round >= 8:  # Late round value
            keeper_score += (current_round - 7) * 3
            
        if "rookie" in player.get("notes", "").lower():
            keeper_score += 8
            
        # High upside positions
        if "RB" in player.get("positions", []) and player.get("age", 30) <= 24:
            keeper_score += 5
            
        if "WR" in player.get("positions", []) and player.get("age", 30) <= 23:
            keeper_score += 5
            
        return keeper_score
    
    def detect_positional_run(self, recent_picks: List[Dict], 
                              window: int = 6) -> Optional[str]:
        """
        Detect if a positional run is happening
        
        Args:
            recent_picks: Last N picks made
            window: How many picks to analyze
            
        Returns:
            Position being run on, or None
        """
        if len(recent_picks) < window:
            return None
            
        # Count positions in recent picks
        position_counts = {}
        for pick in recent_picks[-window:]:
            pos = pick.get("position", "")
            if pos:
                position_counts[pos] = position_counts.get(pos, 0) + 1
                
        # Check if any position has 3+ picks
        for pos, count in position_counts.items():
            if count >= 3:
                return pos
                
        return None
    
    def optimize_recommendation(self, current_pick: int, round_num: int,
                               roster: List[Dict], available_players: List[Dict],
                               rankings: List[Dict], recent_picks: List[Dict]) -> Dict:
        """
        Generate optimized recommendation using all strategies
        
        Args:
            current_pick: Current pick number
            round_num: Current round
            roster: User's current roster
            available_players: Available players
            rankings: Full rankings data
            recent_picks: Recent draft picks
            
        Returns:
            Optimized recommendation with reasoning
        """
        # Get roster state
        roster_state = self._get_roster_state(roster)
        
        # Get round-specific strategy
        round_strategy = self.get_round_strategy(round_num, roster_state)
        
        # Score each available player
        player_scores = []
        
        for player in available_players[:30]:  # Top 30 for performance
            score = 100.0  # Base score
            reasons = []
            
            # Apply ADP value
            adp_value = self.calculate_adp_value(player, current_pick)
            score += adp_value
            if adp_value > 10:
                reasons.append(f"Falling {int(adp_value)} spots below ADP")
                
            # Check tier breaks
            player_pos = player.get("positions", [""])[0]
            if self.detect_tier_break(player_pos, available_players, rankings):
                score += 15
                reasons.append("Last in tier")
                
            # Check stacking
            stack_opps = self.identify_stacking_opportunities(roster, [player])
            if stack_opps:
                score += stack_opps[0]["stack_bonus"]
                reasons.append(f"Stacks with {stack_opps[0]['qb']}")
                
            # Keeper value (rounds 8+)
            if round_num >= 8:
                keeper_val = self.evaluate_keeper_value(player, round_num)
                if keeper_val > 10:
                    score += keeper_val
                    reasons.append(f"High keeper value")
                    
            # Positional run fade
            run_position = self.detect_positional_run(recent_picks)
            if run_position and run_position != player_pos:
                score += 5
                reasons.append(f"Fading {run_position} run")
                
            player_scores.append({
                "player": player,
                "score": score,
                "reasons": reasons
            })
            
        # Sort by score
        player_scores.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top 3 recommendations
        return {
            "primary": player_scores[0] if player_scores else None,
            "alternatives": player_scores[1:3] if len(player_scores) > 1 else [],
            "strategy": round_strategy
        }
    
    def _get_roster_state(self, roster: List[Dict]) -> Dict[str, int]:
        """Get position counts from roster"""
        state = {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "K": 0, "DST": 0}
        for player in roster:
            for pos in player.get("positions", []):
                if pos in state:
                    state[pos] += 1
        return state
    
    def _get_player_tier(self, player: Dict, rankings: List[Dict]) -> int:
        """Determine player's tier from rankings"""
        # This would be implemented based on your tier system
        player_rank = player.get("rank", 999)
        if player_rank <= 10:
            return 1
        elif player_rank <= 30:
            return 2
        elif player_rank <= 60:
            return 3
        elif player_rank <= 100:
            return 4
        else:
            return 5