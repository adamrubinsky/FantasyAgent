#!/usr/bin/env python3
"""
Test Yahoo agents with various queries to verify they respond differently
"""
import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')
load_dotenv('.env')

from yahoo_agents.agents.yahoo_snake_agent import YahooSnakeDraftAgent
from yahoo_agents.agents.yahoo_auction_agent import YahooAuctionAgent

async def test_yahoo_snake():
    """Test Yahoo Snake agent with different queries"""
    print("\n" + "="*60)
    print("TESTING YAHOO SNAKE DRAFT AGENT")
    print("="*60)
    
    agent = YahooSnakeDraftAgent()
    
    # Test different queries
    queries = [
        "Who should I draft?",
        "Who other than Jamarr Chase?",
        "RB or WR?",
        "Best QB available?",
        "Any sleepers?",
        "Value picks?"
    ]
    
    for query in queries:
        print(f"\n📝 Query: {query}")
        context = {
            "query": query,
            "round": 3,
            "pick_number": 28,
            "user_roster": {
                "QB": [],
                "RB": ["Bijan Robinson"],
                "WR": ["Tyreek Hill"],
                "TE": [],
                "K": [],
                "DEF": []
            }
        }
        
        result = await agent.get_recommendation(context)
        
        # Check recommendations
        recs = result.get("recommendations", [])
        if recs:
            print(f"✅ Got {len(recs)} recommendations:")
            for i, rec in enumerate(recs[:2], 1):  # Show first 2
                print(f"   {i}. {rec['name']} ({rec['position']})")
        else:
            print("❌ No recommendations returned")
        
        # Check if response varies
        if "strategy" in result:
            print(f"📊 Strategy: {result['strategy'][:100]}...")
        
        print(f"⏱️  Response time: {result.get('total_time_ms', 0)}ms")

async def test_yahoo_auction():
    """Test Yahoo Auction agent with different queries"""
    print("\n" + "="*60)
    print("TESTING YAHOO AUCTION AGENT")
    print("="*60)
    
    agent = YahooAuctionAgent()
    
    # Test different queries
    queries = [
        "Who should I nominate?",
        "RB or WR?",
        "Should I nominate a QB?",
        "Any cheap values?",
        "Stars and scrubs strategy?"
    ]
    
    for query in queries:
        print(f"\n📝 Query: {query}")
        context = {
            "query": query,
            "remaining_budget": 145,
            "spent_budget": 55,
            "user_roster": {
                "QB": [],
                "RB": ["Jonathan Taylor"],
                "WR": [],
                "TE": [],
                "DEF": []
            },
            "slots_filled": 1,
            "slots_remaining": 14,
            "stars_acquired": 1
        }
        
        result = await agent.get_bid_recommendation(context)
        
        # Check nomination suggestion
        nom = result.get("nomination", {})
        if nom:
            print(f"✅ Nomination suggestion:")
            print(f"   Type: {nom.get('type', 'N/A')}")
            print(f"   Positions: {nom.get('positions', [])}")
            print(f"   Price: {nom.get('price_range', 'N/A')}")
            print(f"   Reason: {nom.get('reason', 'N/A')[:100]}...")
        else:
            print("❌ No nomination suggestion")
        
        # Check strategy
        if "strategy" in result:
            print(f"📊 Strategy: {result['strategy'][:100]}...")
        
        print(f"⏱️  Response time: {result.get('response_ms', 0)}ms")

async def main():
    """Run all tests"""
    await test_yahoo_snake()
    await test_yahoo_auction()
    print("\n✅ Test complete! Check if responses vary based on queries.")

if __name__ == "__main__":
    asyncio.run(main())