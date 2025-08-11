#!/usr/bin/env python3
"""
Test value-based drafting logic to ensure smart recommendations.
Validates that the system considers ADP value, positional scarcity, and roster construction.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

# Test scenarios for value-based drafting decisions
VALUE_SCENARIOS = [
    {
        "name": "QB Value in SUPERFLEX",
        "message": "I have pick #5. Josh Allen is available but so is CeeDee Lamb. Who's better value in SUPERFLEX?",
        "expected_recommendation": "Josh Allen",
        "reasoning": "QBs have massive value in SUPERFLEX format"
    },
    {
        "name": "RB Scarcity",
        "message": "It's round 3 and the RB tier is about to drop off. Should I reach for Tony Pollard or take Mike Evans who's ranked higher?",
        "expected_recommendation": "Tony Pollard",
        "reasoning": "Positional scarcity matters more than pure ranking"
    },
    {
        "name": "WR Depth in 3-WR League",
        "message": "Our league starts 3 WRs. Should I prioritize WRs early even if RBs are ranked higher?",
        "expected_recommendation": "WRs",
        "reasoning": "League format requiring 3 WRs increases WR value"
    },
    {
        "name": "Late Round QB",
        "message": "I already have 2 QBs (Allen and Burrow). Should I draft a 3rd QB (Goff) or get RB depth?",
        "expected_recommendation": "RB depth",
        "reasoning": "2 QBs sufficient for SUPERFLEX, need depth elsewhere"
    },
    {
        "name": "TE Premium",
        "message": "Travis Kelce fell to round 3. Is he worth it over RB/WR needs?",
        "expected_recommendation": "Travis Kelce",
        "reasoning": "Elite TE provides significant positional advantage"
    },
    {
        "name": "Handcuff Value",
        "message": "I have Saquon Barkley. In round 12, should I handcuff him or get a WR flyer?",
        "expected_recommendation": "Depends on roster",
        "reasoning": "Handcuffs valuable but roster balance matters"
    },
    {
        "name": "Rookie vs Veteran",
        "message": "Marvin Harrison Jr or Mike Evans in round 3?",
        "expected_recommendation": "Mike Evans",
        "reasoning": "Proven production over rookie potential in redraft"
    },
    {
        "name": "Bye Week Stacking",
        "message": "I have 3 players with week 10 bye. Should I avoid more week 10 players?",
        "expected_recommendation": "Yes, avoid",
        "reasoning": "Bye week diversity prevents weak lineup weeks"
    }
]

async def test_value_scenario(session, scenario):
    """Test a specific value-based drafting scenario."""
    print(f"\nTesting: {scenario['name']}")
    print(f"Query: {scenario['message']}")
    print(f"Expected: {scenario['expected_recommendation']}")
    print("-" * 40)
    
    url = "http://localhost:3000/api/chat"
    payload = {
        "message": scenario['message'],
        "draft_id": "1259757417588072448",
        "roster_id": 5
    }
    
    try:
        async with session.post(url, json=payload, timeout=30) as response:
            if response.status == 200:
                data = await response.json()
                ai_response = data.get("response", "")
                
                # Check if recommendation aligns with expected
                passed = scenario['expected_recommendation'].lower() in ai_response.lower()
                
                print(f"AI Response Preview: {ai_response[:200]}...")
                print(f"Result: {'✅ PASSED' if passed else '❌ FAILED'}")
                print(f"Reasoning Check: {scenario['reasoning']}")
                
                return {
                    "scenario": scenario['name'],
                    "passed": passed,
                    "response": ai_response
                }
            else:
                print(f"❌ Request failed: {response.status}")
                return {
                    "scenario": scenario['name'],
                    "passed": False,
                    "error": f"HTTP {response.status}"
                }
    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            "scenario": scenario['name'],
            "passed": False,
            "error": str(e)
        }

async def test_roster_balance():
    """Test that recommendations properly consider roster balance."""
    print("\n" + "="*60)
    print("ROSTER BALANCE TESTING")
    print("="*60)
    
    test_rosters = [
        {
            "name": "QB Heavy",
            "roster": "I have 3 QBs, 2 RBs, 2 WRs",
            "message": "I have 3 QBs (Allen, Burrow, Lawrence), 2 RBs, and 2 WRs. What position should I target?",
            "expected": ["RB", "WR"],
            "avoid": ["QB"]
        },
        {
            "name": "Zero RB Build",
            "roster": "I have 1 QB, 0 RBs, 4 WRs",
            "message": "I went zero RB and have 4 WRs but no RBs yet. What should I do in round 4?",
            "expected": ["RB"],
            "avoid": ["WR"]
        },
        {
            "name": "Balanced Build",
            "roster": "I have 1 QB, 2 RBs, 2 WRs, 0 TE",
            "message": "I have a balanced roster with 1 QB, 2 RBs, 2 WRs but no TE. What's my priority?",
            "expected": ["TE", "QB"],
            "avoid": []
        },
        {
            "name": "Late Round Needs",
            "roster": "Full starting lineup, no K/DEF",
            "message": "Round 14, I have full starters but no kicker or defense. What now?",
            "expected": ["K", "DEF"],
            "avoid": ["QB", "RB", "WR"]
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        results = []
        for test in test_rosters:
            print(f"\n{test['name']}: {test['roster']}")
            print(f"Query: {test['message']}")
            
            url = "http://localhost:3000/api/chat"
            payload = {
                "message": test['message'],
                "draft_id": "1259757417588072448",
                "roster_id": 5
            }
            
            try:
                async with session.post(url, json=payload, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        ai_response = data.get("response", "")
                        
                        # Check recommendations
                        has_expected = any(pos in ai_response for pos in test['expected'])
                        has_avoided = any(pos in ai_response.upper() for pos in test['avoid'])
                        
                        passed = has_expected and not has_avoided
                        
                        print(f"Expected: {test['expected']}")
                        print(f"Should Avoid: {test['avoid']}")
                        print(f"Result: {'✅ PASSED' if passed else '❌ FAILED'}")
                        
                        results.append({
                            "test": test['name'],
                            "passed": passed
                        })
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append({
                    "test": test['name'],
                    "passed": False
                })
            
            await asyncio.sleep(2)  # Pause between tests
    
    # Summary
    passed_count = sum(1 for r in results if r['passed'])
    print(f"\n{'='*40}")
    print(f"Roster Balance Results: {passed_count}/{len(results)} passed")
    
    return results

async def test_adp_value():
    """Test that system recognizes ADP value opportunities."""
    print("\n" + "="*60)
    print("ADP VALUE TESTING")
    print("="*60)
    
    value_tests = [
        {
            "name": "Falling Star",
            "message": "Justin Jefferson fell to pick 12. Is that good value?",
            "expected_response": ["great value", "must draft", "steal"]
        },
        {
            "name": "Reach Warning",
            "message": "Should I take Brock Bowers at pick 20? His ADP is 45.",
            "expected_response": ["reach", "too early", "wait"]
        },
        {
            "name": "Value vs Need",
            "message": "I need a RB but Travis Kelce (ADP 25) is available at pick 35. What should I do?",
            "expected_response": ["value", "Kelce", "positional advantage"]
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for test in value_tests:
            print(f"\n{test['name']}")
            print(f"Query: {test['message']}")
            
            url = "http://localhost:3000/api/chat"
            payload = {
                "message": test['message'],
                "draft_id": "1259757417588072448",
                "roster_id": 5
            }
            
            try:
                async with session.post(url, json=payload, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        ai_response = data.get("response", "").lower()
                        
                        # Check for expected concepts
                        found_expected = any(expected in ai_response for expected in test['expected_response'])
                        
                        print(f"Looking for: {test['expected_response']}")
                        print(f"Result: {'✅ Found value concept' if found_expected else '❌ Missing value analysis'}")
                        print(f"Response preview: {ai_response[:150]}...")
            except Exception as e:
                print(f"❌ Error: {e}")
            
            await asyncio.sleep(2)

async def main():
    """Run all value-based drafting tests."""
    print("\n" + "="*60)
    print("VALUE-BASED DRAFTING LOGIC TEST SUITE")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Check server is running
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:3000/", timeout=2) as response:
                if response.status != 200:
                    print("❌ Server not responding")
                    return
        except:
            print("❌ Server not running at http://localhost:3000")
            return
    
    # Run test suites
    print("\n1. VALUE SCENARIO TESTS")
    print("="*40)
    
    async with aiohttp.ClientSession() as session:
        scenario_results = []
        for scenario in VALUE_SCENARIOS:
            result = await test_value_scenario(session, scenario)
            scenario_results.append(result)
            await asyncio.sleep(3)  # Pause between heavy queries
    
    # Run roster balance tests
    roster_results = await test_roster_balance()
    
    # Run ADP value tests
    await test_adp_value()
    
    # Final summary
    print("\n" + "="*60)
    print("TEST SUITE SUMMARY")
    print("="*60)
    
    scenario_passed = sum(1 for r in scenario_results if r['passed'])
    print(f"Value Scenarios: {scenario_passed}/{len(scenario_results)} passed")
    
    roster_passed = sum(1 for r in roster_results if r['passed'])
    print(f"Roster Balance: {roster_passed}/{len(roster_results)} passed")
    
    total_tests = len(scenario_results) + len(roster_results)
    total_passed = scenario_passed + roster_passed
    success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"\nOverall Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("✅ Value-based drafting logic validated!")
    elif success_rate >= 60:
        print("⚠️  Some improvements needed in value logic")
    else:
        print("❌ Significant issues with value-based recommendations")

if __name__ == "__main__":
    asyncio.run(main())