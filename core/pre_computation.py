"""
Fantasy Football Draft Assistant - Pre-computation Engine
Analyzes draft scenarios when user is 3 picks away from their turn
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from agents.draft_crew import FantasyDraftCrew
from api.sleeper_client import SleeperClient
from core.league_context import league_manager


class PreComputationEngine:
    """
    Pre-computation engine that starts analyzing draft scenarios when the user
    is 3 picks away from their turn, ensuring instant recommendations when needed.
    
    Key Features:
    - Turn prediction based on draft order and snake draft logic
    - Scenario analysis for available players at user's turn
    - AI recommendation caching for instant delivery
    - Smart invalidation when picks change the landscape
    """
    
    def __init__(self, username: str, league_id: str, anthropic_api_key: str):
        self.username = username
        self.league_id = league_id
        self.anthropic_api_key = anthropic_api_key
        
        # Cache directory
        self.cache_dir = Path(__file__).parent.parent / "data"
        self.cache_dir.mkdir(exist_ok=True)
        self.precomp_cache_file = self.cache_dir / "precomputation_cache.json"
        
        # Draft state tracking
        self.user_roster_id: Optional[int] = None
        self.draft_order: List[int] = []  # List of roster IDs in draft order
        self.total_rounds: int = 0
        self.picks_per_round: int = 0
        
        # Pre-computation cache
        self.cached_recommendations: Dict[str, Any] = {}
        self.cache_timestamp: Optional[float] = None
        self.cache_ttl: int = 300  # 5 minutes TTL for cached recommendations
        
        # Clients
        self.sleeper_client: Optional[SleeperClient] = None
        self.ai_crew: Optional[FantasyDraftCrew] = None
        
        # Performance tracking
        self.precomp_started: Optional[float] = None
        self.precomp_completed: Optional[float] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.sleeper_client = SleeperClient(self.username, self.league_id)
        await self.sleeper_client.__aenter__()
        
        self.ai_crew = FantasyDraftCrew(anthropic_api_key=self.anthropic_api_key)
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.sleeper_client:
            await self.sleeper_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def initialize_draft_context(self) -> bool:
        """
        Initialize draft context including user roster ID and draft order
        
        Returns:
            bool: True if successfully initialized
        """
        try:
            print("🔄 Initializing pre-computation engine...")
            
            # Get league info
            league_info = await self.sleeper_client.get_league_info()
            draft_id = league_info.get('draft_id')
            
            if not draft_id:
                print("❌ No draft found for league")
                return False
            
            # Get draft info for order and settings
            draft_info = await self.sleeper_client.get_draft_info(draft_id)
            self.draft_order = draft_info.get('draft_order', [])
            
            # Get league rosters to find user's roster ID
            rosters = await self.sleeper_client.get_league_rosters()
            user_info = await self.sleeper_client.get_user()
            user_id = user_info.get('user_id')
            
            # Find user's roster ID
            for roster in rosters:
                if roster.get('owner_id') == user_id:
                    self.user_roster_id = roster.get('roster_id')
                    break
            
            if not self.user_roster_id:
                print("❌ Could not find user's roster ID")
                return False
            
            # Calculate draft parameters
            self.picks_per_round = len(self.draft_order)
            self.total_rounds = league_info.get('settings', {}).get('draft_rounds', 15)
            
            print(f"✅ Pre-computation engine initialized:")
            print(f"   User Roster ID: {self.user_roster_id}")
            print(f"   Draft Order: {len(self.draft_order)} teams")
            print(f"   Total Rounds: {self.total_rounds}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize pre-computation engine: {e}")
            return False
    
    def calculate_picks_until_user_turn(self, current_pick: int) -> int:
        """
        Calculate how many picks until it's the user's turn
        
        Args:
            current_pick: Current pick number (1-based)
            
        Returns:
            int: Number of picks until user's turn, -1 if error
        """
        try:
            if not self.user_roster_id or not self.draft_order:
                return -1
            
            # Find user's position in draft order (0-based)
            try:
                user_position = self.draft_order.index(self.user_roster_id)
            except ValueError:
                return -1
            
            # Calculate current round and pick within round (0-based)
            current_round = (current_pick - 1) // self.picks_per_round
            pick_in_round = (current_pick - 1) % self.picks_per_round
            
            # Snake draft logic - odd rounds (0, 2, 4...) go forward, even rounds (1, 3, 5...) go backward
            if current_round % 2 == 0:  # Forward round
                user_pick_in_round = user_position
            else:  # Reverse round
                user_pick_in_round = self.picks_per_round - 1 - user_position
            
            # Calculate user's next pick number
            if pick_in_round < user_pick_in_round:
                # User picks later this round
                picks_until_turn = user_pick_in_round - pick_in_round
            else:
                # User picks next round
                picks_left_this_round = self.picks_per_round - pick_in_round - 1
                
                # Next round pick position
                next_round = current_round + 1
                if next_round >= self.total_rounds:
                    return -1  # Draft is over
                
                if next_round % 2 == 0:  # Forward round
                    next_round_user_position = user_position
                else:  # Reverse round
                    next_round_user_position = self.picks_per_round - 1 - user_position
                
                picks_until_turn = picks_left_this_round + 1 + next_round_user_position
            
            return picks_until_turn
            
        except Exception as e:
            print(f"❌ Error calculating picks until user turn: {e}")
            return -1
    
    async def should_start_precomputation(self, current_pick: int) -> bool:
        """
        Check if we should start pre-computation based on current draft state
        
        Args:
            current_pick: Current pick number
            
        Returns:
            bool: True if we should start pre-computation
        """
        picks_until_turn = self.calculate_picks_until_user_turn(current_pick)
        
        # Start pre-computation when 3 picks away
        if picks_until_turn == 3:
            print(f"🎯 Pre-computation trigger: {picks_until_turn} picks until user turn")
            return True
        
        return False
    
    async def run_precomputation(self, current_pick: int) -> Dict[str, Any]:
        """
        Run pre-computation analysis for the user's upcoming pick
        
        Args:
            current_pick: Current pick number
            
        Returns:
            Dict containing cached recommendations and analysis
        """
        try:
            self.precomp_started = time.time()
            print("🚀 Starting pre-computation analysis...")
            
            # Get current draft state
            draft_id = await self.sleeper_client.find_draft_id_for_league()
            if not draft_id:
                return {"error": "No draft found"}
            
            # Get available players with enhanced data
            available_players = await self.sleeper_client.get_available_players(
                draft_id, None, enhanced=True
            )
            
            if not available_players:
                return {"error": "No available players found"}
            
            # Analyze top candidates by position
            analysis_results = {}
            
            # Get top players by position for quick recommendations
            positions = ['QB', 'RB', 'WR', 'TE']
            for position in positions:
                position_players = [p for p in available_players if position in p.get('positions', [])]
                top_players = position_players[:5]  # Top 5 per position
                
                if top_players:
                    analysis_results[position] = {
                        'top_players': top_players,
                        'count_available': len(position_players)
                    }
            
            # Generate AI recommendations for top overall players
            top_overall = available_players[:10]
            ai_question = f"""I'm about to pick at position {current_pick + 3}. 
            Here are the top 10 available players: {[p['name'] for p in top_overall]}.
            Give me your top 3 recommendations with brief reasoning for each."""
            
            try:
                ai_recommendations = await self.ai_crew.analyze_draft_question(ai_question)
            except Exception as e:
                print(f"⚠️ AI analysis failed: {e}")
                ai_recommendations = "AI analysis unavailable - use positional rankings"
            
            # Cache the results
            cache_data = {
                'timestamp': time.time(),
                'current_pick': current_pick,
                'picks_until_turn': 3,
                'available_count': len(available_players),
                'position_analysis': analysis_results,
                'ai_recommendations': ai_recommendations,
                'top_overall': top_overall[:5]  # Cache top 5 overall
            }
            
            self.cached_recommendations = cache_data
            self.cache_timestamp = time.time()
            
            # Save to disk
            with open(self.precomp_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
            
            self.precomp_completed = time.time()
            duration = self.precomp_completed - self.precomp_started
            
            print(f"✅ Pre-computation completed in {duration:.1f} seconds")
            print(f"   Available players: {len(available_players)}")
            print(f"   Top recommendations cached for instant delivery")
            
            return cache_data
            
        except Exception as e:
            print(f"❌ Pre-computation failed: {e}")
            return {"error": str(e)}
    
    def get_cached_recommendations(self) -> Optional[Dict[str, Any]]:
        """
        Get cached recommendations if they're still valid
        
        Returns:
            Dict with cached recommendations or None if invalid/expired
        """
        if not self.cached_recommendations or not self.cache_timestamp:
            return None
        
        # Check if cache is still valid (5 minutes)
        if time.time() - self.cache_timestamp > self.cache_ttl:
            print("📅 Cached recommendations expired")
            return None
        
        return self.cached_recommendations
    
    def invalidate_cache(self, reason: str = "Draft state changed"):
        """
        Invalidate cached recommendations when draft state changes
        
        Args:
            reason: Reason for invalidation
        """
        if self.cached_recommendations:
            print(f"🗑️ Invalidating pre-computation cache: {reason}")
            self.cached_recommendations = {}
            self.cache_timestamp = None
    
    def format_quick_recommendations(self, cache_data: Dict[str, Any]) -> str:
        """
        Format cached recommendations for quick display
        
        Args:
            cache_data: Cached recommendation data
            
        Returns:
            Formatted string for display
        """
        if 'error' in cache_data:
            return f"❌ Error: {cache_data['error']}"
        
        output = []
        output.append("🎯 **Pre-computed Recommendations** (instant delivery)")
        output.append(f"Available players: {cache_data.get('available_count', 0)}")
        output.append("")
        
        # Show top overall players
        top_overall = cache_data.get('top_overall', [])
        if top_overall:
            output.append("**Top Overall Available:**")
            for i, player in enumerate(top_overall, 1):
                adp = f"ADP {player.get('adp', 'N/A'):.0f}" if player.get('adp') else ""
                bye = f"Bye {player.get('bye_week', 'N/A')}"
                output.append(f"{i}. {player['name']} ({'/'.join(player.get('positions', []))}) - {adp}, {bye}")
            output.append("")
        
        # Show AI recommendations if available
        ai_recs = cache_data.get('ai_recommendations', '')
        if ai_recs and not ai_recs.startswith('AI analysis unavailable'):
            output.append("**AI Analysis:**")
            output.append(ai_recs[:300] + "..." if len(ai_recs) > 300 else ai_recs)
        
        return "\n".join(output)


# Test function
async def test_precomputation():
    """Test the pre-computation engine"""
    from dotenv import load_dotenv
    import os
    
    load_dotenv('.env.local')
    
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not all([username, league_id, api_key]):
        print("❌ Missing environment variables")
        return
    
    async with PreComputationEngine(username, league_id, api_key) as engine:
        # Initialize
        success = await engine.initialize_draft_context()
        if not success:
            print("❌ Failed to initialize")
            return
        
        # Test pick calculation
        test_picks = [1, 12, 25, 36, 50]
        for pick in test_picks:
            picks_until = engine.calculate_picks_until_user_turn(pick)
            should_precomp = await engine.should_start_precomputation(pick)
            print(f"Pick {pick}: {picks_until} picks until user turn, precompute: {should_precomp}")
        
        # Test pre-computation
        if any(engine.calculate_picks_until_user_turn(p) == 3 for p in test_picks):
            cache_data = await engine.run_precomputation(20)  # Simulate pick 20
            
            if cache_data:
                formatted = engine.format_quick_recommendations(cache_data)
                print("\n" + formatted)


if __name__ == "__main__":
    asyncio.run(test_precomputation())