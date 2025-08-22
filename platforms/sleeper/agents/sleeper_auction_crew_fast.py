"""
Optimized Sleeper Auction Crew with Parallel Execution
Target: <3 second response times
"""

import os
import time
import asyncio
from typing import Dict
import logging
from pathlib import Path

# Load environment variables from .env.local
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent.parent / '.env.local'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try standard .env if .env.local doesn't exist
    load_dotenv()

from crewai import Agent, Task, Crew, Process
from langchain_anthropic import ChatAnthropic

logger = logging.getLogger(__name__)

class SleeperAuctionCrewFast:
    """
    Optimized CrewAI implementation using parallel crews
    Maintains multi-agent architecture while achieving <3s response
    """
    
    def __init__(self, anthropic_api_key: str = None):
        self.api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        
        # Single shared LLM instance for all agents (Haiku for speed)
        self.llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            temperature=0,
            max_tokens=200,  # Keep responses concise
            anthropic_api_key=self.api_key
        )
        
        # Sonnet for final synthesis only
        self.llm_synth = ChatAnthropic(
            model="claude-sonnet-4-20250514",  # Claude Sonnet 4
            temperature=0,
            max_tokens=300,
            anthropic_api_key=self.api_key
        )
        
        # Initialize data providers
        try:
            from .auction_data_provider import SleeperAuctionDataProvider
            from .auction_value_calculator import AuctionValueCalculator, LeagueSettings
            from .auction_cache import get_auction_cache
        except ImportError:
            # For standalone testing
            import sys
            sys.path.append(str(Path(__file__).parent))
            from auction_data_provider import SleeperAuctionDataProvider
            from auction_value_calculator import AuctionValueCalculator, LeagueSettings
            from auction_cache import get_auction_cache
        
        self.data_provider = SleeperAuctionDataProvider()
        self.value_calculator = AuctionValueCalculator(LeagueSettings())
        self.auction_cache = get_auction_cache()
        
        # Performance tracking
        self.perf_stats = {
            "quick_passes": 0,
            "full_analyses": 0,
            "cache_hits": 0,
            "avg_response_ms": []
        }
        
        # Create agents once (reuse for all analyses)
        self._create_agents()
    
    def _create_agents(self):
        """Create reusable agents for parallel analysis"""
        
        # Agent 1: Market Analyst
        self.market_agent = Agent(
            role='Market Analyst',
            goal='Assess market conditions and inflation',
            backstory='Expert at tracking spending patterns.',
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )
        
        # Agent 2: Value Expert
        self.value_agent = Agent(
            role='Value Expert',
            goal='Calculate player worth',
            backstory='VBD and scarcity specialist.',
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )
        
        # Agent 3: Roster Builder
        self.roster_agent = Agent(
            role='Roster Builder',
            goal='Assess roster needs',
            backstory='Roster construction expert.',
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )
        
        # Agent 4: Decision Maker (uses Sonnet)
        self.decision_agent = Agent(
            role='Auction Strategist',
            goal='Make final bid decision',
            backstory='Final decision maker.',
            verbose=False,
            allow_delegation=False,
            llm=self.llm_synth
        )
    
    async def analyze_nomination(self, player: Dict, current_bid: int, context: Dict) -> Dict:
        """
        Main entry point - returns bid decision with max bid amount
        Target: <3 second response
        """
        start_time = time.time()
        
        # 1. Quick cache check
        cache_key = self.auction_cache.make_key(
            player.get("id", "unknown"),
            context
        )
        cached = self.auction_cache.get(cache_key, ttl=30)
        if cached:
            self.perf_stats["cache_hits"] += 1
            cached["response_time_ms"] = 0
            return cached
        
        # 2. Quick rule-based pass
        pass_reason = self.auction_cache.get_quick_decision(player, context)
        if pass_reason:
            self.perf_stats["quick_passes"] += 1
            result = {
                "action": "PASS",
                "max_bid": 0,
                "reasoning": pass_reason,
                "response_time_ms": int((time.time() - start_time) * 1000)
            }
            self.auction_cache.put(cache_key, result)
            return result
        
        # 3. Calculate max bid (this is fast - 3ms)
        max_bid = await self._calculate_max_bid(player, context)
        
        # 4. If current bid already exceeds max, instant pass
        if current_bid >= max_bid:
            result = {
                "action": "PASS",
                "max_bid": max_bid,
                "reasoning": f"Current bid ${current_bid} exceeds max value ${max_bid}",
                "response_time_ms": int((time.time() - start_time) * 1000)
            }
            self.auction_cache.put(cache_key, result)
            return result
        
        # 5. Run parallel analysis for complex decisions
        analysis = await self._run_parallel_analysis(player, current_bid, max_bid, context)
        
        # Add timing and cache
        analysis["response_time_ms"] = int((time.time() - start_time) * 1000)
        self.perf_stats["avg_response_ms"].append(analysis["response_time_ms"])
        self.perf_stats["full_analyses"] += 1
        
        self.auction_cache.put(cache_key, analysis, analysis["response_time_ms"])
        
        return analysis
    
    async def _calculate_max_bid(self, player: Dict, context: Dict) -> int:
        """Fast max bid calculation based on value and context"""
        # Get base value from FantasyPros or calculate
        player_id = player.get("id") or player.get("player_id")
        
        # Try cache first
        if not hasattr(self, "_value_cache"):
            self._value_cache = {}
        
        if player_id not in self._value_cache:
            # Load rankings if needed
            data = await self.data_provider.get_rankings_with_values("HALF")
            if data and "auction_values" in data:
                self._value_cache.update(data["auction_values"])
        
        base_value = self._value_cache.get(player_id, 20)
        
        # Adjust for context
        my_budget = context.get("my_budget", 200)
        roster_spots = context.get("roster_spots_left", 16)
        stars_acquired = context.get("stars_acquired", 0)
        
        # Never bid more than budget - spots + 1
        absolute_max = my_budget - roster_spots + 1
        
        # Adjust base value
        adjusted = base_value
        
        # Stars & Scrubs adjustments
        if stars_acquired < 3 and player.get("rank", 99) <= 10:
            adjusted *= 1.2  # Pay up for stars
        elif stars_acquired >= 3:
            adjusted *= 0.85  # Be conservative after stars
        
        # Position adjustments
        position = player.get("position")
        my_roster = context.get("my_roster", {})
        pos_count = len(my_roster.get(position, []))
        
        if position in ["RB", "WR"] and pos_count == 0:
            adjusted *= 1.15  # Need starters
        elif position == "QB" and pos_count > 0:
            adjusted *= 0.5  # Don't need backup QB
        elif position == "DEF":
            adjusted = min(adjusted, 2)  # Never pay for defense
        
        return min(int(adjusted), absolute_max)
    
    async def _run_parallel_analysis(self, player: Dict, current_bid: int, 
                                    max_bid: int, context: Dict) -> Dict:
        """
        Run 3 parallel crews for fast multi-agent analysis
        """
        # Create 3 parallel analysis crews
        
        # Crew 1: Market Analysis
        market_task = Task(
            description=f"""Bid ${current_bid} for {player['name']}
            My budget: ${context['my_budget']}, Avg: ${context.get('avg_budget', 150)}
            Is this OVER/UNDER/FAIR? (one word + rate 0.8-1.2)""",
            agent=self.market_agent,
            expected_output="OVER/UNDER/FAIR + rate"
        )
        market_crew = Crew(
            agents=[self.market_agent],
            tasks=[market_task],
            process=Process.sequential,
            verbose=False
        )
        
        # Crew 2: Value Analysis  
        value_task = Task(
            description=f"""{player['name']} {player.get('position')} rank {player.get('rank', 99)}
            Half-PPR, current ${current_bid}, max ${max_bid}
            Worth? (number only)""",
            agent=self.value_agent,
            expected_output="Dollar value"
        )
        value_crew = Crew(
            agents=[self.value_agent],
            tasks=[value_task],
            process=Process.sequential,
            verbose=False
        )
        
        # Crew 3: Roster Analysis
        roster_task = Task(
            description=f"""Need {player.get('position')}?
            Have: {len(context.get('my_roster', {}).get(player.get('position'), []))}
            Spots left: {context.get('roster_spots_left', 16)}
            CRITICAL/HIGH/MEDIUM/LOW?""",
            agent=self.roster_agent,
            expected_output="Need level"
        )
        roster_crew = Crew(
            agents=[self.roster_agent],
            tasks=[roster_task],
            process=Process.sequential,
            verbose=False
        )
        
        try:
            # Execute all 3 in parallel
            results = await asyncio.gather(
                market_crew.kickoff_async(),
                value_crew.kickoff_async(),
                roster_crew.kickoff_async(),
                return_exceptions=True
            )
            
            # Extract raw outputs
            market_result = results[0].raw if hasattr(results[0], 'raw') else str(results[0])
            value_result = results[1].raw if hasattr(results[1], 'raw') else str(results[1])
            roster_result = results[2].raw if hasattr(results[2], 'raw') else str(results[2])
            
        except Exception as e:
            logger.error(f"Parallel analysis error: {e}")
            market_result = "FAIR"
            value_result = str(max_bid)
            roster_result = "MEDIUM"
        
        # Final synthesis
        synthesis_task = Task(
            description=f"""Market: {market_result}, Value: {value_result}, Need: {roster_result}
            {player['name']} at ${current_bid} (max ${max_bid})
            Stars: {context.get('stars_acquired', 0)}/3, Budget: ${context['my_budget']}
            
            Decision? Format:
            ACTION: BID or PASS
            MAX_BID: $X
            REASON: (10 words max)""",
            agent=self.decision_agent,
            expected_output="ACTION, MAX_BID, REASON"
        )
        
        final_crew = Crew(
            agents=[self.decision_agent],
            tasks=[synthesis_task],
            process=Process.sequential,
            verbose=False
        )
        
        try:
            final_result = final_crew.kickoff()
            result_text = final_result.raw if hasattr(final_result, 'raw') else str(final_result)
            
            # Parse the structured response
            if "PASS" in result_text.upper():
                action = "PASS"
            else:
                action = "BID"
            
            # Extract max bid from response or use calculated
            import re
            bid_match = re.search(r'\$(\d+)', result_text)
            if bid_match:
                extracted_max = int(bid_match.group(1))
                final_max_bid = min(extracted_max, max_bid)
            else:
                final_max_bid = max_bid
            
            # Extract reasoning
            reason_match = re.search(r'REASON:\s*(.+)', result_text, re.IGNORECASE)
            if reason_match:
                reasoning = reason_match.group(1).strip()
            else:
                reasoning = result_text[:100]
            
            return {
                "action": action,
                "max_bid": final_max_bid,
                "recommended_bid": min(current_bid + 1, final_max_bid) if action == "BID" else 0,
                "reasoning": reasoning,
                "market_analysis": market_result,
                "value_analysis": value_result,
                "roster_need": roster_result
            }
            
        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            # Fallback decision
            if current_bid < max_bid * 0.75:
                return {
                    "action": "BID",
                    "max_bid": max_bid,
                    "recommended_bid": min(current_bid + 1, max_bid),
                    "reasoning": "Good value below 75% of max"
                }
            else:
                return {
                    "action": "PASS",
                    "max_bid": max_bid,
                    "recommended_bid": 0,
                    "reasoning": "Too close to maximum value"
                }
    
    def get_proactive_analysis(self, context: Dict) -> Dict:
        """
        Provide proactive auction insights for the UI
        Shows current nominations and max bid recommendations
        """
        my_budget = context.get("my_budget", 200)
        avg_budget = context.get("avg_budget", 150)
        picks_complete = context.get("picks_complete", 0)
        stars_acquired = context.get("stars_acquired", 0)
        my_roster = context.get("my_roster", {})
        
        # Calculate draft phase
        total_picks = 192  # 12 teams * 16 roster spots
        progress = picks_complete / total_picks if total_picks > 0 else 0
        
        # Determine strategy phase
        if stars_acquired < 3 and my_budget > 140:
            phase = "STARS"
            phase_advice = "🎯 Target elite RBs/WRs ($40-60)"
        elif my_budget > 60:
            phase = "VALUE"
            phase_advice = "💰 Find mid-tier values ($8-25)"
        else:
            phase = "SCRUBS"
            phase_advice = "🪙 Fill roster with $1-3 players"
        
        # Position needs
        needs = []
        if len(my_roster.get("QB", [])) == 0:
            needs.append("QB (max $15-20)")
        if len(my_roster.get("RB", [])) < 2:
            needs.append(f"RB ({2 - len(my_roster.get('RB', []))} needed)")
        if len(my_roster.get("WR", [])) < 2:
            needs.append(f"WR ({2 - len(my_roster.get('WR', []))} needed)")
        if len(my_roster.get("TE", [])) == 0:
            needs.append("TE (elite or wait)")
        
        # Budget management
        roster_spots_left = 16 - sum(len(players) for players in my_roster.values())
        min_reserve = roster_spots_left - 1  # Keep $1 per spot
        max_spend = my_budget - min_reserve
        
        insights = [
            f"**Phase:** {phase} - {phase_advice}",
            f"**Budget:** ${my_budget} (avg: ${avg_budget})",
            f"**Max spend:** ${max_spend} on next player",
            f"**Position needs:** {', '.join(needs) if needs else 'Balanced'}",
            f"**Draft progress:** {progress:.0%} complete"
        ]
        
        # Add specific recommendations
        if phase == "STARS" and stars_acquired < 3:
            insights.append("⚡ **Action:** Bid aggressively on top 10 RB/WR")
        elif phase == "VALUE":
            insights.append("📊 **Action:** Wait for value, nominate overpriced QBs/TEs")
        else:
            insights.append("✅ **Action:** Nominate expensive players, bid $1-2 only")
        
        return {
            "title": f"Auction Strategy - {phase} Phase",
            "insights": insights,
            "phase": phase,
            "maxSpend": max_spend,
            "budgetStatus": "healthy" if my_budget > avg_budget else "tight"
        }
    
    async def analyze_draft_question(self, question: str, context: Dict) -> str:
        """
        Handle general Q&A about the auction draft with REAL rankings data
        """
        # Always get real rankings data - no assumptions!
        rankings_context = ""
        try:
            # Get real rankings data
            logger.info("Fetching real rankings for Q&A response...")
            data = await self.data_provider.get_rankings_with_values("HALF")
            if data and "rankings" in data:
                logger.info(f"Got {len(data['rankings'])} players from rankings")
                
                # Get list of drafted player names to filter out
                drafted_names = context.get("drafted_player_names", [])
                logger.info(f"Filtering out {len(drafted_names)} drafted players")
                
                # Normalize names for better matching (handle Jr, Sr, III, etc.)
                def normalize_name(name):
                    """Normalize player names for comparison"""
                    if not name:
                        return ""
                    # Remove common suffixes and extra spaces
                    normalized = name.replace(" Jr.", "").replace(" Jr", "")
                    normalized = normalized.replace(" Sr.", "").replace(" Sr", "")
                    normalized = normalized.replace(" III", "").replace(" II", "")
                    normalized = normalized.replace(" IV", "").replace(" V", "")
                    return normalized.strip().lower()
                
                # Create normalized drafted names set for faster lookup
                normalized_drafted = {normalize_name(name) for name in drafted_names}
                
                # Filter out drafted players from rankings with normalized comparison
                available_players = [
                    p for p in data["rankings"] 
                    if normalize_name(p.get("name", "")) not in normalized_drafted
                ]
                logger.info(f"Found {len(available_players)} available players after filtering")
                
                # Calculate what we can actually afford
                my_budget = context.get('my_budget', 200)
                my_roster = context.get('my_roster', {})
                roster_spots_filled = sum(len(players) for players in my_roster.values())
                roster_spots_left = 16 - roster_spots_filled
                max_affordable = max(1, my_budget - roster_spots_left + 1)
                
                # Filter to only affordable players
                affordable_players = [
                    p for p in available_players 
                    if p.get("auction_value", 1) <= max_affordable
                ]
                
                # Get top available players by position (NOT drafted AND affordable)
                top_rbs = [p for p in affordable_players if p.get("position") == "RB"][:5]
                top_wrs = [p for p in affordable_players if p.get("position") == "WR"][:5]
                top_qbs = [p for p in affordable_players if p.get("position") == "QB"][:3]
                top_tes = [p for p in affordable_players if p.get("position") == "TE"][:3]
                
                # Check if late draft for different recommendations
                picks_complete = context.get('picks_complete', 0)
                is_late_draft = picks_complete > 135  # After pick 135 of 192
                
                if is_late_draft and max_affordable <= 3:
                    # In late draft with minimal budget - different strategy
                    rankings_context = f"""
ENDGAME SITUATION: Pick #{picks_complete}/192 with only ${my_budget} remaining.
Most teams also have $1-3 left. Expensive nominations won't help anymore.

STRATEGY: Nominate players YOU want for $1-2, not expensive decoys.

TOP $1-2 TARGETS (From available players):
RBs: {', '.join([f"{p['name']}" for p in top_rbs[:3]]) if top_rbs else 'Look for handcuffs'}
WRs: {', '.join([f"{p['name']}" for p in top_wrs[:3]]) if top_wrs else 'Look for rookies'}
QBs: {', '.join([f"{p['name']}" for p in top_qbs[:2]]) if top_qbs else 'Backup QBs'}
TEs: {', '.join([f"{p['name']}" for p in top_tes[:2]]) if top_tes else 'Streaming options'}

Nominate players you actually want to roster at $1-2. Everyone is budget-constrained now."""
                else:
                    rankings_context = f"""
BUDGET CONSTRAINT: You have ${my_budget} and need ${roster_spots_left - 1} for remaining spots.
Maximum you can spend on one player: ${max_affordable}

TOP AVAILABLE PLAYERS (Within Your Budget):
RBs: {', '.join([f"{p['name']} (${p.get('auction_value', 20)})" for p in top_rbs]) if top_rbs else 'None affordable'}
WRs: {', '.join([f"{p['name']} (${p.get('auction_value', 15)})" for p in top_wrs]) if top_wrs else 'None affordable'}
QBs: {', '.join([f"{p['name']} (${p.get('auction_value', 10)})" for p in top_qbs]) if top_qbs else 'None affordable'}
TEs: {', '.join([f"{p['name']} (${p.get('auction_value', 8)})" for p in top_tes]) if top_tes else 'None affordable'}

IMPORTANT: Only recommend players from the above list that fit within the ${max_affordable} budget constraint."""
            else:
                rankings_context = "ERROR: Unable to fetch current rankings. Cannot recommend specific players."
        except Exception as e:
            logger.error(f"Failed to get rankings for Q&A: {e}")
            rankings_context = "ERROR: Rankings unavailable. Cannot recommend specific players without data."
        
        # Determine if we're in late draft (endgame)
        picks_complete = context.get('picks_complete', 0)
        total_picks = 192  # 12 teams * 16 roster spots
        draft_progress = picks_complete / total_picks if total_picks > 0 else 0
        is_late_draft = draft_progress > 0.70  # After 70% of picks
        
        # Add late draft context
        late_draft_context = ""
        if is_late_draft:
            late_draft_context = f"""
LATE DRAFT CONTEXT (Pick #{picks_complete} of {total_picks}):
- Most teams are also budget-constrained with $1-5 remaining
- Expensive player nominations won't drain others' budgets significantly
- Focus on $1-2 values and filling roster needs
- Nominate players you actually want at $1-2, not expensive decoys
"""
        
        prompt = f"""You are an expert fantasy football auction draft assistant.
        
League: 12-team, $200 budget, Half-PPR, No kicker
Current Context:
- Budget: ${context.get('my_budget', 200)}
- Roster: {context.get('my_roster', [])}
- Stars acquired: {context.get('stars_acquired', 0)}/3
- Draft Progress: {draft_progress:.0%} complete (Pick #{picks_complete})
{late_draft_context}
{rankings_context}

Question: {question}

CRITICAL Instructions:
1. ONLY recommend players from the list above - they are filtered for budget and availability
2. NEVER recommend a player costing more than the max affordable amount shown
3. NEVER recommend players not in the list (they are already drafted)
4. Be realistic about budget constraints - with ${context.get('my_budget', 200)} you cannot get expensive players
5. In late draft (>70% complete), assume other teams also have limited budgets
6. Provide concise, actionable answer (2-3 sentences max)"""
        
        try:
            response = self.llm_synth.invoke(prompt)
            return response.content
        except Exception as e:
            return f"Focus on getting 3-4 elite players for 70% of budget. Check rankings data availability."
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        avg_ms = sum(self.perf_stats["avg_response_ms"]) / len(self.perf_stats["avg_response_ms"]) \
                 if self.perf_stats["avg_response_ms"] else 0
        
        return {
            "quick_passes": self.perf_stats["quick_passes"],
            "full_analyses": self.perf_stats["full_analyses"],
            "cache_hits": self.perf_stats["cache_hits"],
            "avg_response_ms": avg_ms,
            "cache_stats": self.auction_cache.get_stats()
        }


# Quick test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        crew = SleeperAuctionCrewFast()
        
        player = {
            "id": "test1",
            "name": "Christian McCaffrey",
            "position": "RB",
            "rank": 1
        }
        
        context = {
            "my_budget": 180,
            "my_roster": {},
            "avg_budget": 150,
            "stars_acquired": 0,
            "roster_spots_left": 15,
            "picks_complete": 20
        }
        
        print("Testing optimized parallel crew...")
        start = time.time()
        result = await crew.analyze_nomination(player, 45, context)
        elapsed = (time.time() - start) * 1000
        
        print(f"\nResult in {elapsed:.0f}ms:")
        print(f"  Action: {result['action']}")
        print(f"  Max Bid: ${result['max_bid']}")
        print(f"  Recommended: ${result.get('recommended_bid', 'N/A')}")
        print(f"  Reasoning: {result['reasoning']}")
        
        if elapsed < 3000:
            print("\n✅ SUCCESS - Under 3 second target!")
        else:
            print(f"\n❌ Too slow - {elapsed:.0f}ms")
    
    asyncio.run(test())