"""
Advanced Auction Value Calculator for Yahoo League 3
Based on industry-standard formulas and FantasyPros methodology
"""

import math
from typing import Dict, List, Optional
from datetime import datetime


class AuctionValueCalculator:
    """
    Calculate auction values using a more sophisticated algorithm
    Based on Value-Based Drafting (VBD) and market dynamics
    """
    
    def __init__(self, 
                 budget: int = 200,
                 num_teams: int = 12,
                 roster_spots: int = 15):
        """
        Initialize auction calculator
        
        Args:
            budget: Total auction budget per team
            num_teams: Number of teams in league
            roster_spots: Total roster spots to fill
        """
        self.budget = budget
        self.num_teams = num_teams
        self.roster_spots = roster_spots
        
        # League 3 specific roster requirements
        self.roster_requirements = {
            "QB": 1,
            "RB": 2,
            "WR": 2,
            "TE": 1,
            "FLEX": 1,
            "DEF": 1,
            "BENCH": 5,
            "IR": 1
        }
        
        # Position scarcity multipliers for Half-PPR
        self.scarcity_factors = {
            "RB": 1.15,  # RBs are scarce
            "WR": 1.0,   # Balanced in Half-PPR
            "QB": 0.75,  # Devalued with 4PT TDs
            "TE": 1.1,   # Elite TEs are valuable
            "DEF": 0.3,  # Low value
            "K": 0.0     # No kicker in League 3
        }
        
        # Calculate total dollars in pool
        self.total_dollars = budget * num_teams
        
        # Reserve $1 for each bench/low-value spot
        self.bench_spots = 7  # 5 bench + 1 DEF + 1 IR
        self.starter_budget = budget - self.bench_spots
        
    def calculate_vbd_values(self, 
                            rankings: List[Dict],
                            projections: Dict = None) -> List[Dict]:
        """
        Calculate Value-Based Drafting (VBD) auction values
        
        This uses the methodology where:
        1. Calculate replacement level at each position
        2. Calculate points above replacement (PAR)
        3. Convert PAR to dollar values
        4. Apply league-specific adjustments
        """
        
        # Step 1: Find replacement level players
        replacement_levels = self._find_replacement_levels(rankings)
        
        # Step 2: Calculate PAR for each player
        players_with_par = []
        
        for player in rankings:
            pos = player.get("position", "")
            rank = player.get("rank", 999)
            
            # Get projected points (would come from projections in real impl)
            proj_points = self._estimate_points(player, projections)
            
            # Get replacement level points
            replacement_points = replacement_levels.get(pos, 0)
            
            # Calculate Points Above Replacement
            par = max(0, proj_points - replacement_points)
            
            player["projected_points"] = proj_points
            player["par"] = par
            players_with_par.append(player)
        
        # Step 3: Convert PAR to dollars
        players_with_values = self._par_to_dollars(players_with_par)
        
        # Step 4: Apply League 3 specific adjustments
        final_values = self._apply_league3_adjustments(players_with_values)
        
        return final_values
    
    def _find_replacement_levels(self, rankings: List[Dict]) -> Dict[str, float]:
        """
        Find replacement level (baseline) for each position
        Replacement = starter quality at position * num_teams + buffer
        """
        replacement_levels = {}
        
        # Define how many starters at each position (across all teams)
        starters_needed = {
            "QB": self.num_teams * 1,  # 12 QBs
            "RB": self.num_teams * 3,  # 36 RBs (2 + 1 flex)
            "WR": self.num_teams * 3,  # 36 WRs (2 + 1 flex)
            "TE": self.num_teams * 1,  # 12 TEs
            "DEF": self.num_teams * 1   # 12 DEFs
        }
        
        # Count players by position and find replacement level
        for pos, needed in starters_needed.items():
            pos_players = [p for p in rankings if p.get("position") == pos]
            
            # Replacement player is roughly at the "needed + 3" rank
            if pos_players:
                replacement_idx = min(needed + 3, len(pos_players) - 1)
                replacement_idx = max(0, replacement_idx)  # Ensure non-negative
                
                # Estimate points for replacement player
                replacement_player = pos_players[replacement_idx]
                replacement_points = self._estimate_points(replacement_player)
                replacement_levels[pos] = replacement_points
            else:
                replacement_levels[pos] = 0
        
        return replacement_levels
    
    def _estimate_points(self, 
                        player: Dict,
                        projections: Dict = None) -> float:
        """
        Estimate fantasy points for a player
        In production, would use actual projections
        For now, use rank-based estimation
        """
        rank = player.get("rank", 999)
        pos = player.get("position", "")
        
        # If we have real projections, use them
        if projections and player.get("name") in projections:
            return projections[player["name"]].get("fantasy_points", 0)
        
        # Otherwise, estimate based on rank and position
        # Top players score ~300-350 points, declining by rank
        if pos == "QB":
            # QBs score more total points but less valuable in 4PT TD
            base = 350 * 0.85  # Reduced for 4PT TDs
        elif pos == "RB":
            base = 250
        elif pos == "WR":
            base = 240
        elif pos == "TE":
            base = 180
        else:
            base = 100
        
        # Decline curve based on rank
        if rank <= 5:
            multiplier = 1.0
        elif rank <= 10:
            multiplier = 0.92
        elif rank <= 20:
            multiplier = 0.82
        elif rank <= 30:
            multiplier = 0.72
        elif rank <= 50:
            multiplier = 0.60
        elif rank <= 75:
            multiplier = 0.45
        elif rank <= 100:
            multiplier = 0.30
        else:
            multiplier = 0.15
        
        return base * multiplier
    
    def _par_to_dollars(self, players: List[Dict]) -> List[Dict]:
        """
        Convert Points Above Replacement to dollar values
        """
        # Calculate total PAR across all draftable players
        num_draftable = min(self.num_teams * self.roster_spots, len(players))
        draftable_players = sorted(players, 
                                  key=lambda x: x.get("par", 0), 
                                  reverse=True)[:num_draftable]
        
        total_par = sum(p.get("par", 0) for p in draftable_players)
        
        # Dollars available for starters (minus $1 bench spots)
        available_dollars = self.total_dollars - (self.num_teams * self.bench_spots)
        
        # Calculate dollar per PAR point
        if total_par > 0:
            dollar_per_par = available_dollars / total_par
        else:
            # Fallback: distribute based on rank
            dollar_per_par = 1.0
        
        # Assign dollar values
        for player in players:
            par = player.get("par", 0)
            rank = player.get("rank", 999)
            
            if par > 0:
                # Base value from PAR
                base_value = par * dollar_per_par
                
                # Apply position scarcity
                pos = player.get("position", "")
                scarcity = self.scarcity_factors.get(pos, 1.0)
                
                # Calculate final value
                value = base_value * scarcity
                
                # Round to nearest dollar
                player["auction_value"] = max(1, round(value))
            elif rank <= 100:
                # For players without PAR but in top 100, use rank-based fallback
                if rank <= 10:
                    player["auction_value"] = 50
                elif rank <= 20:
                    player["auction_value"] = 30
                elif rank <= 40:
                    player["auction_value"] = 15
                elif rank <= 60:
                    player["auction_value"] = 8
                elif rank <= 80:
                    player["auction_value"] = 4
                else:
                    player["auction_value"] = 2
            else:
                # Replacement level or below = $1
                player["auction_value"] = 1
        
        return players
    
    def _apply_league3_adjustments(self, players: List[Dict]) -> List[Dict]:
        """
        Apply League 3 specific adjustments
        - 4PT passing TDs (QB devalue)
        - Half-PPR (balanced RB/WR)
        - No kicker
        - Stars & Scrubs viable
        """
        for player in players:
            pos = player.get("position", "")
            value = player.get("auction_value", 1)
            
            # QB adjustment for 4PT passing TDs
            if pos == "QB":
                # Max QB value should be ~$20-25
                if value > 25:
                    player["auction_value"] = min(25, int(value * 0.75))
                player["l3_note"] = "4PT Pass TD cap"
            
            # No kicker in this league
            elif pos == "K":
                player["auction_value"] = 0
                player["l3_note"] = "No kicker position"
            
            # Elite player premium for Stars & Scrubs
            elif player.get("rank", 999) <= 5:
                # Top 5 at position get premium
                player["auction_value"] = int(value * 1.1)
                player["l3_note"] = "Elite player premium"
            
            # Pass-catching RB bonus in Half-PPR
            elif pos == "RB":
                # Known pass-catchers get small boost
                pass_catchers = ["McCaffrey", "Ekeler", "Kamara", "White", "Hall"]
                if any(name in player.get("name", "") for name in pass_catchers):
                    player["auction_value"] = int(value * 1.05)
                    player["l3_note"] = "Pass-catching bonus"
        
        # Normalize to $200 budget
        self._normalize_values(players)
        
        return players
    
    def _normalize_values(self, players: List[Dict]):
        """
        Ensure total values don't exceed league budget
        """
        # Get top 180 players (15 * 12 teams)
        num_drafted = self.num_teams * self.roster_spots
        top_players = sorted(players, 
                           key=lambda x: x.get("auction_value", 0), 
                           reverse=True)[:num_drafted]
        
        # Calculate total value
        total_value = sum(p.get("auction_value", 0) for p in top_players)
        
        # If over budget, scale down
        if total_value > self.total_dollars:
            scale_factor = self.total_dollars / total_value
            
            for player in players:
                old_value = player.get("auction_value", 1)
                new_value = max(1, int(old_value * scale_factor))
                player["auction_value"] = new_value
    
    def get_nomination_strategy(self, 
                               budget_remaining: int,
                               roster_needs: List[str]) -> Dict:
        """
        Get nomination strategy based on budget and needs
        """
        avg_per_slot = budget_remaining / len(roster_needs) if roster_needs else 0
        
        if budget_remaining > 120:
            # Early auction - nominate expensive players you don't want
            return {
                "strategy": "PRICE_ENFORCE",
                "target": "Expensive QBs/TEs you don't want",
                "reason": "Force opponents to spend early"
            }
        elif budget_remaining > 50:
            # Mid auction - target values
            return {
                "strategy": "VALUE_HUNT",
                "target": f"$8-15 players at {roster_needs[0] if roster_needs else 'FLEX'}",
                "reason": "Find undervalued targets"
            }
        else:
            # Late auction - get sleepers
            return {
                "strategy": "SLEEPER_GRAB",
                "target": "$1-2 upside players",
                "reason": "Fill roster with lottery tickets"
            }


# Test function
def test_auction_values():
    """Test the advanced auction value calculator"""
    print("\n" + "="*60)
    print("ADVANCED AUCTION VALUE CALCULATOR TEST")
    print("="*60)
    
    calculator = AuctionValueCalculator(budget=200, num_teams=12)
    
    # Mock rankings for testing
    test_rankings = [
        {"name": "Christian McCaffrey", "position": "RB", "rank": 1},
        {"name": "Tyreek Hill", "position": "WR", "rank": 2},
        {"name": "Justin Jefferson", "position": "WR", "rank": 3},
        {"name": "Austin Ekeler", "position": "RB", "rank": 4},
        {"name": "Ja'Marr Chase", "position": "WR", "rank": 5},
        {"name": "Josh Allen", "position": "QB", "rank": 6},
        {"name": "Saquon Barkley", "position": "RB", "rank": 7},
        {"name": "Patrick Mahomes", "position": "QB", "rank": 8},
        {"name": "Travis Kelce", "position": "TE", "rank": 9},
        {"name": "Stefon Diggs", "position": "WR", "rank": 10}
    ]
    
    # Calculate values
    valued_players = calculator.calculate_vbd_values(test_rankings)
    
    print("\nCalculated Auction Values (League 3 - Half PPR, 4PT Pass TD):")
    print("-" * 60)
    
    for player in valued_players[:10]:
        name = player["name"]
        pos = player["position"]
        value = player.get("auction_value", 0)
        note = player.get("l3_note", "")
        
        print(f"{name:25} ({pos:2}) - ${value:3}  {note}")
    
    # Test nomination strategy
    print("\n" + "="*60)
    print("NOMINATION STRATEGIES")
    print("-" * 60)
    
    scenarios = [
        (150, ["RB", "WR", "RB", "WR", "TE"]),
        (80, ["WR", "RB", "TE"]),
        (30, ["BENCH", "BENCH"])
    ]
    
    for budget, needs in scenarios:
        strategy = calculator.get_nomination_strategy(budget, needs)
        print(f"\nBudget: ${budget}, Needs: {needs}")
        print(f"Strategy: {strategy['strategy']}")
        print(f"Target: {strategy['target']}")
        print(f"Reason: {strategy['reason']}")


if __name__ == "__main__":
    test_auction_values()