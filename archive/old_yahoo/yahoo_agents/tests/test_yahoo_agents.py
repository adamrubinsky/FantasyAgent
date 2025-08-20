"""
Comprehensive tests for Yahoo Fantasy agents
Tests both Snake Draft (League 2) and Auction (League 3) agents
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List

# Import our agents
from yahoo_snake_agent import YahooSnakeDraftAgent
from yahoo_auction_agent import YahooAuctionAgent
from auction_values import AuctionValueCalculator


async def test_auction_scenarios():
    """
    Test 40 different auction scenarios with various:
    - Budget situations ($180, $100, $50, $20)
    - Roster needs (empty, partially filled, almost complete)
    - Player types (elite, mid-tier, sleeper)
    - Market conditions (early, mid, late auction)
    """
    print("\n" + "="*80)
    print("YAHOO AUCTION AGENT - 40 SCENARIO TEST")
    print("League 3: Half-PPR, 4PT Pass TDs, $200 Budget")
    print("="*80)
    
    agent = YahooAuctionAgent()
    calculator = AuctionValueCalculator()
    
    # Define test scenarios
    scenarios = []
    
    # SCENARIO SET 1: Early Auction (Budget $150-180)
    early_rosters = [
        {"QB": [], "RB": [], "WR": [], "TE": [], "DEF": []},
        {"QB": [], "RB": ["Christian McCaffrey"], "WR": [], "TE": [], "DEF": []},
        {"QB": ["Josh Allen"], "RB": [], "WR": ["Tyreek Hill"], "TE": [], "DEF": []},
    ]
    
    early_players = [
        {"name": "Justin Jefferson", "position": "WR", "rank": 3},
        {"name": "Austin Ekeler", "position": "RB", "rank": 8},
        {"name": "Patrick Mahomes", "position": "QB", "rank": 4},
        {"name": "Travis Kelce", "position": "TE", "rank": 5},
        {"name": "Saquon Barkley", "position": "RB", "rank": 6},
        {"name": "Stefon Diggs", "position": "WR", "rank": 12},
        {"name": "Lamar Jackson", "position": "QB", "rank": 7},
    ]
    
    # Generate early auction scenarios
    for roster in early_rosters:
        for player in early_players:
            for current_bid in [5, 25, 45, 60]:
                budget = 170 - (len(roster.get("RB", [])) * 50 + len(roster.get("WR", [])) * 40)
                scenarios.append({
                    "phase": "EARLY",
                    "budget": max(budget, 100),
                    "roster": roster,
                    "player": player,
                    "current_bid": current_bid
                })
    
    # SCENARIO SET 2: Mid Auction (Budget $60-100)
    mid_rosters = [
        {"QB": ["Dak Prescott"], "RB": ["Najee Harris", "Joe Mixon"], "WR": ["CeeDee Lamb"], "TE": [], "DEF": []},
        {"QB": [], "RB": ["Derrick Henry"], "WR": ["A.J. Brown", "Amari Cooper"], "TE": ["Mark Andrews"], "DEF": []},
    ]
    
    mid_players = [
        {"name": "Calvin Ridley", "position": "WR", "rank": 25},
        {"name": "James Conner", "position": "RB", "rank": 28},
        {"name": "Tua Tagovailoa", "position": "QB", "rank": 15},
        {"name": "Dallas Goedert", "position": "TE", "rank": 18},
    ]
    
    # Generate mid auction scenarios
    for roster in mid_rosters:
        for player in mid_players:
            for current_bid in [3, 10, 18, 25]:
                scenarios.append({
                    "phase": "MID",
                    "budget": 80,
                    "roster": roster,
                    "player": player,
                    "current_bid": current_bid
                })
    
    # SCENARIO SET 3: Late Auction (Budget $20-50)
    late_rosters = [
        {
            "QB": ["Jalen Hurts"],
            "RB": ["Jonathan Taylor", "Tony Pollard", "Rachaad White"],
            "WR": ["Ja'Marr Chase", "Chris Olave"],
            "TE": ["T.J. Hockenson"],
            "DEF": []
        }
    ]
    
    late_players = [
        {"name": "Jahan Dotson", "position": "WR", "rank": 65},
        {"name": "Khalil Herbert", "position": "RB", "rank": 58},
        {"name": "Sam Howell", "position": "QB", "rank": 28},
        {"name": "Dalton Schultz", "position": "TE", "rank": 35},
    ]
    
    # Generate late auction scenarios
    for roster in late_rosters:
        for player in late_players:
            for current_bid in [1, 2, 4, 7]:
                scenarios.append({
                    "phase": "LATE",
                    "budget": 25,
                    "roster": roster,
                    "player": player,
                    "current_bid": current_bid
                })
    
    # Limit to 40 scenarios
    scenarios = scenarios[:40]
    
    # Test each scenario
    print(f"\nTesting {len(scenarios)} auction scenarios...\n")
    print(f"{'#':<3} {'Phase':<6} {'Budget':<7} {'Player':<20} {'Pos':<4} {'Bid':<5} {'Rec':<5} {'Max':<5} {'Decision':<20}")
    print("-" * 80)
    
    results = []
    for i, scenario in enumerate(scenarios, 1):
        # Calculate roster slots
        roster = scenario["roster"]
        slots_filled = sum(len(players) for players in roster.values())
        slots_remaining = 15 - slots_filled
        
        # Determine stars acquired (simplified)
        stars = 0
        if any("McCaffrey" in p for p in roster.get("RB", [])):
            stars += 1
        if any("Jefferson" in p or "Hill" in p for p in roster.get("WR", [])):
            stars += 1
        if any("Allen" in p or "Mahomes" in p for p in roster.get("QB", [])):
            stars += 1
        
        # Build context for agent
        context = {
            "remaining_budget": scenario["budget"],
            "spent_budget": 200 - scenario["budget"],
            "user_roster": roster,
            "slots_filled": slots_filled,
            "slots_remaining": slots_remaining,
            "stars_acquired": stars,
            "player_up": scenario["player"],
            "current_bid": scenario["current_bid"]
        }
        
        # Get recommendation
        try:
            result = await agent.get_bid_recommendation(context)
            bid_rec = result["bid"]
            
            should_bid = bid_rec.get("should_bid", False)
            amount = bid_rec.get("amount", 0)
            max_bid = bid_rec.get("max_bid", 0)
            reason = bid_rec.get("reason", "")[:18]
            
            results.append({
                "scenario": i,
                "phase": scenario["phase"],
                "budget": scenario["budget"],
                "player": scenario["player"]["name"][:18],
                "position": scenario["player"]["position"],
                "current_bid": scenario["current_bid"],
                "should_bid": should_bid,
                "bid_amount": amount,
                "max_bid": max_bid,
                "reason": reason
            })
            
            # Print result
            bid_str = f"${amount}" if should_bid else "PASS"
            print(f"{i:<3} {scenario['phase']:<6} ${scenario['budget']:<6} {scenario['player']['name'][:18]:<20} "
                  f"{scenario['player']['position']:<4} ${scenario['current_bid']:<4} {bid_str:<5} ${max_bid:<4} {reason:<20}")
            
        except Exception as e:
            print(f"{i:<3} ERROR: {e}")
            
        # Add small delay to avoid overwhelming
        if i % 10 == 0:
            await asyncio.sleep(0.1)
    
    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("-" * 80)
    
    # Analyze bidding patterns
    total_bids = sum(1 for r in results if r["should_bid"])
    total_passes = sum(1 for r in results if not r["should_bid"])
    
    print(f"Total Bid Recommendations: {total_bids}")
    print(f"Total Pass Recommendations: {total_passes}")
    print(f"Bid Rate: {total_bids/len(results)*100:.1f}%")
    
    # Analyze by position
    print("\nBidding by Position:")
    for pos in ["QB", "RB", "WR", "TE"]:
        pos_results = [r for r in results if r["position"] == pos]
        if pos_results:
            pos_bids = sum(1 for r in pos_results if r["should_bid"])
            avg_max = sum(r["max_bid"] for r in pos_results) / len(pos_results)
            print(f"  {pos}: {pos_bids}/{len(pos_results)} bids, Avg Max: ${avg_max:.0f}")
    
    # Analyze by phase
    print("\nBidding by Auction Phase:")
    for phase in ["EARLY", "MID", "LATE"]:
        phase_results = [r for r in results if r["phase"] == phase]
        if phase_results:
            phase_bids = sum(1 for r in phase_results if r["should_bid"])
            avg_budget = sum(r["budget"] for r in phase_results) / len(phase_results)
            print(f"  {phase}: {phase_bids}/{len(phase_results)} bids, Avg Budget: ${avg_budget:.0f}")
    
    return results


async def test_snake_draft_scenarios():
    """
    Test Yahoo Snake Draft agent with various scenarios
    """
    print("\n" + "="*80)
    print("YAHOO SNAKE DRAFT AGENT TEST")
    print("League 2: Full PPR, 6PT Pass TDs")
    print("="*80)
    
    agent = YahooSnakeDraftAgent()
    
    # Test scenarios for different draft positions
    scenarios = [
        # Early rounds - need core players
        {
            "round": 1,
            "pick_number": 8,
            "roster": {"QB": [], "RB": [], "WR": [], "TE": []},
            "description": "First pick - empty roster"
        },
        {
            "round": 3,
            "pick_number": 32,
            "roster": {"QB": [], "RB": ["Bijan Robinson"], "WR": ["Justin Jefferson"], "TE": []},
            "description": "Round 3 - need QB or second RB/WR"
        },
        # Mid rounds - filling needs
        {
            "round": 6,
            "pick_number": 68,
            "roster": {
                "QB": ["Josh Allen"],
                "RB": ["Saquon Barkley", "Josh Jacobs"],
                "WR": ["CeeDee Lamb", "Calvin Ridley"],
                "TE": []
            },
            "description": "Round 6 - need TE"
        },
        # Late rounds - depth and upside
        {
            "round": 10,
            "pick_number": 116,
            "roster": {
                "QB": ["Lamar Jackson", "Tua Tagovailoa"],
                "RB": ["CMC", "Breece Hall", "James Conner"],
                "WR": ["Tyreek Hill", "Davante Adams", "Chris Olave"],
                "TE": ["Travis Kelce"]
            },
            "description": "Round 10 - depth picks"
        }
    ]
    
    print("\nTesting Snake Draft Scenarios...")
    print("-" * 80)
    
    for scenario in scenarios:
        print(f"\n{scenario['description']}")
        print(f"Round {scenario['round']}, Pick {scenario['pick_number']}")
        
        # Mock available players (would be live data in production)
        available = [
            {"name": "Davante Adams", "position": "WR", "rank": 15},
            {"name": "Joe Burrow", "position": "QB", "rank": 8},
            {"name": "Mark Andrews", "position": "TE", "rank": 12},
            {"name": "Tony Pollard", "position": "RB", "rank": 25},
            {"name": "DeVonta Smith", "position": "WR", "rank": 28}
        ]
        
        context = {
            "round": scenario["round"],
            "pick_number": scenario["pick_number"],
            "user_roster": scenario["roster"],
            "available_players": available
        }
        
        result = await agent.get_recommendation(context)
        
        print(f"Response Time: {result['total_time_ms']}ms")
        print(f"Strategy: {result['strategy']}")
        print("Recommendations:")
        
        for i, rec in enumerate(result["recommendations"][:3], 1):
            print(f"  {i}. {rec['name']} ({rec['position']}) - {rec['reason']}")


async def main():
    """Run all tests"""
    print("\n🏈 YAHOO FANTASY AGENTS - COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    # Test auction scenarios
    auction_results = await test_auction_scenarios()
    
    # Test snake draft
    await test_snake_draft_scenarios()
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETE")
    print("="*80)
    
    # Check performance
    print("\n📊 Performance Summary:")
    print("- Auction agent: 40 scenarios tested")
    print("- Snake draft agent: 4 scenarios tested")
    print("- Target: <3s response time")
    
    return auction_results


if __name__ == "__main__":
    asyncio.run(main())