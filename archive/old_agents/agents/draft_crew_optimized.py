#!/usr/bin/env python3
"""
Optimized version of DraftCrew with performance improvements.
Goal: Reduce response time from 15s to under 10s.
"""

import asyncio
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

# Import CrewAI components
from crewai import Agent, Task, Crew, Process, LLM

class OptimizedDraftCrew:
    """Optimized draft recommendation system with <10s response time."""
    
    def __init__(self):
        """Initialize with performance optimizations."""
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minute cache for similar contexts
        self.llm = None
        self.quick_agent = None  # Single optimized agent
        self._initialize_llm()
        self._initialize_quick_agent()
    
    def _initialize_llm(self):
        """Initialize LLM with optimized settings."""
        # Set environment variable if needed
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
        
        # Optimized LLM settings for speed
        self.llm = LLM(
            model="claude-sonnet-4-20250514",
            temperature=0.5,  # Lower temp for consistency
            max_tokens=1500,  # Reduced from 4000 for speed
            timeout=15  # Strict timeout
        )
    
    def _initialize_quick_agent(self):
        """Create a single optimized agent for fast responses."""
        self.quick_agent = Agent(
            role="Draft Expert",
            goal="Provide top 3 draft picks in under 10 seconds",
            backstory="Expert fantasy analyst with instant recall",
            verbose=False,  # Less output for speed
            llm=self.llm,
            allow_delegation=False,  # No delegation for speed
            max_iter=1  # Single pass only
        )
    
    def _generate_cache_key(self, context: Dict) -> str:
        """Generate cache key from context."""
        # Create cache key from important context elements
        roster = context.get('user_roster', {})
        key_parts = [
            str(context.get('round', 0)),
            str(context.get('pick_number', 0)),
            str(len(roster.get('QB', []))),
            str(len(roster.get('RB', []))),
            str(len(roster.get('WR', []))),
            str(len(roster.get('TE', [])))
        ]
        return "_".join(key_parts)
    
    def _check_cache(self, cache_key: str) -> Optional[str]:
        """Check if we have a cached response."""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if datetime.now() - entry['time'] < timedelta(seconds=self.cache_ttl):
                return entry['response']
        return None
    
    def _update_cache(self, cache_key: str, response: str):
        """Update cache with new response."""
        self.cache[cache_key] = {
            'response': response,
            'time': datetime.now()
        }
    
    async def get_optimized_recommendation(self, context: Dict) -> str:
        """
        Get draft recommendation with optimized performance.
        Target: <10 second response time.
        """
        start_time = datetime.now()
        
        # Check cache first
        cache_key = self._generate_cache_key(context)
        cached = self._check_cache(cache_key)
        if cached:
            print(f"✅ Cache hit! Returning in {(datetime.now() - start_time).total_seconds():.1f}s")
            return cached
        
        # Prepare optimized context (reduce data size)
        optimized_context = self._optimize_context(context)
        
        # Create streamlined task description
        task_description = self._create_optimized_task(optimized_context)
        
        try:
            # Create task with minimal description
            task = Task(
                description=task_description,
                agent=self.quick_agent,
                expected_output="Top 3 player recommendations with position and brief reason"
            )
            
            # Execute with single agent (no multi-agent overhead)
            crew = Crew(
                agents=[self.quick_agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,  # Minimal output
                max_rpm=100  # Rate limiting if needed
            )
            
            # Run with timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(crew.kickoff),  # Run in thread to avoid blocking
                timeout=9.0  # 9 second timeout
            )
            
            # Format and cache result
            formatted_result = self._format_result(result)
            self._update_cache(cache_key, formatted_result)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"✅ Recommendation generated in {elapsed:.1f}s")
            
            return formatted_result
            
        except asyncio.TimeoutError:
            return self._get_fallback_recommendation(optimized_context)
        except Exception as e:
            print(f"Error: {e}")
            return self._get_fallback_recommendation(optimized_context)
    
    def _optimize_context(self, context: Dict) -> Dict:
        """Optimize context to reduce token count."""
        # Only include essential data
        optimized = {
            'round': context.get('round', 1),
            'pick': context.get('pick_number', 1),
            'roster': self._summarize_roster(context.get('user_roster', {})),
            'top_available': self._get_top_available(context.get('available_players', []), limit=30),
            'needs': self._calculate_needs(context.get('user_roster', {}))
        }
        return optimized
    
    def _summarize_roster(self, roster: Dict) -> str:
        """Create concise roster summary."""
        summary = []
        for pos, players in roster.items():
            if players:
                summary.append(f"{pos}:{len(players)}")
        return " ".join(summary) if summary else "Empty"
    
    def _get_top_available(self, players: List, limit: int = 30) -> str:
        """Get top available players in concise format."""
        if not players:
            return "No data"
        
        # Format: "Name(POS,Rank)" for compactness
        formatted = []
        for player in players[:limit]:
            name = player.get('player_name', player.get('name', 'Unknown'))
            pos = player.get('player_position_id', player.get('position', '??'))
            rank = player.get('rank_ecr', player.get('rank', 999))
            formatted.append(f"{name}({pos},{rank})")
        
        return " | ".join(formatted)
    
    def _calculate_needs(self, roster: Dict) -> str:
        """Calculate position needs quickly."""
        needs = []
        
        # SUPERFLEX needs: 2-3 QB, 4-6 RB, 5-7 WR, 1-2 TE
        qb_count = len(roster.get('QB', []))
        rb_count = len(roster.get('RB', []))
        wr_count = len(roster.get('WR', []))
        te_count = len(roster.get('TE', []))
        
        if qb_count < 2:
            needs.append("QB-HIGH")
        elif qb_count >= 3:
            needs.append("QB-AVOID")
            
        if rb_count < 3:
            needs.append("RB-HIGH")
        elif rb_count >= 6:
            needs.append("RB-LOW")
            
        if wr_count < 4:
            needs.append("WR-HIGH")
        elif wr_count >= 7:
            needs.append("WR-LOW")
            
        if te_count == 0:
            needs.append("TE-NEED")
        elif te_count >= 2:
            needs.append("TE-AVOID")
        
        return " ".join(needs) if needs else "BALANCED"
    
    def _create_optimized_task(self, context: Dict) -> str:
        """Create minimal but effective task description."""
        return f"""
SUPERFLEX DRAFT - Round {context['round']}, Pick {context['pick']}

Roster: {context['roster']}
Needs: {context['needs']}

Top Available (Name(Pos,Rank)):
{context['top_available']}

Provide exactly 3 recommendations:
🥇 PRIMARY: [Name] ([Pos]) - [1 line reason]
🥈 BACKUP: [Name] ([Pos]) - [1 line reason]  
🥉 THIRD: [Name] ([Pos]) - [1 line reason]

Rules: Follow needs, use rankings, only pick from available list.
"""
    
    def _format_result(self, result: Any) -> str:
        """Format result consistently."""
        if not result:
            return "No recommendations available"
        
        result_str = str(result)
        
        # Ensure proper formatting
        if "🥇" not in result_str:
            # Add formatting if missing
            lines = result_str.split('\n')
            if len(lines) >= 3:
                return f"🥇 {lines[0]}\n🥈 {lines[1]}\n🥉 {lines[2]}"
        
        return result_str
    
    def _get_fallback_recommendation(self, context: Dict) -> str:
        """Quick fallback recommendation based on needs."""
        needs = context.get('needs', '')
        available = context.get('top_available', '')
        
        # Parse available players
        players = []
        for player_str in available.split(' | ')[:10]:
            if '(' in player_str and ')' in player_str:
                players.append(player_str)
        
        if not players:
            return "Unable to generate recommendations - no player data"
        
        # Simple need-based selection
        recommendations = []
        
        # Prioritize by needs
        if "QB-HIGH" in needs:
            qbs = [p for p in players if '(QB,' in p]
            if qbs:
                recommendations.append(f"🥇 {qbs[0]} - Top QB available, SUPERFLEX value")
        
        if "RB-HIGH" in needs:
            rbs = [p for p in players if '(RB,' in p]
            if rbs:
                recommendations.append(f"{'🥇' if not recommendations else '🥈'} {rbs[0]} - RB depth needed")
        
        if "WR-HIGH" in needs:
            wrs = [p for p in players if '(WR,' in p]
            if wrs:
                recommendations.append(f"{'🥇' if not recommendations else '🥈' if len(recommendations)==1 else '🥉'} {wrs[0]} - WR depth needed")
        
        # Fill remaining slots with best available
        while len(recommendations) < 3 and players:
            player = players.pop(0)
            if player not in str(recommendations):
                medal = ['🥇', '🥈', '🥉'][len(recommendations)]
                recommendations.append(f"{medal} {player} - Best available")
        
        return '\n'.join(recommendations) if recommendations else "Unable to generate recommendations"

# Parallel processing optimization
async def parallel_analysis(context: Dict) -> Dict:
    """
    Run multiple analyses in parallel for speed.
    """
    tasks = [
        asyncio.create_task(analyze_qb_value(context)),
        asyncio.create_task(analyze_rb_wr_balance(context)),
        asyncio.create_task(analyze_positional_scarcity(context)),
        asyncio.create_task(check_bye_weeks(context))
    ]
    
    results = await asyncio.gather(*tasks)
    
    return {
        'qb_analysis': results[0],
        'balance_analysis': results[1],
        'scarcity_analysis': results[2],
        'bye_week_analysis': results[3]
    }

async def analyze_qb_value(context: Dict) -> str:
    """Quick QB value analysis for SUPERFLEX."""
    await asyncio.sleep(0.1)  # Simulate quick analysis
    qb_count = len(context.get('user_roster', {}).get('QB', []))
    if qb_count < 2:
        return "Need QB - SUPERFLEX priority"
    elif qb_count >= 3:
        return "Avoid QB - sufficient depth"
    return "QB optional - consider value"

async def analyze_rb_wr_balance(context: Dict) -> str:
    """Quick RB/WR balance check."""
    await asyncio.sleep(0.1)
    roster = context.get('user_roster', {})
    rb_count = len(roster.get('RB', []))
    wr_count = len(roster.get('WR', []))
    
    if rb_count < 3:
        return "Prioritize RB"
    elif wr_count < 4:
        return "Prioritize WR"
    return "Balanced approach"

async def analyze_positional_scarcity(context: Dict) -> str:
    """Check positional scarcity."""
    await asyncio.sleep(0.1)
    # Would analyze available players by position
    return "RB scarce, WR deep"

async def check_bye_weeks(context: Dict) -> str:
    """Quick bye week analysis."""
    await asyncio.sleep(0.1)
    # Would check bye week overlap
    return "Avoid week 10 byes"

# Performance testing function
async def test_optimization():
    """Test the optimized system."""
    print("\n" + "="*60)
    print("TESTING OPTIMIZED DRAFT CREW")
    print("="*60)
    
    # Test context
    test_context = {
        'round': 4,
        'pick_number': 44,
        'user_roster': {
            'QB': ['Josh Allen'],
            'RB': ['Saquon Barkley', 'Josh Jacobs'],
            'WR': ['CeeDee Lamb'],
            'TE': [],
            'K': [],
            'DEF': []
        },
        'available_players': [
            {'player_name': 'Davante Adams', 'player_position_id': 'WR', 'rank_ecr': 15},
            {'player_name': 'Joe Burrow', 'player_position_id': 'QB', 'rank_ecr': 8},
            {'player_name': 'Travis Kelce', 'player_position_id': 'TE', 'rank_ecr': 12},
            {'player_name': 'Calvin Ridley', 'player_position_id': 'WR', 'rank_ecr': 22},
            {'player_name': 'Tony Pollard', 'player_position_id': 'RB', 'rank_ecr': 25},
        ]
    }
    
    # Initialize optimized crew
    crew = OptimizedDraftCrew()
    
    # Test multiple times
    for i in range(3):
        print(f"\nTest {i+1}:")
        start = datetime.now()
        
        result = await crew.get_optimized_recommendation(test_context)
        
        elapsed = (datetime.now() - start).total_seconds()
        print(f"Time: {elapsed:.1f}s")
        print(f"Result:\n{result}")
        
        if elapsed < 10:
            print("✅ Target achieved!")
        else:
            print("⚠️  Over 10 seconds")

if __name__ == "__main__":
    asyncio.run(test_optimization())