"""
Simple Auction Max Bid Calculator Test
Shows maximum bid values for players based on budget and roster state
"""

import asyncio
from auction_values import AuctionValueCalculator


async def get_max_bid_values():
    """
    Calculate max bid values for top players at different budget levels
    Focus on League 3: Half-PPR, 4PT Pass TDs
    """
    print("\n" + "="*80)
    print("YAHOO AUCTION MAX BID VALUES")
    print("League 3: Half-PPR, 4PT Pass TDs, $200 Budget")
    print("="*80)
    
    calculator = AuctionValueCalculator(budget=200, num_teams=12)
    
    # Top players to evaluate
    test_players = [
        # Elite Tier
        {"name": "Christian McCaffrey", "position": "RB", "rank": 1},
        {"name": "Tyreek Hill", "position": "WR", "rank": 2},
        {"name": "Justin Jefferson", "position": "WR", "rank": 3},
        {"name": "Austin Ekeler", "position": "RB", "rank": 4},
        {"name": "Travis Kelce", "position": "TE", "rank": 5},
        
        # QB Tier (devalued in 4PT TD)
        {"name": "Josh Allen", "position": "QB", "rank": 6},
        {"name": "Patrick Mahomes", "position": "QB", "rank": 7},
        {"name": "Jalen Hurts", "position": "QB", "rank": 8},
        
        # Second Tier RB/WR
        {"name": "Saquon Barkley", "position": "RB", "rank": 9},
        {"name": "Nick Chubb", "position": "RB", "rank": 10},
        {"name": "Stefon Diggs", "position": "WR", "rank": 11},
        {"name": "Davante Adams", "position": "WR", "rank": 12},
        {"name": "A.J. Brown", "position": "WR", "rank": 13},
        
        # Mid Tier
        {"name": "Joe Mixon", "position": "RB", "rank": 20},
        {"name": "Calvin Ridley", "position": "WR", "rank": 22},
        {"name": "Mark Andrews", "position": "TE", "rank": 15},
        {"name": "Lamar Jackson", "position": "QB", "rank": 18},
        
        # Value Tier
        {"name": "James Conner", "position": "RB", "rank": 28},
        {"name": "Chris Olave", "position": "WR", "rank": 25},
        {"name": "Dallas Goedert", "position": "TE", "rank": 30},
        {"name": "Dak Prescott", "position": "QB", "rank": 32},
        
        # Late Round
        {"name": "Rachaad White", "position": "RB", "rank": 35},
        {"name": "Christian Watson", "position": "WR", "rank": 40},
        {"name": "David Njoku", "position": "TE", "rank": 45},
        {"name": "Tua Tagovailoa", "position": "QB", "rank": 38},
        
        # Deep Sleepers
        {"name": "Khalil Herbert", "position": "RB", "rank": 58},
        {"name": "Jahan Dotson", "position": "WR", "rank": 65},
        {"name": "Sam LaPorta", "position": "TE", "rank": 72},
        {"name": "Kenny Pickett", "position": "QB", "rank": 85}
    ]
    
    # Calculate VBD values
    valued_players = calculator.calculate_vbd_values(test_players)
    
    # Different budget scenarios
    budget_scenarios = [
        {"budget": 200, "spent": 0, "phase": "START", "desc": "Full Budget"},
        {"budget": 150, "spent": 50, "phase": "EARLY", "desc": "After 1 Star"},
        {"budget": 100, "spent": 100, "phase": "MID", "desc": "After 2 Stars"},
        {"budget": 50, "spent": 150, "phase": "LATE", "desc": "Value Hunting"},
        {"budget": 20, "spent": 180, "phase": "END", "desc": "Scrubs Phase"}
    ]
    
    # Print header
    print("\n📊 MAX BID VALUES BY BUDGET LEVEL")
    print("-" * 80)
    
    # Create formatted table
    print(f"\n{'Player':<25} {'Pos':<4} {'Rank':<5} | {'$200':<6} {'$150':<6} {'$100':<6} {'$50':<6} {'$20':<6}")
    print("-" * 80)
    
    for player in valued_players:
        name = player["name"][:23]
        pos = player["position"]
        rank = player["rank"]
        base_value = player.get("auction_value", 1)
        
        # Calculate max bid for each budget level
        max_bids = []
        for scenario in budget_scenarios:
            budget_remaining = scenario["budget"]
            slots_remaining = 15 - (scenario["spent"] // 15)  # Approximate
            
            if slots_remaining <= 0:
                slots_remaining = 1
                
            # Max bid calculation
            # Never spend more than 40% of remaining budget on one player
            max_budget_pct = 0.4 if scenario["phase"] in ["START", "EARLY"] else 0.3
            
            # Adjust base value by budget phase
            if scenario["phase"] == "START":
                adjusted_value = base_value
            elif scenario["phase"] == "EARLY":
                adjusted_value = base_value * 0.95
            elif scenario["phase"] == "MID":
                adjusted_value = base_value * 0.85
            elif scenario["phase"] == "LATE":
                adjusted_value = min(base_value * 0.7, budget_remaining * 0.25)
            else:  # END
                adjusted_value = min(3, base_value * 0.5)
            
            # Apply position-specific limits
            if pos == "QB" and scenario["phase"] != "END":
                # QB max value in 4PT TD league
                adjusted_value = min(adjusted_value, 22)
            
            # Calculate final max bid
            max_bid = min(
                adjusted_value,
                budget_remaining * max_budget_pct,
                budget_remaining - slots_remaining + 1  # Save $1 per remaining slot
            )
            
            max_bids.append(int(max(1, max_bid)))
        
        # Format output
        bid_strs = [f"${b}" for b in max_bids]
        
        # Color code by value tier
        if rank <= 5:
            tier = "⭐"  # Elite
        elif rank <= 15:
            tier = "🔥"  # Premium
        elif rank <= 30:
            tier = "✅"  # Good
        elif rank <= 50:
            tier = "💰"  # Value
        else:
            tier = "🎯"  # Sleeper
            
        print(f"{tier} {name:<23} {pos:<4} {rank:<5} | {bid_strs[0]:<6} {bid_strs[1]:<6} {bid_strs[2]:<6} {bid_strs[3]:<6} {bid_strs[4]:<6}")
    
    # Print key insights
    print("\n" + "="*80)
    print("💡 KEY INSIGHTS FOR LEAGUE 3 (Half-PPR, 4PT Pass TDs):")
    print("-" * 80)
    print("1. QBs capped at ~$22 due to 4PT passing TDs (vs 6PT)")
    print("2. Pass-catching RBs get 5-10% premium in Half-PPR")
    print("3. Elite WRs (Jefferson, Hill) worth up to $60 with full budget")
    print("4. Never spend >40% of remaining budget on one player")
    print("5. Save $1 per remaining roster spot minimum")
    print("\n📌 STARS & SCRUBS STRATEGY:")
    print("   - Spend $140-160 on 3-4 elite players")
    print("   - Fill remaining spots with $1-3 players")
    print("   - Target: 2 RBs + 1-2 WRs as your stars")


async def test_specific_scenarios():
    """
    Test specific auction scenarios you might face
    """
    print("\n" + "="*80)
    print("SPECIFIC SCENARIO TESTS")
    print("="*80)
    
    calculator = AuctionValueCalculator()
    
    scenarios = [
        {
            "desc": "Opening Bid - CMC",
            "player": {"name": "Christian McCaffrey", "position": "RB", "rank": 1},
            "budget": 200,
            "roster_state": "Empty"
        },
        {
            "desc": "Already have 1 star RB, Tyreek Hill nominated",
            "player": {"name": "Tyreek Hill", "position": "WR", "rank": 2},
            "budget": 140,
            "roster_state": "Have Ekeler ($60)"
        },
        {
            "desc": "Need QB, Mahomes available",
            "player": {"name": "Patrick Mahomes", "position": "QB", "rank": 7},
            "budget": 80,
            "roster_state": "Have 2 RBs, 2 WRs"
        },
        {
            "desc": "Late value RB",
            "player": {"name": "Rachaad White", "position": "RB", "rank": 35},
            "budget": 45,
            "roster_state": "Need RB3"
        },
        {
            "desc": "Sleeper WR end of draft",
            "player": {"name": "Jahan Dotson", "position": "WR", "rank": 65},
            "budget": 12,
            "roster_state": "Need bench depth"
        }
    ]
    
    print("\nScenario Analysis:")
    print("-" * 80)
    
    for scenario in scenarios:
        # Calculate value
        values = calculator.calculate_vbd_values([scenario["player"]])
        if values:
            player_value = values[0]
            base_value = player_value.get("auction_value", 1)
            
            # Adjust for budget
            budget_pct = scenario["budget"] / 200
            if budget_pct > 0.7:
                max_bid = base_value
            elif budget_pct > 0.4:
                max_bid = base_value * 0.9
            elif budget_pct > 0.2:
                max_bid = base_value * 0.75
            else:
                max_bid = min(base_value * 0.5, scenario["budget"] * 0.3)
            
            # Position limits
            if scenario["player"]["position"] == "QB":
                max_bid = min(max_bid, 22)
            
            max_bid = int(max(1, max_bid))
            
            print(f"\n📍 {scenario['desc']}")
            print(f"   Player: {scenario['player']['name']} ({scenario['player']['position']})")
            print(f"   Your Budget: ${scenario['budget']}")
            print(f"   Roster: {scenario['roster_state']}")
            print(f"   Base Value: ${base_value}")
            print(f"   ➜ MAX BID: ${max_bid}")
            
            # Strategy note
            if max_bid >= 50:
                print(f"   Strategy: AGGRESSIVE - This is a cornerstone player")
            elif max_bid >= 20:
                print(f"   Strategy: SELECTIVE - Good value if price is right")
            elif max_bid >= 10:
                print(f"   Strategy: OPPORTUNISTIC - Take if undervalued")
            else:
                print(f"   Strategy: PATIENT - Only if bargain price")


async def main():
    """Run all auction value tests"""
    # Get max bid values table
    await get_max_bid_values()
    
    # Test specific scenarios
    await test_specific_scenarios()
    
    print("\n" + "="*80)
    print("✅ AUCTION VALUE TESTING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())