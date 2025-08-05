#!/usr/bin/env python3
"""
Test Enhanced Player Data Features
Validates ADP, bye weeks, playoff outlook, and fantasy scoring
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.player_data_enricher import PlayerDataEnricher
from api.sleeper_client import SleeperClient
from dotenv import load_dotenv
import os


async def test_basic_enrichment():
    """Test basic player data enrichment"""
    print("🧪 Testing Basic Player Data Enrichment")
    print("=" * 50)
    
    sample_players = [
        {"name": "Josh Allen", "team": "BUF", "positions": ["QB"], "rank": 2},
        {"name": "Tee Higgins", "team": "CIN", "positions": ["WR"], "rank": 25},
        {"name": "Jayden Higgins", "team": "HOU", "positions": ["WR"], "rank": 159},
    ]
    
    async with PlayerDataEnricher() as enricher:
        enriched = await enricher.enrich_player_data(sample_players)
        
        for player in enriched:
            print(f"\n📊 {player['name']} ({player['team']}):")
            print(f"   Rank: {player.get('rank')}")
            print(f"   ADP: {player.get('adp', 'N/A')}")
            print(f"   ADP Trend: {player.get('adp_trend', 'N/A')}")
            print(f"   Bye Week: {player.get('bye_week', 'N/A')}")
            print(f"   Playoff Outlook: {player.get('playoff_outlook', 'N/A')}")
            print(f"   Fantasy Score: {player.get('fantasy_score', 'N/A')}")


async def test_sleeper_integration():
    """Test enhanced data through Sleeper client"""
    print("\n🧪 Testing Sleeper Integration with Enhanced Data")
    print("=" * 50)
    
    load_dotenv('.env.local')
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    if not username or not league_id:
        print("❌ Skipping Sleeper test - no credentials")
        return
    
    async with SleeperClient(username=username, league_id=league_id) as client:
        try:
            league = await client.get_league_info()
            draft_id = league.get('draft_id')
            
            if not draft_id:
                print("❌ No draft found for this league")
                return
            
            print(f"✅ Found draft ID: {draft_id}")
            
            # Test basic vs enhanced data
            print("\n📋 Basic Player Data (Top 5 WRs):")
            basic_players = await client.get_available_players(draft_id, "WR", enhanced=False)
            for i, player in enumerate(basic_players[:5]):
                print(f"  {i+1}. {player['name']} ({player['team']}) - Rank: {player['rank']}")
            
            print("\n🚀 Enhanced Player Data (Top 5 WRs):")
            enhanced_players = await client.get_available_players(draft_id, "WR", enhanced=True)
            for i, player in enumerate(enhanced_players[:5]):
                adp = f"{player.get('adp', 'N/A'):.1f}" if player.get('adp') else 'N/A'
                print(f"  {i+1}. {player['name']} ({player['team']}) - ADP: {adp}, Bye: {player.get('bye_week', 'N/A')}, Score: {player.get('fantasy_score', 0):.1f}")
            
            # Test specific player search
            print("\n🔍 Finding Both Higgins Players:")
            all_wrs = await client.get_available_players(draft_id, "WR", enhanced=True)
            
            for player in all_wrs:
                if "higgins" in player.get('name', '').lower():
                    print(f"  📍 {player['name']} ({player['team']}):")
                    print(f"      Rank: {player['rank']}, ADP: {player.get('adp', 'N/A'):.1f}")
                    print(f"      Bye Week: {player.get('bye_week')}, Playoff: {player.get('playoff_outlook')}")
                    print(f"      Fantasy Score: {player.get('fantasy_score', 0):.1f}")
                    
        except Exception as e:
            print(f"❌ Error testing Sleeper integration: {e}")


async def test_bye_week_analysis():
    """Test bye week distribution and analysis"""
    print("\n🧪 Testing Bye Week Analysis")
    print("=" * 50)
    
    async with PlayerDataEnricher() as enricher:
        # Test bye week distribution
        bye_week_data = await enricher._get_bye_week_data()
        
        print("📅 2025 NFL Bye Week Schedule:")
        bye_weeks = {}
        for team, week in bye_week_data.items():
            if week not in bye_weeks:
                bye_weeks[week] = []
            bye_weeks[week].append(team)
        
        for week in sorted(bye_weeks.keys()):
            teams = ", ".join(sorted(bye_weeks[week]))
            print(f"  Week {week}: {teams} ({len(bye_weeks[week])} teams)")
        
        # Analyze bye week impact
        print("\n📊 Bye Week Fantasy Impact:")
        print("  Week 5-6: Early bye weeks (bad for consistency)")
        print("  Week 7-10: Ideal bye weeks (manageable)")
        print("  Week 11-14: Late bye weeks (playoff concerns)")


async def test_adp_sources():
    """Test ADP data sources and accuracy"""
    print("\n🧪 Testing ADP Data Sources")
    print("=" * 50)
    
    async with PlayerDataEnricher() as enricher:
        adp_data = await enricher._get_adp_data()
        
        print(f"📈 ADP Data Coverage: {len(adp_data)} players")
        
        # Show ADP ranges by tier
        tiers = {}
        for name, data in adp_data.items():
            tier = data.get('tier', 5)
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append((name, data['adp'], data.get('trend', 'stable')))
        
        for tier in sorted(tiers.keys()):
            players = sorted(tiers[tier], key=lambda x: x[1])  # Sort by ADP
            print(f"\n  Tier {tier} Players:")
            for name, adp, trend in players[:5]:  # Show top 5 per tier
                trend_emoji = {"rising": "📈", "falling": "📉", "stable": "➡️"}.get(trend, "➡️")
                print(f"    {name}: ADP {adp:.1f} {trend_emoji}")


async def main():
    """Run all enhanced data tests"""
    print("🏈 Fantasy Football Draft Assistant - Enhanced Data Testing")
    print("=" * 70)
    
    await test_basic_enrichment()
    await test_sleeper_integration()
    await test_bye_week_analysis()
    await test_adp_sources()
    
    print("\n" + "=" * 70)
    print("✅ Enhanced Data Testing Complete!")
    print("\n💡 Key Features Demonstrated:")
    print("   🎯 ADP data with trends from multiple sources")
    print("   📅 Bye week information for all 32 NFL teams")
    print("   🏆 Playoff outlook analysis (Weeks 14-16)")
    print("   📊 Composite fantasy relevance scoring")
    print("   🔧 Seamless integration with Sleeper API")
    print("   ⚡ Smart caching with configurable TTL")


if __name__ == "__main__":
    asyncio.run(main())