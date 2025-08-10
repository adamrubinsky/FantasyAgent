#!/usr/bin/env python3
"""
Live System Testing Script for Fantasy Draft Assistant
Created: August 8, 2025 (End of Day 4)

This script tests the ACTUAL running system to verify it works correctly,
rather than just assuming code changes work.

Usage:
    python tests/test_live_system.py --draft-url "https://sleeper.com/draft/nfl/..." --roster-id 5 --expected-pick 125
"""

import requests
import json
import time
import argparse
from typing import Dict, List, Any
from datetime import datetime

class LiveSystemTester:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.draft_url = None
        self.roster_id = None
        self.test_results = []
        
    def log_result(self, test_name: str, passed: bool, details: str):
        """Log test results for final report"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
        # Print immediately
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            print(f"  Details: {details}")
    
    def test_server_running(self) -> bool:
        """Test 1: Is the server actually running?"""
        try:
            response = requests.get(f"{self.base_url}/api/dev-status", timeout=2)
            if response.status_code == 200:
                data = response.json()
                self.log_result("Server Running", True, f"Server active on port {data.get('port', 'unknown')}")
                return True
            else:
                self.log_result("Server Running", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Server Running", False, str(e))
            return False
    
    def test_draft_connection(self, draft_url: str, roster_id: int) -> bool:
        """Test 2: Can we connect to the draft?"""
        self.draft_url = draft_url
        self.roster_id = roster_id
        
        try:
            # Connect to draft
            response = requests.post(
                f"{self.base_url}/api/start-draft-monitoring",
                json={"draft_url": draft_url, "user_roster_id": roster_id},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_result("Draft Connection", True, f"Connected to draft: {data.get('draft_id', 'unknown')}")
                    return True
                else:
                    self.log_result("Draft Connection", False, f"Connection failed: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_result("Draft Connection", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Draft Connection", False, str(e))
            return False
    
    def test_draft_status(self, expected_pick: int = None) -> Dict:
        """Test 3: Check draft status and verify pick number"""
        try:
            response = requests.get(f"{self.base_url}/api/draft-status", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    status = data.get("draft_status", {})
                    current_pick = status.get("current_pick")
                    
                    # Check if pick number matches expected
                    if expected_pick and current_pick:
                        if abs(current_pick - expected_pick) <= 1:  # Allow 1 pick difference
                            self.log_result("Pick Number", True, f"Current pick #{current_pick} (expected ~#{expected_pick})")
                        else:
                            self.log_result("Pick Number", False, 
                                          f"Wrong pick! Shows #{current_pick}, expected #{expected_pick}")
                    else:
                        self.log_result("Pick Number", True, f"Current pick: #{current_pick}")
                    
                    return status
                else:
                    self.log_result("Draft Status", False, "No active draft")
                    return {}
            else:
                self.log_result("Draft Status", False, f"Status code: {response.status_code}")
                return {}
        except Exception as e:
            self.log_result("Draft Status", False, str(e))
            return {}
    
    def test_roster_detection(self, expected_players: List[str] = None) -> bool:
        """Test 4: Is the roster being detected correctly?"""
        try:
            # Get chat response which should include roster
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={"message": "What is my current roster?"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                message = data.get("response", "")
                
                # Check for "0 QB, 0 RB" which indicates broken roster tracking
                if "0 QB, 0 RB, 0 WR, 0 TE" in message:
                    self.log_result("Roster Detection", False, 
                                  "Roster shows all zeros - tracking is BROKEN!")
                    return False
                
                # Check if expected players are mentioned
                if expected_players:
                    found_players = [p for p in expected_players if p.lower() in message.lower()]
                    if found_players:
                        self.log_result("Roster Detection", True, 
                                      f"Found players: {', '.join(found_players)}")
                        return True
                    else:
                        self.log_result("Roster Detection", False, 
                                      f"None of expected players found: {expected_players}")
                        return False
                else:
                    # Just check that it's not all zeros
                    if any(x in message for x in ["1 QB", "2 QB", "1 RB", "2 RB", "3 RB"]):
                        self.log_result("Roster Detection", True, "Roster has non-zero counts")
                        return True
                    else:
                        self.log_result("Roster Detection", False, "Can't determine roster status")
                        return False
            else:
                self.log_result("Roster Detection", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Roster Detection", False, str(e))
            return False
    
    def test_ai_recommendations(self) -> bool:
        """Test 5: Are AI recommendations working (not fallback)?"""
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={"message": "Who should I draft next?"},
                timeout=35  # Give AI time to work
            )
            
            if response.status_code == 200:
                data = response.json()
                message = data.get("response", "")
                
                # Check for fallback message
                if "Focus on proven performers" in message or "For SUPERFLEX leagues, remember" in message:
                    self.log_result("AI Recommendations", False, 
                                  "AI is using generic fallback - NOT WORKING!")
                    return False
                
                # Check for actual player names
                if any(name in message for name in ["Brandon Aubrey", "Jake Bates", "Rhamondre", 
                                                    "Kyle Pitts", "Dallas Goedert", "Keon Coleman"]):
                    self.log_result("AI Recommendations", True, "AI provided specific player names")
                    return True
                
                # Check if it's recommending kicker first (bad for round 11)
                if "Primary Need: KICKER" in message:
                    self.log_result("AI Recommendations", False, 
                                  "Recommending kicker in round 11 - wrong priority!")
                    return False
                
                self.log_result("AI Recommendations", False, "Response unclear, might be broken")
                return False
            else:
                self.log_result("AI Recommendations", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("AI Recommendations", False, str(e))
            return False
    
    def test_proactive_recommendations(self) -> bool:
        """Test 6: Check if proactive recommendations are present"""
        try:
            status = self.test_draft_status()
            proactive = status.get("proactive_recommendation", {})
            
            if proactive.get("proactive_generated"):
                self.log_result("Proactive Recommendations", True, 
                              f"Generated {proactive.get('picks_ahead')} picks ahead")
                return True
            else:
                picks_until = status.get("picks_until_user")
                if picks_until and picks_until <= 6:
                    self.log_result("Proactive Recommendations", False, 
                                  f"Should trigger ({picks_until} picks away) but didn't!")
                    return False
                else:
                    self.log_result("Proactive Recommendations", True, 
                                  f"Not triggered yet ({picks_until} picks away)")
                    return True
        except Exception as e:
            self.log_result("Proactive Recommendations", False, str(e))
            return False
    
    def run_all_tests(self, draft_url: str, roster_id: int, expected_pick: int = None,
                      expected_players: List[str] = None) -> Dict:
        """Run all tests and generate report"""
        print("\n" + "="*60)
        print("🧪 FANTASY DRAFT ASSISTANT - LIVE SYSTEM TEST")
        print("="*60)
        print(f"Draft URL: {draft_url}")
        print(f"Roster ID: {roster_id}")
        print(f"Expected Pick: #{expected_pick}" if expected_pick else "Expected Pick: Not specified")
        print(f"Expected Players: {', '.join(expected_players)}" if expected_players else "Expected Players: Not specified")
        print("="*60 + "\n")
        
        # Run tests in order
        if not self.test_server_running():
            print("\n⚠️  Server not running! Start with: python3 dev_server.py")
            return self.generate_report()
        
        time.sleep(1)
        
        if not self.test_draft_connection(draft_url, roster_id):
            print("\n⚠️  Can't connect to draft! Check URL and roster ID")
            return self.generate_report()
        
        time.sleep(2)  # Give system time to load
        
        self.test_draft_status(expected_pick)
        time.sleep(1)
        
        self.test_roster_detection(expected_players)
        time.sleep(1)
        
        print("\n🤖 Testing AI (this may take 30 seconds)...")
        self.test_ai_recommendations()
        
        self.test_proactive_recommendations()
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate final test report"""
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = sum(1 for r in self.test_results if not r["passed"])
        
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "N/A")
        
        if failed > 0:
            print("\n⚠️  CRITICAL FAILURES:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n" + "="*60)
        
        return {
            "passed": passed,
            "failed": failed,
            "results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }


def main():
    parser = argparse.ArgumentParser(description="Test Fantasy Draft Assistant Live System")
    parser.add_argument("--draft-url", required=True, help="Sleeper draft URL")
    parser.add_argument("--roster-id", type=int, required=True, help="Your roster position (1-12)")
    parser.add_argument("--expected-pick", type=int, help="Expected current pick number")
    parser.add_argument("--expected-players", nargs="+", help="Players you've drafted (for roster check)")
    parser.add_argument("--base-url", default="http://localhost:3000", help="Server URL")
    
    args = parser.parse_args()
    
    tester = LiveSystemTester(args.base_url)
    report = tester.run_all_tests(
        draft_url=args.draft_url,
        roster_id=args.roster_id,
        expected_pick=args.expected_pick,
        expected_players=args.expected_players
    )
    
    # Save report to file
    with open("test_results.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📁 Full report saved to: test_results.json")
    
    # Exit with error code if any tests failed
    exit(0 if report["failed"] == 0 else 1)


if __name__ == "__main__":
    main()