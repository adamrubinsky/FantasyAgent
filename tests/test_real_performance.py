#!/usr/bin/env python3
"""
Real-world performance test against the running server.
Tests actual response times with live data.
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime

async def test_chat_endpoint(session, message: str, draft_id: str = "1259757417588072448"):
    """Test the chat endpoint with timing."""
    url = "http://localhost:3000/api/chat"
    payload = {
        "message": message,
        "draft_id": draft_id,
        "roster_id": 5  # Your typical roster position
    }
    
    start = time.time()
    try:
        async with session.post(url, json=payload, timeout=30) as response:
            result = await response.json()
            elapsed = time.time() - start
            return {
                "success": response.status == 200,
                "time": elapsed,
                "response": result.get("response", ""),
                "error": result.get("error", None)
            }
    except asyncio.TimeoutError:
        elapsed = time.time() - start
        return {
            "success": False,
            "time": elapsed,
            "response": "",
            "error": "Timeout after 30 seconds"
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "success": False,
            "time": elapsed,
            "response": "",
            "error": str(e)
        }

async def test_draft_status(session, draft_id: str = "1259757417588072448"):
    """Test draft status endpoint."""
    url = "http://localhost:3000/api/draft-status"
    
    start = time.time()
    try:
        async with session.get(url, timeout=10) as response:
            result = await response.json()
            elapsed = time.time() - start
            return {
                "success": response.status == 200,
                "time": elapsed,
                "picks": result.get("total_picks", 0),
                "current_pick": result.get("current_pick", 0)
            }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "success": False,
            "time": elapsed,
            "error": str(e)
        }

async def run_performance_tests():
    """Run comprehensive performance tests."""
    print("\n" + "="*60)
    print("REAL-WORLD PERFORMANCE TESTING")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Target: <10 second response time")
    print("="*60)
    
    # Test queries of varying complexity
    test_queries = [
        {
            "name": "Simple player query",
            "message": "Should I draft Josh Allen?",
            "expected_time": 5
        },
        {
            "name": "Comparison query",
            "message": "Compare Josh Allen vs Lamar Jackson for SUPERFLEX",
            "expected_time": 8
        },
        {
            "name": "Complex strategy query",
            "message": "What's my draft strategy for rounds 3-5 in SUPERFLEX?",
            "expected_time": 10
        },
        {
            "name": "Roster analysis",
            "message": "Analyze my current roster and suggest needs",
            "expected_time": 10
        },
        {
            "name": "Top available query",
            "message": "Who are the top 3 available players right now?",
            "expected_time": 8
        }
    ]
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        # First test draft status
        print("\n1. Testing Draft Status Endpoint...")
        status = await test_draft_status(session)
        print(f"   Time: {status['time']:.2f}s")
        if status['success']:
            print(f"   ✅ Draft connected - Pick #{status.get('current_pick', 0)}")
        else:
            print(f"   ❌ Failed: {status.get('error', 'Unknown error')}")
        
        # Test each query
        print("\n2. Testing Chat Queries...")
        for i, test in enumerate(test_queries, 1):
            print(f"\n   Test {i}: {test['name']}")
            print(f"   Query: \"{test['message']}\"")
            
            result = await test_chat_endpoint(session, test['message'])
            results.append({
                **test,
                **result
            })
            
            print(f"   Time: {result['time']:.2f}s (target: <{test['expected_time']}s)")
            
            if result['success']:
                # Show first 100 chars of response
                response_preview = result['response'][:100] + "..." if len(result['response']) > 100 else result['response']
                print(f"   Response: {response_preview}")
                
                if result['time'] <= test['expected_time']:
                    print(f"   ✅ PASSED - Under target time!")
                else:
                    print(f"   ⚠️  SLOW - Exceeded target by {result['time'] - test['expected_time']:.1f}s")
            else:
                print(f"   ❌ FAILED: {result.get('error', 'Unknown error')}")
            
            # Brief pause between tests
            await asyncio.sleep(2)
    
    # Print summary
    print("\n" + "="*60)
    print("PERFORMANCE TEST SUMMARY")
    print("="*60)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    if successful:
        avg_time = sum(r['time'] for r in successful) / len(successful)
        max_time = max(r['time'] for r in successful)
        min_time = min(r['time'] for r in successful)
        
        print(f"Successful Tests: {len(successful)}/{len(results)}")
        print(f"Average Response Time: {avg_time:.2f}s")
        print(f"Fastest Response: {min_time:.2f}s")
        print(f"Slowest Response: {max_time:.2f}s")
        
        # Check against targets
        under_target = [r for r in successful if r['time'] <= r['expected_time']]
        print(f"\nTarget Achievement:")
        print(f"  Under target: {len(under_target)}/{len(successful)}")
        
        if avg_time < 10:
            print(f"\n🎯 SUCCESS: Average response time {avg_time:.2f}s is under 10s target!")
        else:
            print(f"\n⚠️  Target missed: Average {avg_time:.2f}s exceeds 10s target")
    
    if failed:
        print(f"\n❌ Failed Tests: {len(failed)}")
        for r in failed:
            print(f"  - {r['name']}: {r.get('error', 'Unknown error')}")
    
    # Performance breakdown
    print("\nPerformance Breakdown:")
    for r in results:
        if r['success']:
            status = "✅" if r['time'] <= r['expected_time'] else "⚠️"
            print(f"  {r['name']}: {r['time']:.2f}s {status}")
    
    # Optimization recommendations
    print("\nOptimization Recommendations:")
    if successful and avg_time > 10:
        print("  1. Implement caching for similar queries")
        print("  2. Reduce context size sent to AI")
        print("  3. Use parallel processing for data fetching")
        print("  4. Consider pre-computing common scenarios")
        print("  5. Optimize task descriptions for CrewAI")

async def test_concurrent_requests():
    """Test how the system handles concurrent requests."""
    print("\n" + "="*60)
    print("CONCURRENT REQUEST TESTING")
    print("="*60)
    
    queries = [
        "Who should I draft at pick 44?",
        "Compare CeeDee Lamb vs Justin Jefferson",
        "What QBs are available?"
    ]
    
    async with aiohttp.ClientSession() as session:
        print("\nSending 3 concurrent requests...")
        start = time.time()
        
        tasks = [test_chat_endpoint(session, q) for q in queries]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start
        
        print(f"Total time for 3 concurrent requests: {total_time:.2f}s")
        
        for i, (query, result) in enumerate(zip(queries, results), 1):
            print(f"\nRequest {i}: \"{query}\"")
            print(f"  Time: {result['time']:.2f}s")
            print(f"  Success: {'✅' if result['success'] else '❌'}")
        
        avg_time = sum(r['time'] for r in results) / len(results)
        print(f"\nAverage response time: {avg_time:.2f}s")
        
        if all(r['success'] for r in results) and avg_time < 15:
            print("✅ Concurrent handling successful!")
        else:
            print("⚠️  Issues with concurrent request handling")

async def main():
    """Run all performance tests."""
    # Check if server is running first
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:3000/", timeout=2) as response:
                if response.status != 200:
                    print("❌ Server not responding properly")
                    return
    except:
        print("❌ Server not running at http://localhost:3000")
        print("Please start the server with: python3 dev_server.py")
        return
    
    # Run tests
    await run_performance_tests()
    
    # Test concurrent handling
    print("\n" + "="*60)
    await test_concurrent_requests()
    
    print("\n✅ All performance tests complete!")

if __name__ == "__main__":
    asyncio.run(main())