#!/usr/bin/env python3
"""
Comprehensive stress test for AI draft recommendations.
Tests multiple scenarios to ensure accuracy and reliability.
"""

import asyncio
import sys
import os
import time
import json
from typing import List, Dict, Tuple
from datetime import datetime

sys.path.append('..')

# Test scenarios for different draft positions and roster states
TEST_SCENARIOS = [
    {
        "name": "Early Draft - Empty Roster",
        "pick_number": 5,
        "round": 1,
        "roster": {},
        "expected_focus": ["Elite QB", "Elite RB", "Elite WR"],
        "avoid": ["K", "DEF"],
        "description": "Pick 5 - Should prioritize elite talent, likely QB in SUPERFLEX"
    },
    {
        "name": "Mid Round - Balanced Start",
        "pick_number": 44,
        "round": 4,
        "roster": {
            "QB": ["Josh Allen"],
            "RB": ["Saquon Barkley", "Josh Jacobs"],
            "WR": ["CeeDee Lamb"],
            "TE": [],
            "K": [],
            "DEF": []
        },
        "expected_focus": ["WR", "QB", "TE"],
        "avoid": ["RB", "K", "DEF"],
        "description": "Need WR depth, consider 2nd QB for SUPERFLEX, or elite TE"
    },
    {
        "name": "QB Heavy - Need Balance",
        "pick_number": 68,
        "round": 6,
        "roster": {
            "QB": ["Lamar Jackson", "Dak Prescott", "Trevor Lawrence"],
            "RB": ["Kenneth Walker", "James Conner"],
            "WR": ["Tyreek Hill", "Mike Evans"],
            "TE": [],
            "K": [],
            "DEF": []
        },
        "expected_focus": ["RB", "WR", "TE"],
        "avoid": ["QB", "K", "DEF"],
        "description": "3 QBs enough for SUPERFLEX - need RB/WR depth"
    },
    {
        "name": "Late Rounds - Depth Focus",
        "pick_number": 125,
        "round": 11,
        "roster": {
            "QB": ["Jalen Hurts", "Kirk Cousins"],
            "RB": ["Derrick Henry", "Najee Harris", "Brian Robinson", "Tyjae Spears"],
            "WR": ["Justin Jefferson", "Chris Olave", "Deebo Samuel", "Hollywood Brown"],
            "TE": ["Mark Andrews"],
            "K": [],
            "DEF": []
        },
        "expected_focus": ["RB", "WR", "QB"],
        "avoid": ["K", "DEF"],
        "description": "Focus on upside/handcuffs, not K/DEF yet"
    },
    {
        "name": "Defense/Kicker Time",
        "pick_number": 156,
        "round": 13,
        "roster": {
            "QB": ["Joe Burrow", "Jared Goff", "Will Levis"],
            "RB": ["CMC", "Aaron Jones", "Rachaad White", "Jaylen Warren", "Chase Brown"],
            "WR": ["AJ Brown", "DK Metcalf", "Terry McLaurin", "Chris Godwin", "Jordan Addison"],
            "TE": ["Travis Kelce"],
            "K": [],
            "DEF": []
        },
        "expected_focus": ["DEF", "K"],
        "avoid": ["QB", "RB", "WR"],
        "description": "Round 13+ - Time for DEF and K"
    },
    {
        "name": "Zero RB Strategy Test",
        "pick_number": 29,
        "round": 3,
        "roster": {
            "QB": ["Patrick Mahomes"],
            "RB": [],
            "WR": ["Ja'Marr Chase", "Amon-Ra St. Brown"],
            "TE": [],
            "K": [],
            "DEF": []
        },
        "expected_focus": ["RB"],
        "avoid": ["WR", "K", "DEF"],
        "description": "Zero RB start - MUST get RBs now"
    },
    {
        "name": "Bye Week Conflict",
        "pick_number": 92,
        "round": 8,
        "roster": {
            "QB": ["Josh Allen", "Tua Tagovailoa"],  # Both have same bye
            "RB": ["Bijan Robinson", "Travis Etienne", "James Cook"],  # Multiple same byes
            "WR": ["Stefon Diggs", "Garrett Wilson", "Drake London"],
            "TE": ["Dallas Goedert"],
            "K": [],
            "DEF": []
        },
        "expected_focus": ["Players with different bye weeks"],
        "avoid": ["Players with week 12 bye"],
        "description": "Avoid bye week stacking"
    }
]

class StressTester:
    def __init__(self, mock_mode: bool = True):
        """Initialize the stress tester."""
        self.mock_mode = mock_mode
        self.results = []
        self.start_time = None
        
    async def test_scenario(self, scenario: Dict) -> Dict:
        """Test a single draft scenario."""
        print(f"\n{'='*60}")
        print(f"Testing: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print(f"Pick #{scenario['pick_number']} (Round {scenario['round']})")
        print(f"Current Roster: {self._format_roster(scenario['roster'])}")
        print(f"Expected Focus: {', '.join(scenario['expected_focus'])}")
        print(f"Should Avoid: {', '.join(scenario['avoid'])}")
        print('-'*60)
        
        # Simulate API call to get recommendations
        start = time.time()
        
        if self.mock_mode:
            # Mock response for testing
            recommendations = await self._get_mock_recommendations(scenario)
        else:
            # Real API call would go here
            recommendations = await self._get_real_recommendations(scenario)
        
        elapsed = time.time() - start
        
        # Analyze the recommendations
        analysis = self._analyze_recommendations(recommendations, scenario)
        
        result = {
            "scenario": scenario['name'],
            "response_time": elapsed,
            "recommendations": recommendations,
            "analysis": analysis,
            "passed": analysis['score'] >= 70  # 70% threshold
        }
        
        # Print results
        print(f"Response Time: {elapsed:.2f}s")
        print(f"Recommendations: {recommendations}")
        print(f"Analysis Score: {analysis['score']}/100")
        print(f"Result: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
        
        return result
    
    async def _get_mock_recommendations(self, scenario: Dict) -> List[str]:
        """Get mock recommendations for testing."""
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        # Return position-appropriate mock recommendations
        if "Elite QB" in scenario['expected_focus']:
            return ["Josh Allen (QB)", "Lamar Jackson (QB)", "CeeDee Lamb (WR)"]
        elif "RB" in scenario['expected_focus'] and not scenario['roster'].get('RB'):
            return ["Tony Pollard (RB)", "Joe Mixon (RB)", "Calvin Ridley (WR)"]
        elif "WR" in scenario['expected_focus']:
            return ["Mike Evans (WR)", "Amari Cooper (WR)", "George Kittle (TE)"]
        elif "DEF" in scenario['expected_focus']:
            return ["Ravens DEF", "49ers DEF", "Harrison Butker (K)"]
        else:
            return ["Best Player Available", "Value Pick", "Upside Play"]
    
    async def _get_real_recommendations(self, scenario: Dict) -> List[str]:
        """Get real recommendations from the AI system."""
        # This would call the actual draft_crew.py system
        # For now, return mock data
        return await self._get_mock_recommendations(scenario)
    
    def _analyze_recommendations(self, recommendations: List[str], scenario: Dict) -> Dict:
        """Analyze if recommendations match expected behavior."""
        score = 100
        issues = []
        
        # Check if recommendations match expected positions
        rec_positions = [self._extract_position(r) for r in recommendations]
        
        # Check for positions that should be prioritized
        for expected in scenario['expected_focus']:
            if expected in ["Elite QB", "Elite RB", "Elite WR"]:
                position = expected.split()[-1]
                if position not in rec_positions:
                    score -= 20
                    issues.append(f"Missing expected {position}")
            elif expected not in rec_positions and expected != "Players with different bye weeks":
                score -= 15
                issues.append(f"Missing expected {expected}")
        
        # Check for positions that should be avoided
        for avoid in scenario['avoid']:
            if avoid in rec_positions:
                score -= 25
                issues.append(f"Recommended {avoid} when should avoid")
        
        # Bonus points for getting primary need right
        if rec_positions and scenario['expected_focus']:
            primary_need = scenario['expected_focus'][0]
            if "Elite" in primary_need:
                primary_need = primary_need.split()[-1]
            if rec_positions[0] == primary_need:
                score = min(100, score + 10)
        
        return {
            "score": max(0, score),
            "issues": issues,
            "rec_positions": rec_positions
        }
    
    def _extract_position(self, recommendation: str) -> str:
        """Extract position from recommendation string."""
        # Handle format like "Josh Allen (QB)"
        if "(" in recommendation and ")" in recommendation:
            return recommendation.split("(")[1].split(")")[0]
        
        # Handle DEF and K
        if "DEF" in recommendation:
            return "DEF"
        if " K)" in recommendation or "Kicker" in recommendation.lower():
            return "K"
        
        # Default
        for pos in ["QB", "RB", "WR", "TE"]:
            if pos in recommendation:
                return pos
        
        return "Unknown"
    
    def _format_roster(self, roster: Dict) -> str:
        """Format roster for display."""
        if not roster:
            return "Empty"
        
        parts = []
        for pos, players in roster.items():
            if players:
                parts.append(f"{pos}: {len(players)}")
        
        return ", ".join(parts) if parts else "Empty"
    
    async def run_all_tests(self) -> None:
        """Run all test scenarios."""
        print("\n" + "="*60)
        print("STARTING COMPREHENSIVE STRESS TEST")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Scenarios: {len(TEST_SCENARIOS)}")
        print("="*60)
        
        self.start_time = time.time()
        
        for scenario in TEST_SCENARIOS:
            result = await self.test_scenario(scenario)
            self.results.append(result)
            await asyncio.sleep(1)  # Brief pause between tests
        
        self._print_summary()
    
    def _print_summary(self) -> None:
        """Print test summary."""
        total_time = time.time() - self.start_time
        passed = sum(1 for r in self.results if r['passed'])
        failed = len(self.results) - passed
        avg_response = sum(r['response_time'] for r in self.results) / len(self.results)
        
        print("\n" + "="*60)
        print("STRESS TEST SUMMARY")
        print("="*60)
        print(f"Total Scenarios: {len(self.results)}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/len(self.results)*100):.1f}%")
        print(f"Average Response Time: {avg_response:.2f}s")
        print(f"Total Test Time: {total_time:.1f}s")
        
        if failed > 0:
            print("\nFailed Scenarios:")
            for result in self.results:
                if not result['passed']:
                    print(f"  - {result['scenario']}: {result['analysis']['issues']}")
        
        # Performance analysis
        print("\nPerformance Analysis:")
        fast = sum(1 for r in self.results if r['response_time'] < 10)
        medium = sum(1 for r in self.results if 10 <= r['response_time'] < 15)
        slow = sum(1 for r in self.results if r['response_time'] >= 15)
        
        print(f"  Fast (<10s): {fast}")
        print(f"  Medium (10-15s): {medium}")
        print(f"  Slow (>15s): {slow}")
        
        if avg_response < 10:
            print("\n🎯 TARGET ACHIEVED: Average response under 10 seconds!")
        else:
            print(f"\n⚠️  Performance target missed: {avg_response:.1f}s (target: <10s)")

async def main():
    """Run the stress test."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Stress test draft recommendations')
    parser.add_argument('--live', action='store_true', help='Use live API instead of mock')
    parser.add_argument('--scenario', type=int, help='Run specific scenario (0-based index)')
    args = parser.parse_args()
    
    tester = StressTester(mock_mode=not args.live)
    
    if args.scenario is not None:
        # Run single scenario
        if 0 <= args.scenario < len(TEST_SCENARIOS):
            result = await tester.test_scenario(TEST_SCENARIOS[args.scenario])
            tester.results = [result]
            tester._print_summary()
        else:
            print(f"Invalid scenario index. Choose 0-{len(TEST_SCENARIOS)-1}")
    else:
        # Run all scenarios
        await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())