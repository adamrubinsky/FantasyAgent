"""
Sleeper Auction Draft Crew - CrewAI Implementation
Optimized for real-time bidding decisions with <3s response time

League 3 Settings:
- 12-team auction draft
- $200 budget
- Half-PPR scoring
- No kicker position
- W/R/T Flex spot
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pathlib import Path

# Load environment variables from .env.local
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent.parent / '.env.local'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Try standard .env

from crewai import Agent, Task, Crew, Process
from langchain_anthropic import ChatAnthropic

# Import data providers
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from core.official_fantasypros import OfficialFantasyProsMCP

logger = logging.getLogger(__name__)

# League 3 specific constants
LEAGUE_SETTINGS = {
    "scoring": "HALF_PPR",
    "teams": 12,
    "budget": 200,
    "roster": {
        "QB": 1,
        "RB": 2,
        "WR": 2,
        "TE": 1,
        "FLEX": 1,  # W/R/T
        "DEF": 1,
        "BENCH": 5,
        "IR": 1
        # No Kicker!
    },
    "strategy": "STARS_AND_SCRUBS"
}

# Position priorities for auction
POSITION_TIERS = {
    "ELITE": ["RB1", "WR1"],  # Worth $40-60
    "PREMIUM": ["RB2", "WR2", "TE1"],  # Worth $20-35
    "VALUE": ["QB1", "RB3", "WR3"],  # Worth $10-20
    "DEPTH": ["RB4", "WR4", "TE2"],  # Worth $5-10
    "SCRUBS": ["QB2", "DEF", "BENCH"]  # Worth $1-3
}


class SleeperAuctionCrew:
    """
    CrewAI implementation for Sleeper auction drafts
    Focused on speed, reliability, and context awareness
    """
    
    def __init__(self, anthropic_api_key: str = None):
        self.api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        
        # Initialize LLMs - Haiku for speed, Sonnet for final decision
        self.llm_fast = ChatAnthropic(
            model="claude-3-haiku-20240307",
            temperature=0,
            max_tokens=300,  # Reduced for speed
            anthropic_api_key=self.api_key
        )
        
        self.llm_smart = ChatAnthropic(
            model="claude-sonnet-4-20250514",  # Claude Sonnet 4
            temperature=0,
            max_tokens=500,  # Reduced for speed
            anthropic_api_key=self.api_key
        )
        
        # Initialize data providers
        from .auction_data_provider import SleeperAuctionDataProvider
        from .auction_value_calculator import AuctionValueCalculator, LeagueSettings
        from .auction_cache import get_auction_cache
        
        self.data_provider = SleeperAuctionDataProvider()
        self.value_calculator = AuctionValueCalculator(LeagueSettings())
        self.auction_cache = get_auction_cache()  # High-performance cache
        
        # Cache for rankings and values
        self.cache = {
            "rankings": None,
            "auction_values": {},  # FantasyPros auction values
            "adjusted_values": {},  # Our adjusted values
            "last_update": None,
            "analysis_cache": {}  # Cache recent player analyses
        }
        
        # Performance tracking
        self.perf_stats = {
            "quick_passes": 0,
            "full_analyses": 0,
            "cache_hits": 0,
            "avg_response_ms": 0
        }
        
        # Initialize the crew with memory
        self._setup_crew()
    
    def _setup_crew(self):
        """Set up the CrewAI agents for auction draft"""
        
        # Agent 1: Budget Analyst
        self.budget_analyst = Agent(
            role='Auction Budget Analyst',
            goal='Track spending patterns and identify market inefficiencies',
            backstory="""You are an expert at auction dynamics, tracking how teams spend
            their budgets and identifying when players are going over or under value.
            You understand market inflation and can predict spending patterns.""",
            verbose=False,
            allow_delegation=False,
            llm=self.llm_fast
        )
        
        # Agent 2: Value Calculator
        self.value_calculator = Agent(
            role='Player Value Expert',
            goal='Calculate real-time player values based on remaining budget and needs',
            backstory="""You specialize in Value-Based Drafting (VBD) and Points Above
            Replacement (PAR) calculations. You adjust values based on league settings,
            position scarcity, and market conditions.""",
            verbose=False,
            allow_delegation=False,
            llm=self.llm_fast
        )
        
        # Agent 3: Roster Analyzer
        self.roster_analyzer = Agent(
            role='Roster Construction Specialist',
            goal='Analyze roster needs for all teams and identify leverage opportunities',
            backstory="""You track what positions each team needs and identify when
            teams will be desperate for certain positions. You understand roster
            construction strategy and positional scarcity.""",
            verbose=False,
            allow_delegation=False,
            llm=self.llm_fast
        )
        
        # Agent 4: Bid Strategist (Final Decision)
        self.bid_strategist = Agent(
            role='Auction Bid Strategist',
            goal='Make final bid recommendations based on all factors',
            backstory="""You are the final decision maker who synthesizes all analysis
            into a clear bid/pass recommendation with a specific dollar amount.
            You balance aggression with budget discipline.""",
            verbose=False,
            allow_delegation=False,
            llm=self.llm_smart  # Use Sonnet for final synthesis
        )
    
    def _quick_pass_check(self, player: Dict, context: Dict) -> Optional[str]:
        """
        Fast rule-based check to quickly pass on obvious non-targets
        Returns reason to pass, or None if should consider
        """
        my_budget = context.get("my_budget", 200)
        my_roster = context.get("my_roster", {})
        current_bid = context.get("current_bid", 1)
        
        # Pass if bid exceeds remaining budget
        if current_bid > my_budget - 5:  # Keep $5 for emergencies
            return "Bid exceeds available budget"
        
        # Pass if we already have 2 QBs (only need 1 starter)
        qb_count = len(my_roster.get("QB", []))
        if player.get("position") == "QB" and qb_count >= 2:
            return "Already have sufficient QB depth"
        
        # Pass if DEF and bid > $3 (never pay for defense)
        if player.get("position") == "DEF" and current_bid > 3:
            return "Defense not worth more than $3"
        
        # Pass if it's a backup TE and bid > $5
        te_count = len(my_roster.get("TE", []))
        if player.get("position") == "TE" and te_count >= 1 and current_bid > 5:
            return "Backup TE not worth more than $5"
        
        # Check Stars & Scrubs strategy
        stars_count = context.get("stars_acquired", 0)
        if stars_count < 3:
            # Still acquiring stars - pass on mid-tier players
            if 15 < current_bid < 35:
                return "Mid-tier player conflicts with Stars & Scrubs strategy"
        
        return None  # Should consider this player
    
    async def _calculate_max_bid(self, player: Dict, context: Dict) -> int:
        """
        Calculate maximum bid for a player based on value and roster needs
        """
        my_budget = context.get("my_budget", 200)
        roster_spots_left = context.get("roster_spots_left", 16)
        
        # Never bid more than budget minus spots to fill
        absolute_max = my_budget - roster_spots_left + 1
        
        # Get player's projected value
        base_value = await self._get_player_value(player)
        
        # Adjust for position need
        position = player.get("position")
        my_roster = context.get("my_roster", {})
        position_count = len(my_roster.get(position, []))
        
        # Position need multipliers
        if position in ["RB", "WR"]:
            if position_count == 0:
                base_value *= 1.2  # Premium for first starter
            elif position_count == 1:
                base_value *= 1.1  # Still need second starter
            elif position_count >= 3:
                base_value *= 0.7  # Discount for depth
        
        # Market inflation adjustment
        inflation = context.get("market_inflation", 1.0)
        adjusted_value = base_value * inflation
        
        # Stars & Scrubs adjustment
        stars_count = context.get("stars_acquired", 0)
        if stars_count < 3 and player.get("tier") == "ELITE":
            adjusted_value *= 1.15  # Pay up for elite players
        elif stars_count >= 3:
            adjusted_value *= 0.8  # Be conservative after getting stars
        
        return min(int(adjusted_value), absolute_max)
    
    async def _get_player_value(self, player: Dict) -> int:
        """
        Get auction value for a player from FantasyPros
        Falls back to calculated value if not available
        """
        player_id = player.get("id") or player.get("player_id")
        
        # Check if we need to refresh cache
        if not self.cache.get("auction_values"):
            # Load FantasyPros data
            data = await self.data_provider.get_rankings_with_values("HALF")
            self.cache["rankings"] = data["rankings"]
            self.cache["auction_values"] = data["auction_values"]
        
        # First try to get FantasyPros auction value
        if player_id in self.cache["auction_values"]:
            base_value = self.cache["auction_values"][player_id]
        else:
            # Fall back to calculating from rank if no auction value
            rank = player.get("rank", 200)
            position = player.get("position", "FLEX")
            
            # Base values by rank tier (Half-PPR)
            if rank <= 10:
                base_value = 55 - (rank * 2)  # $55-35 range
            elif rank <= 30:
                base_value = 35 - ((rank - 10) * 1.5)  # $35-5 range
            elif rank <= 60:
                base_value = 15 - ((rank - 30) * 0.3)  # $15-6 range
            elif rank <= 100:
                base_value = 6 - ((rank - 60) * 0.1)  # $6-2 range
            else:
                base_value = 1
            
            # Position adjustments for Half-PPR if we're calculating
            if position == "RB" and rank <= 24:
                base_value *= 1.1  # RBs slightly more valuable in Half-PPR
            elif position == "WR" and rank <= 36:
                base_value *= 0.95  # WRs slightly less than Full-PPR
            elif position == "QB":
                base_value = min(base_value, 22)  # Cap QB value (4PT passing TDs)
            elif position == "TE" and rank > 5:
                base_value *= 0.8  # Only elite TEs worth paying for
            elif position == "DEF":
                base_value = min(base_value, 2)  # Never pay for defense
        
        return int(base_value)
    
    async def analyze_nomination(self, player: Dict, current_bid: int, context: Dict) -> Dict:
        """
        Main entry point for analyzing a player nomination
        Returns bid recommendation with reasoning
        """
        start_time = time.time()
        
        # Try auction cache first for instant response
        pass_reason = self.auction_cache.get_quick_decision(player, context)
        if pass_reason:
            self.perf_stats["quick_passes"] += 1
            return {
                "action": "PASS",
                "max_bid": 0,
                "reasoning": pass_reason,
                "response_time_ms": int((time.time() - start_time) * 1000)
            }
        
        # Quick pass check from rules (no LLM needed)
        pass_reason = self._quick_pass_check(player, context)
        if pass_reason:
            return {
                "action": "PASS",
                "max_bid": 0,
                "reasoning": pass_reason,
                "response_time_ms": int((time.time() - start_time) * 1000)
            }
        
        # Calculate maximum bid
        max_bid = await self._calculate_max_bid(player, context)
        
        # If current bid already exceeds our max, pass
        if current_bid >= max_bid:
            return {
                "action": "PASS",
                "max_bid": max_bid,
                "reasoning": f"Current bid (${current_bid}) exceeds our max value (${max_bid})",
                "response_time_ms": int((time.time() - start_time) * 1000)
            }
        
        # Full analysis for potential bid
        analysis = await self._run_crew_analysis(player, current_bid, max_bid, context)
        
        # Add response time
        analysis["response_time_ms"] = int((time.time() - start_time) * 1000)
        
        return analysis
    
    async def _run_crew_analysis(self, player: Dict, current_bid: int, max_bid: int, context: Dict) -> Dict:
        """
        Run optimized analysis using direct LLM calls for speed
        """
        # Check analysis cache first
        cache_key = f"{player.get('id')}_{current_bid}_{context.get('my_budget')}_{context.get('picks_complete')}"
        if cache_key in self.cache["analysis_cache"]:
            cached = self.cache["analysis_cache"][cache_key]
            # Use cached result if less than 30 seconds old
            if time.time() - cached["timestamp"] < 30:
                self.perf_stats["cache_hits"] += 1
                return cached["result"]
        
        # Create tasks - only last can be async in CrewAI
        budget_task = Task(
            description=f"""Market analysis for {player.get('name')}:
            Bid: ${current_bid}, My budget: ${context.get('my_budget')}
            Avg budget: ${context.get('avg_budget', 150)}
            Return: OVER/UNDER/FAIR and inflation rate (0.8-1.2)""",
            agent=self.budget_analyst,
            expected_output="OVER/UNDER/FAIR and inflation rate",
            async_execution=False  # Sequential for now
        )
        
        value_task = Task(
            description=f"""{player.get('name')} value:
            Position: {player.get('position')}, Rank: {player.get('rank')}
            Half-PPR, Current: ${current_bid}
            Return: Fair value $X and scarcity factor (0.8-1.5)""",
            agent=self.value_calculator,
            expected_output="Value $X, scarcity factor",
            async_execution=False  # Sequential for now
        )
        
        roster_task = Task(
            description=f"""Roster need for {player.get('position')}:
            Current: {len(context.get('my_roster', {}).get(player.get('position'), []))}
            Spots left: {context.get('roster_spots_left')}
            Return: CRITICAL/HIGH/MEDIUM/LOW need level""",
            agent=self.roster_analyzer,
            expected_output="CRITICAL/HIGH/MEDIUM/LOW need",
            async_execution=False  # Only last task can be async in CrewAI
        )
        
        # Create the crew (memory disabled for now - requires OpenAI API)
        crew = Crew(
            agents=[self.budget_analyst, self.value_calculator, self.roster_analyzer],
            tasks=[budget_task, value_task, roster_task],
            process=Process.sequential,  # Tasks run async with async_execution=True
            verbose=False,
            memory=False,  # Disabled - requires OpenAI API key
            cache=True,  # Enable caching
            max_rpm=100  # Rate limit for API calls
        )
        
        # Execute parallel analysis
        try:
            parallel_results = crew.kickoff()
        except Exception as e:
            logger.error(f"Crew analysis error: {e}")
            parallel_results = "Analysis failed, using fallback"
        
        # Final synthesis - ultra-concise for speed
        synthesis_task = Task(
            description=f"""{parallel_results}
            Player: {player.get('name')} ${current_bid} (max ${max_bid})
            Budget: ${context.get('my_budget')}, Stars: {context.get('stars_acquired', 0)}/3
            Reply: BID or PASS""",
            agent=self.bid_strategist,
            expected_output="BID or PASS with reason"
        )
        
        final_crew = Crew(
            agents=[self.bid_strategist],
            tasks=[synthesis_task],
            process=Process.sequential,
            verbose=False,
            memory=False,  # Disabled - requires OpenAI API key
            cache=True
        )
        
        try:
            final_result = final_crew.kickoff()
            
            # Parse the result into structured format
            if "PASS" in str(final_result).upper():
                result = {
                    "action": "PASS",
                    "max_bid": max_bid,
                    "reasoning": str(final_result)
                }
            else:
                # Extract bid recommendation
                recommended_bid = min(current_bid + 1, max_bid)
                
                result = {
                    "action": "BID",
                    "recommended_bid": recommended_bid,
                    "max_bid": max_bid,
                    "reasoning": str(final_result),
                    "confidence": "HIGH" if max_bid - current_bid > 10 else "MEDIUM"
                }
            
            # Cache the result
            self.cache["analysis_cache"][cache_key] = {
                "result": result,
                "timestamp": time.time()
            }
            
            # Clean old cache entries (keep last 20)
            if len(self.cache["analysis_cache"]) > 20:
                sorted_cache = sorted(
                    self.cache["analysis_cache"].items(),
                    key=lambda x: x[1]["timestamp"],
                    reverse=True
                )
                self.cache["analysis_cache"] = dict(sorted_cache[:20])
            
            self.perf_stats["full_analyses"] += 1
            return result
        except Exception as e:
            logger.error(f"Final synthesis error: {e}")
            return {
                "action": "PASS",
                "max_bid": max_bid,
                "reasoning": "Analysis error - defaulting to pass for safety"
            }
    
    async def get_nomination_suggestion(self, context: Dict) -> Dict:
        """
        Suggest a player to nominate when it's user's turn
        Strategy: Nominate players others will overpay for, or get your targets
        """
        my_budget = context.get("my_budget", 200)
        stars_acquired = context.get("stars_acquired", 0)
        market_inflation = context.get("market_inflation", 1.0)
        available_players = context.get("available_players", [])
        
        # Filter to top available players
        top_players = sorted(
            available_players,
            key=lambda p: p.get("rank", 999)
        )[:20]
        
        if market_inflation > 1.15 and stars_acquired >= 2:
            # Market is hot - nominate a trap player
            # Find a popular player who's overvalued
            for player in top_players:
                if player.get("position") in ["QB", "TE"] and player.get("rank") < 50:
                    return {
                        "player": player,
                        "strategy": "PRICE_ENFORCE",
                        "reasoning": f"Market is inflated ({market_inflation:.0%}). Nominate {player['name']} to make others overpay.",
                        "suggested_opening": 1  # Start at $1 to maximize bidding
                    }
        
        elif stars_acquired < 3:
            # Still need stars - nominate our target
            for player in top_players:
                if player.get("tier") == "ELITE" and player.get("position") in ["RB", "WR"]:
                    max_bid = await self._calculate_max_bid(player, context)
                    if max_bid > 35:  # Worth pursuing as a star
                        return {
                            "player": player,
                            "strategy": "ACQUIRE",
                            "reasoning": f"Need elite talent. Target {player['name']} up to ${max_bid}.",
                            "suggested_opening": max(1, max_bid - 20)  # Start reasonably
                        }
        
        else:
            # Need value/depth - nominate a mid-tier player others want
            for player in top_players:
                if 10 < player.get("rank", 0) < 40:
                    return {
                        "player": player,
                        "strategy": "PRICE_ENFORCE",
                        "reasoning": f"Let others fight over {player['name']} while we wait for value.",
                        "suggested_opening": 1
                    }
        
        # Default: nominate the highest ranked available
        if top_players:
            return {
                "player": top_players[0],
                "strategy": "DEFAULT",
                "reasoning": f"Nominate {top_players[0]['name']} to keep draft moving.",
                "suggested_opening": 1
            }
        
        return {
            "player": None,
            "strategy": "WAIT",
            "reasoning": "No clear nomination target"
        }
    
    async def analyze_draft_question(self, question: str, context: Dict) -> str:
        """
        Handle general Q&A about the auction draft
        """
        # This can reuse much of the logic from the snake draft crew
        # but with auction-specific context
        
        prompt = f"""You are an expert fantasy football auction draft assistant.
        
        League Settings:
        - Format: 12-team Auction Draft
        - Budget: $200
        - Scoring: Half-PPR
        - Roster: 1 QB, 2 RB, 2 WR, 1 TE, 1 W/R/T Flex, 1 DEF, 5 Bench
        - Strategy: Stars & Scrubs (spend 70% on 3-4 elite players)
        
        Current Context:
        - My Budget: ${context.get('my_budget', 200)}
        - My Roster: {json.dumps(context.get('my_roster', {}), indent=2)}
        - Average Budget: ${context.get('avg_budget', 150)}
        - Market Inflation: {context.get('market_inflation', 1.0):.0%}
        
        User Question: {question}
        
        Provide a concise, actionable answer focused on auction strategy."""
        
        try:
            response = self.llm_smart.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"Question analysis error: {e}")
            return "I'm having trouble analyzing that right now. Try asking about specific players or positions."
    
    def get_proactive_analysis(self, context: Dict) -> Dict:
        """
        Generate proactive insights for the draft
        """
        my_budget = context.get("my_budget", 200)
        avg_budget = context.get("avg_budget", 150)
        picks_complete = context.get("picks_complete", 0)
        total_picks = context.get("total_picks", 192)  # 12 teams * 16 slots
        
        # Calculate draft progress
        progress = picks_complete / total_picks if total_picks > 0 else 0
        
        # Budget analysis
        budget_advantage = my_budget - avg_budget
        
        insights = []
        
        # Budget position
        if budget_advantage > 20:
            insights.append(f"💰 Strong position with ${budget_advantage} above average")
        elif budget_advantage < -20:
            insights.append(f"⚠️ Budget constrained: ${abs(budget_advantage)} below average")
        
        # Draft phase
        if progress < 0.25:
            insights.append("🌟 Early phase: Focus on acquiring 1-2 elite players")
        elif progress < 0.5:
            insights.append("📊 Mid-draft: Balance stars with value targets")
        elif progress < 0.75:
            insights.append("🎯 Late-middle: Target undervalued depth players")
        else:
            insights.append("🏁 End game: Fill roster with $1-3 players")
        
        # Position targets
        roster = context.get("my_roster", {})
        if len(roster.get("RB", [])) < 2:
            insights.append("🏃 Need RB starters - prioritize next quality RB")
        if len(roster.get("WR", [])) < 2:
            insights.append("🎯 Need WR starters - target pass catchers")
        
        return {
            "title": "Auction Strategy Update",
            "insights": insights,
            "action": self._get_next_action(context)
        }
    
    def _get_next_action(self, context: Dict) -> str:
        """Get the next recommended action based on context"""
        stars = context.get("stars_acquired", 0)
        if stars < 2:
            return "Target elite RB/WR if available"
        elif stars < 3:
            return "One more star or pivot to value"
        else:
            return "Focus on value and depth"