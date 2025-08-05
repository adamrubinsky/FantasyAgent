#!/usr/bin/env python3
"""
Test script for FantasyPros caching system
Run: python3 test_caching.py
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_servers.fantasypros_mcp import get_rankings, POSITION_LIMITS

def test_basic_caching():
    """Test basic caching functionality"""
    print("🧪 TEST 1: Basic Caching")
    print("-" * 30)
    
    result = get_rankings(limit=10)
    players = result.get('players', [])
    
    print(f"✅ Retrieved {len(players)} players")
    print(f"📊 Data source: {result.get('source', 'unknown')}")
    print(f"🕐 Last updated: {result.get('last_updated', 'unknown')}")
    
    if players:
        print("\n📍 Sample players:")
        for i, player in enumerate(players[:3]):
            print(f"  {i+1}. {player['name']} ({player['position']}) - Rank: {player['rank']}")
    
    print()

def test_position_filtering():
    """Test position-specific filtering"""
    print("🏈 TEST 2: Position Filtering")
    print("-" * 30)
    
    positions = ['QB', 'RB', 'WR']
    for pos in positions:
        result = get_rankings(position=pos, limit=5)
        players = result.get('players', [])
        print(f"✅ {pos}: {len(players)} players")
        
        if players:
            top_player = players[0]
            print(f"   Top {pos}: {top_player['name']} (Rank: {top_player['rank']})")
    
    print()

def test_comprehensive_limits():
    """Test position-specific limits"""
    print("📊 TEST 3: Position Limits")
    print("-" * 30)
    
    print("Position limits configured:")
    for pos, limit in POSITION_LIMITS.items():
        print(f"  {pos}: {limit} max players")
    
    print("\nTesting actual retrieval:")
    for pos, limit in POSITION_LIMITS.items():
        if pos != 'OVERALL':
            result = get_rankings(position=pos, limit=limit)
            available = len([p for p in result.get('players', []) if p.get('position') == pos])
            print(f"  {pos}: {available} available (limit: {limit})")
    
    print()

def test_specific_players():
    """Test for specific players like Jayden Reed"""
    print("🔍 TEST 4: Specific Player Search")
    print("-" * 30)
    
    result = get_rankings(limit=200)  # Get more players to find Jayden Reed
    players = result.get('players', [])
    
    target_players = ["Josh Allen", "Jayden Reed", "Tee Higgins"]
    
    for target in target_players:
        found = False
        for player in players:
            if target.lower() in player['name'].lower():
                print(f"✅ Found {player['name']}: Rank {player['rank']}, ADP {player['adp']}")
                found = True
                break
        
        if not found:
            print(f"❌ {target} not found in current data")
    
    print()

def test_cache_files():
    """Check cache file status"""
    print("🗂️ TEST 5: Cache Files")
    print("-" * 30)
    
    cache_dir = Path("/tmp/fantasypros_data")
    if cache_dir.exists():
        print(f"✅ Cache directory exists: {cache_dir}")
        
        cache_file = cache_dir / "cached_rankings.json"
        update_file = cache_dir / "last_update.txt"
        
        if cache_file.exists():
            size = cache_file.stat().st_size
            print(f"✅ Cache file: {cache_file} ({size} bytes)")
        else:
            print("📝 Cache file doesn't exist yet")
            
        if update_file.exists():
            with open(update_file, 'r') as f:
                last_update = f.read().strip()
            print(f"✅ Last update: {last_update}")
        else:
            print("📝 Update timestamp doesn't exist yet")
    else:
        print("📝 Cache directory doesn't exist yet (will be created on first use)")
    
    print()

def main():
    """Run all tests"""
    print("🧪 FANTASYPROS CACHING SYSTEM TESTS")
    print("=" * 50)
    print()
    
    try:
        test_basic_caching()
        test_position_filtering()
        test_comprehensive_limits()
        test_specific_players()
        test_cache_files()
        
        print("🎉 ALL TESTS COMPLETED!")
        print("\nNext steps:")
        print("• Try: python3 main.py ask 'Should I draft Josh Allen?'")
        print("• Try: python3 main.py compare 'Tee Higgins' 'Jayden Reed'")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()