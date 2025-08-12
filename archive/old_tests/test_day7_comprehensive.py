#!/usr/bin/env python3
"""
Day 7 Comprehensive Test Suite
Tests all critical functionality and provides detailed output
"""

import requests
import json
import time
from datetime import datetime

def test_connection(draft_url, user_roster_id=5):
    """Test connecting to a draft"""
    print("\n" + "="*60)
    print("1️⃣  TESTING DRAFT CONNECTION")
    print("="*60)
    
    response = requests.post('http://localhost:3000/api/start-draft-monitoring', 
                             json={'draft_url': draft_url, 'user_roster_id': user_roster_id},
                             timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Connected to draft successfully")
        print(f"   Draft ID: {data.get('draft_id')}")
        print(f"   User Roster: {data.get('user_roster_id')}")
        return True
    else:
        print(f"❌ Connection failed: {response.status_code}")
        return False

def test_draft_status():
    """Test getting draft status"""
    print("\n" + "="*60)
    print("2️⃣  TESTING DRAFT STATUS")
    print("="*60)
    
    response = requests.get('http://localhost:3000/api/draft-status', timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        status = data.get('draft_status', {})
        print(f"✅ Draft status retrieved")
        print(f"   Current Pick: #{status.get('current_pick', 0)}")
        print(f"   User Next Pick: #{status.get('user_next_pick', 0)}")
        print(f"   Picks Until User: {status.get('picks_until_user', 'N/A')}")
        print(f"   Available Players: {status.get('available_count', 0)}")
        print(f"   User Roster Size: {len(status.get('user_roster', []))}")
        return status
    else:
        print(f"❌ Status retrieval failed: {response.status_code}")
        return None

def test_ai_recommendations(queries):
    """Test AI recommendations with various queries"""
    print("\n" + "="*60)
    print("3️⃣  TESTING AI RECOMMENDATIONS")
    print("="*60)
    
    results = []
    
    for query in queries:
        print(f"\n📝 Query: '{query}'")
        print("-" * 50)
        
        start_time = time.time()
        try:
            response = requests.post('http://localhost:3000/api/chat', 
                                    json={'message': query},
                                    timeout=45)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                resp_text = data.get('response', '')
                agent_type = data.get('agent_type', 'Unknown')
                
                # Check if it's a fallback response
                fallback_phrases = [
                    'focus on proven', 'best available', 'without specific context',
                    'general advice', 'typically', 'i would need'
                ]
                is_fallback = any(phrase in resp_text.lower() for phrase in fallback_phrases)
                
                # Check if it uses real draft context
                uses_context = any(term in resp_text for term in [
                    'pick #', 'Pick #', 'round', 'Round', 'your roster', 'already drafted'
                ])
                
                print(f"⏱️  Response Time: {elapsed:.1f}s")
                print(f"🤖 Agent Type: {agent_type}")
                print(f"📊 Response Quality: {'❌ FALLBACK' if is_fallback else '✅ REAL AI'}")
                print(f"🎯 Uses Context: {'✅ YES' if uses_context else '❌ NO'}")
                print(f"\n📄 Response (first 400 chars):")
                print(f"   {resp_text[:400]}...")
                
                results.append({
                    'query': query,
                    'time': elapsed,
                    'is_fallback': is_fallback,
                    'uses_context': uses_context,
                    'agent_type': agent_type
                })
            else:
                print(f"❌ Request failed: {response.status_code}")
                if response.text:
                    print(f"   Error: {response.text[:200]}")
                    
        except requests.exceptions.Timeout:
            print(f"⏱️  TIMEOUT after 45 seconds")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return results

def test_rankings():
    """Test if rankings are properly loaded"""
    print("\n" + "="*60)
    print("4️⃣  TESTING RANKINGS DATA")
    print("="*60)
    
    # Test a query that should use rankings
    query = "Who are the top 5 QBs in SUPERFLEX rankings?"
    
    start_time = time.time()
    response = requests.post('http://localhost:3000/api/chat', 
                            json={'message': query},
                            timeout=45)
    elapsed = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        resp_text = data.get('response', '')
        
        # Check for specific QBs that should be in SUPERFLEX top 5
        expected_qbs = ['Josh Allen', 'Lamar Jackson', 'Jayden Daniels', 'Jalen Hurts', 'Joe Burrow']
        found_qbs = [qb for qb in expected_qbs if qb in resp_text]
        
        print(f"✅ Rankings query completed in {elapsed:.1f}s")
        print(f"📊 Found {len(found_qbs)}/{len(expected_qbs)} expected QBs:")
        for qb in expected_qbs:
            status = "✅" if qb in resp_text else "❌"
            print(f"   {status} {qb}")
        
        return len(found_qbs) >= 3  # Success if at least 3 of the top 5 are mentioned
    else:
        print(f"❌ Rankings test failed: {response.status_code}")
        return False

def main():
    print("\n" + "🏈"*30)
    print(" "*20 + "FANTASY AGENT - DAY 7 COMPREHENSIVE TEST")
    print("🏈"*30)
    print(f"\n📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test configuration
    draft_url = 'https://sleeper.com/draft/nfl/1260758387386241025'
    user_roster_id = 5
    
    # Test queries
    test_queries = [
        "Who should I draft with pick #92?",
        "Compare Tyreek Hill vs CeeDee Lamb for my team",
        "What QB offers best value in round 8?",
    ]
    
    # Run tests
    print(f"\n🎯 Testing with Mock Draft: {draft_url}")
    print(f"👤 User Roster ID: {user_roster_id}")
    
    # Test 1: Connection
    connected = test_connection(draft_url, user_roster_id)
    
    if connected:
        # Wait for connection to stabilize
        time.sleep(2)
        
        # Test 2: Draft Status
        status = test_draft_status()
        
        # Test 3: AI Recommendations
        results = test_ai_recommendations(test_queries)
        
        # Test 4: Rankings
        rankings_work = test_rankings()
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total_tests = len(results) + 2  # AI tests + connection + rankings
        successful = sum(1 for r in results if not r['is_fallback']) + (1 if connected else 0) + (1 if rankings_work else 0)
        
        print(f"\n✅ Successful: {successful}/{total_tests}")
        print(f"❌ Failed: {total_tests - successful}/{total_tests}")
        
        if results:
            avg_time = sum(r['time'] for r in results) / len(results)
            print(f"⏱️  Average Response Time: {avg_time:.1f}s")
            
            context_using = sum(1 for r in results if r['uses_context'])
            print(f"🎯 Queries Using Context: {context_using}/{len(results)}")
        
        print("\n🔍 Key Issues:")
        if not rankings_work:
            print("   ❌ Rankings not returning expected SUPERFLEX QBs")
        if results and all(r['is_fallback'] for r in results):
            print("   ❌ All AI responses are fallbacks")
        if results and not any(r['uses_context'] for r in results):
            print("   ❌ AI not using draft context")
        
        if successful == total_tests:
            print("\n🎉 ALL TESTS PASSED!")
        elif successful > total_tests / 2:
            print("\n⚠️  PARTIAL SUCCESS - Some issues need fixing")
        else:
            print("\n❌ CRITICAL ISSUES - System not working properly")
    else:
        print("\n❌ Cannot proceed - connection failed")

if __name__ == "__main__":
    main()