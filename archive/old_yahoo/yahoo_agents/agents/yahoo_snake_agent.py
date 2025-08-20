"""
Yahoo Fantasy Snake Draft Agent (League 2 - FULL PPR)
Using LangGraph for <3s response times

League 2 Specific Settings:
- FULL PPR (1 point per reception) 
- 6 PT passing TDs
- Return yards scoring
- WR-heavy strategy
- Only 1 QB needed
"""

import asyncio
import os
from typing import Dict, List, Optional, TypedDict
from datetime import datetime
import json

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# LangChain imports  
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableParallel
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Local imports for data
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from data_providers.direct_fantasypros import get_direct_fantasypros_client


# League 2 specific constants
LEAGUE_2_SETTINGS = {
    "scoring": "FULL_PPR",
    "passing_td": 6,
    "positions": {
        "QB": 1,
        "RB": 2,
        "WR": 2,
        "TE": 1,
        "FLEX": 1,  # W/R Flex
        "K": 1,
        "DEF": 1,
        "BENCH": 7
    },
    "bonuses": {
        "passing_300": 3,
        "rushing_90": 3,
        "receiving_100": 3
    },
    "return_scoring": True  # 25 yards/point, 6 PT TDs
}


class SnakeDraftState(TypedDict):
    """State for Yahoo Snake Draft (League 2)"""
    # Input
    round: int
    pick_number: int
    user_roster: Dict[str, List]
    available_players: List[Dict]
    
    # Analysis (parallel)
    wr_priority_score: Optional[float]  # WR value in Full PPR
    rb_pass_catch_scores: Optional[Dict]  # Pass-catching RB values
    return_specialist_bonus: Optional[List]  # Players with return value
    position_scarcity: Optional[Dict]
    
    # Output
    recommendations: Optional[List[Dict]]
    strategy_notes: Optional[str]
    response_time_ms: Optional[int]


class YahooSnakeDraftAgent:
    """
    Optimized agent for Yahoo Snake Draft (League 2)
    Full PPR specific strategies
    """
    
    def __init__(self, anthropic_api_key: str = None):
        self.api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        
        # Use Haiku for speed on most tasks
        self.fast_llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            api_key=self.api_key,
            temperature=0.2,
            max_tokens=300
        )
        
        # Sonnet only for final synthesis
        self.smart_llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=self.api_key,
            temperature=0.4,
            max_tokens=500
        )
        
        self.graph = self._build_graph()
        self.memory = MemorySaver()
        self.app = self.graph.compile(checkpointer=self.memory)
        
        # Pre-computed Full PPR strategies
        self.ppr_strategies = self._load_ppr_strategies()
        
        # FantasyPros direct client for live data
        self.fp_client = get_direct_fantasypros_client()
        
        # Cache for rankings data
        self.rankings_cache = None
        self.rankings_cache_time = None
        
    def _build_graph(self) -> StateGraph:
        """Build optimized graph for snake draft"""
        workflow = StateGraph(SnakeDraftState)
        
        # Nodes
        workflow.add_node("quick_check", self.quick_position_check)
        workflow.add_node("parallel_ppr_analysis", self.parallel_ppr_analysis)
        workflow.add_node("synthesize", self.synthesize_picks)
        
        # Edges
        workflow.add_conditional_edges(
            "quick_check",
            self.needs_deep_analysis,
            {
                "simple": "synthesize",
                "complex": "parallel_ppr_analysis"
            }
        )
        
        workflow.add_edge("parallel_ppr_analysis", "synthesize")
        workflow.add_edge("synthesize", END)
        
        workflow.set_entry_point("quick_check")
        
        return workflow
    
    async def quick_position_check(self, state: SnakeDraftState) -> SnakeDraftState:
        """Quick rule-based check for obvious picks"""
        roster = state["user_roster"]
        round_num = state["round"]
        
        # Full PPR specific quick rules
        qb_count = len(roster.get("QB", []))
        rb_count = len(roster.get("RB", []))
        wr_count = len(roster.get("WR", []))
        te_count = len(roster.get("TE", []))
        
        # Check if we have pre-filtered players (means user asked for specific position)
        available = state["available_players"]
        if available and len(available) <= 30:
            # We have a filtered list, check what positions are available
            positions = set(p.get("position") for p in available[:10])
            if len(positions) == 1:
                # User asked for specific position
                pos = list(positions)[0]
                if available:
                    # Return top 3 at that position
                    recs = []
                    for p in available[:3]:
                        if pos == "QB":
                            reason = "Top QB with 6PT passing TD bonus in Full PPR"
                        elif pos == "WR":
                            reason = "Elite WR for Full PPR scoring"
                        elif pos == "RB":
                            reason = "Top RB with pass-catching upside"
                        elif pos == "TE":
                            reason = "Top TE target"
                        else:
                            reason = f"Best available {pos}"
                        
                        recs.append({
                            "name": p.get("name", "Unknown"),
                            "position": p.get("position", pos),
                            "reason": reason
                        })
                    
                    state["recommendations"] = recs
                    state["response_time_ms"] = 100
                    return state
        
        # Original roster-based logic only if no specific query
        obvious_need = None
        
        if round_num <= 10:  # Core roster rounds
            if te_count == 0 and round_num >= 4:
                obvious_need = "TE"
            elif qb_count == 0 and round_num >= 6:
                obvious_need = "QB"
            elif wr_count < 2:
                obvious_need = "WR"  # WR priority in Full PPR
            elif rb_count < 2:
                obvious_need = "RB"
        
        if obvious_need:
            # Find best available at position
            candidates = [p for p in state["available_players"][:20] 
                         if p.get("position") == obvious_need]
            if candidates:
                state["recommendations"] = [{
                    "name": candidates[0]["name"],
                    "position": obvious_need,
                    "reason": f"Critical need at {obvious_need} in Full PPR"
                }]
                state["response_time_ms"] = 50  # Near instant
        
        return state
    
    async def parallel_ppr_analysis(self, state: SnakeDraftState) -> SnakeDraftState:
        """Run Full PPR specific analyses in parallel"""
        start = datetime.now()
        
        # Parallel tasks optimized for Full PPR
        analyses = RunnableParallel(
            wr_values=self._analyze_wr_value_ppr,
            rb_pass_catching=self._analyze_rb_pass_catching,
            return_specialists=self._find_return_specialists,
            scarcity=self._check_position_scarcity
        )
        
        # Run all in parallel
        results = await analyses.ainvoke({
            "available": state["available_players"][:30],  # Top 30 only for speed
            "roster": state["user_roster"],
            "round": state["round"]
        })
        
        # Update state
        state["wr_priority_score"] = results["wr_values"]
        state["rb_pass_catch_scores"] = results["rb_pass_catching"]
        state["return_specialist_bonus"] = results["return_specialists"]
        state["position_scarcity"] = results["scarcity"]
        
        state["response_time_ms"] = int((datetime.now() - start).total_seconds() * 1000)
        
        return state
    
    async def synthesize_picks(self, state: SnakeDraftState) -> SnakeDraftState:
        """Synthesize Full PPR optimized recommendations"""
        
        if state.get("recommendations"):
            # Already have quick pick
            return state
        
        # Get available players and their positions
        available = state.get("available_players", [])[:10]
        player_list = "\n".join([f"- {p.get('name', 'Unknown')} ({p.get('position', '??')})" for p in available])
        
        # Build context for Full PPR
        context = f"""
        FULL PPR LEAGUE (1 point per reception)
        Round {state['round']}, Pick {state['pick_number']}
        
        Available Players:
        {player_list}
        
        WR Priority Score: {state.get('wr_priority_score', 'N/A')}
        Top Pass-Catching RBs: {json.dumps(state.get('rb_pass_catch_scores', {}))[:200]}
        Return Specialists Available: {state.get('return_specialist_bonus', [])}
        
        Strategy: Prioritize WRs and pass-catching RBs. Return yards are bonus.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a Full PPR draft expert.
            WRs are premium. Pass-catching RBs > rushing RBs.
            Return specialists get bonus points.
            IMPORTANT: Only recommend players from the Available Players list provided.
            Format: [{"name": "Player", "position": "POS", "reason": "PPR-specific reason"}]"""),
            HumanMessage(content=context + "\nRecommend top 3 picks from the available players for Full PPR.")
        ])
        
        chain = prompt | self.smart_llm | JsonOutputParser()
        
        try:
            recommendations = await chain.ainvoke({})
            state["recommendations"] = recommendations[:3]
        except:
            # Fallback to simple recommendations from available players
            state["recommendations"] = self._get_fallback_ppr_picks(state)
        
        state["strategy_notes"] = "Full PPR: Target WRs and pass-catching backs"
        
        return state
    
    def needs_deep_analysis(self, state: SnakeDraftState) -> str:
        """Decide if we need deep analysis or can use quick pick"""
        if state.get("recommendations"):
            return "simple"
        return "complex"
    
    async def _analyze_wr_value_ppr(self, data: Dict) -> float:
        """Calculate WR priority in Full PPR"""
        available = data["available"]
        
        # Count top WRs available (handle both field names)
        top_wrs = [p for p in available if p.get("position", p.get("player_position_id")) == "WR"][:10]
        
        if len(top_wrs) < 3:
            return 0.9  # High priority - scarcity
        elif len(top_wrs) > 7:
            return 0.5  # Medium - plenty available
        else:
            return 0.7  # Good value zone
    
    async def _analyze_rb_pass_catching(self, data: Dict) -> Dict:
        """Identify pass-catching RBs for Full PPR"""
        # In real implementation, would check reception projections
        # For now, use heuristics based on player names/teams
        
        pass_catch_rbs = {
            "Christian McCaffrey": 0.95,
            "Austin Ekeler": 0.90,
            "Alvin Kamara": 0.88,
            "Saquon Barkley": 0.85,
            "Tony Pollard": 0.75,
            "James Conner": 0.70
        }
        
        available = data["available"]
        scores = {}
        
        for player in available:
            if player.get("position", player.get("player_position_id")) == "RB":
                name = player.get("name", player.get("player_name", ""))
                # Check if known pass-catcher
                for rb_name, score in pass_catch_rbs.items():
                    if rb_name in name:
                        scores[name] = score
                        break
        
        return scores
    
    async def _find_return_specialists(self, data: Dict) -> List[str]:
        """Find players with return value (League 2 specific)"""
        # Players known for return TDs
        return_specialists = [
            "Deebo Samuel", "Tyreek Hill", "Rashid Shaheed",
            "KaVontae Turpin", "Jaylen Waddle"
        ]
        
        available = data["available"]
        found = []
        
        for player in available:
            name = player.get("name", "")
            if any(rs in name for rs in return_specialists):
                found.append(name)
        
        return found[:3]  # Top 3 max
    
    async def _check_position_scarcity(self, data: Dict) -> Dict:
        """Check position scarcity for draft"""
        available = data["available"]
        
        counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}
        
        for player in available:
            pos = player.get("position", player.get("player_position_id", ""))
            if pos in counts:
                counts[pos] += 1
        
        scarcity = {}
        for pos, count in counts.items():
            if count < 3:
                scarcity[pos] = "CRITICAL"
            elif count < 8:
                scarcity[pos] = "HIGH"
            else:
                scarcity[pos] = "NORMAL"
        
        return scarcity
    
    def _load_ppr_strategies(self) -> Dict:
        """Load pre-computed Full PPR strategies"""
        return {
            "early_rounds": "WR > RB unless elite RB available",
            "mid_rounds": "Fill RB2/WR3, grab pass-catching backs",
            "late_rounds": "Target upside WRs, wait on QB",
            "avoid": "Non-catching RBs, early QBs (only need 1)"
        }
    
    def _get_fallback_ppr_picks(self, state: SnakeDraftState) -> List[Dict]:
        """Simple fallback for Full PPR"""
        picks = []
        available = state["available_players"][:10]
        
        # Use the actual filtered players
        for p in available[:3]:
            pos = p.get("position", "??")
            if pos == "QB":
                reason = "Top QB with 6PT passing TD bonus"
            elif pos == "WR":
                reason = "Elite WR for Full PPR premium"
            elif pos == "RB":
                reason = "Pass-catching RB for PPR value"
            elif pos == "TE":
                reason = "Top TE target with reception upside"
            else:
                reason = f"Best available {pos}"
                
            picks.append({
                "name": p.get("name", "Unknown"),
                "position": pos,
                "reason": reason
            })
        
        return picks
    
    async def _fetch_live_rankings(self, position: str = "ALL") -> List[Dict]:
        """Fetch live rankings from FantasyPros MCP with caching"""
        # Cache for 30 minutes to avoid excessive MCP calls
        if self.rankings_cache and self.rankings_cache_time:
            if (datetime.now() - self.rankings_cache_time).seconds < 1800:
                return self.rankings_cache
        
        # Fetch from MCP (League 2 = Full PPR)
        raw_rankings = await self.fp_client.get_rankings_for_yahoo_league(2, position)
        
        # Ensure field mapping even if empty
        if not raw_rankings:
            return []
        
        # Apply League 2 specific adjustments (includes field mapping)
        rankings = self._apply_league2_adjustments(raw_rankings)
        
        # Cache the results
        self.rankings_cache = rankings
        self.rankings_cache_time = datetime.now()
        
        return rankings
    
    def _apply_league2_adjustments(self, rankings: List[Dict]) -> List[Dict]:
        """
        Apply League 2 specific scoring adjustments
        - 6PT passing TDs (15% QB boost)
        - Full PPR (WR and pass-catching RB boost)
        - Return yards bonus
        - Bonus points at yardage thresholds
        """
        adjusted = []
        
        for player in rankings:
            p = player.copy()
            
            # Map FantasyPros field names to expected names
            position = p.get("player_position_id", p.get("position", ""))
            p["position"] = position  # Ensure position field exists
            p["name"] = p.get("player_name", p.get("name", "Unknown"))
            p["team"] = p.get("player_team_id", p.get("team", ""))
            p["rank"] = p.get("rank_ecr", p.get("rank", 999))
            
            # QB adjustment for 6PT passing TDs
            if position == "QB":
                # QBs are MORE valuable with 6PT TDs
                p["l2_adjustment"] = 1.15
                p["adjusted_rank"] = p.get("rank", 999) * 0.87  # Better rank
                p["strategy_note"] = "6PT passing TD bonus"
                
            # WR boost for Full PPR
            elif position == "WR":
                p["l2_adjustment"] = 1.25
                p["adjusted_rank"] = p.get("rank", 999) * 0.80
                p["strategy_note"] = "Full PPR premium"
                
                # Extra boost for return specialists
                return_guys = ["Tyreek Hill", "Deebo Samuel", "Rashid Shaheed", 
                             "KaVontae Turpin", "Jaylen Waddle"]
                if any(name in p["name"] for name in return_guys):
                    p["return_bonus"] = True
                    p["l2_adjustment"] *= 1.05
                    p["adjusted_rank"] *= 0.95
                    p["strategy_note"] += " + Return yards"
                    
            # RB adjustments based on receiving ability
            elif position == "RB":
                # Known pass-catching backs get boost
                pass_catchers = {
                    "Christian McCaffrey": 1.20,
                    "Austin Ekeler": 1.18,
                    "Alvin Kamara": 1.15,
                    "Breece Hall": 1.12,
                    "Rachaad White": 1.10,
                    "Kenneth Walker": 0.95,  # Not a pass-catcher
                    "Nick Chubb": 0.93  # Pure rusher, less valuable
                }
                
                for rb_name, multiplier in pass_catchers.items():
                    if rb_name in p["name"]:
                        p["l2_adjustment"] = multiplier
                        p["adjusted_rank"] = p.get("rank", 999) / multiplier
                        p["strategy_note"] = "Pass-catching RB" if multiplier > 1 else "Pure rusher"
                        break
                else:
                    # Default RB adjustment
                    p["l2_adjustment"] = 1.05
                    p["adjusted_rank"] = p.get("rank", 999) * 0.95
                    
            # TE gets small PPR boost
            elif position == "TE":
                p["l2_adjustment"] = 1.08
                p["adjusted_rank"] = p.get("rank", 999) * 0.93
                p["strategy_note"] = "PPR TE value"
            
            else:
                p["adjusted_rank"] = p.get("rank", 999)
                
            adjusted.append(p)
        
        # Re-sort by adjusted rank
        adjusted.sort(key=lambda x: x.get("adjusted_rank", 999))
        
        return adjusted
    
    async def get_recommendation(self, context: Dict) -> Dict:
        """Get Full PPR optimized recommendation"""
        start = datetime.now()
        
        # Parse the query to understand what user is asking
        query_text = context.get("query", "").lower()
        print(f"🎯 Yahoo Snake processing query: '{query_text}'")
        
        # Check for questions about draft position/status
        if any(phrase in query_text for phrase in ["what pick", "draft position", "draft slot", "which pick", "my turn"]):
            draft_slot = context.get("draft_slot", "unknown")
            current_pick = context.get("current_pick", 1)
            current_round = context.get("current_round", 1)
            my_turn = context.get("my_turn", False)
            
            response = f"You have the **#{draft_slot} pick** in this 10-team Full PPR draft.\n\n"
            response += f"Current status: Pick #{current_pick} (Round {current_round})\n"
            if my_turn:
                response += "🎯 **It's your turn to pick!**\n\n"
                # Also give a recommendation
                response += "Since you're up, I recommend taking the best available WR or pass-catching RB for Full PPR value."
            else:
                # Calculate when next pick is in snake draft
                if draft_slot and draft_slot != "unknown":
                    slot = int(draft_slot)
                    # Snake draft logic
                    if current_round % 2 == 1:  # Odd round
                        if current_pick % 10 < slot:
                            picks_until = slot - (current_pick % 10)
                        else:
                            picks_until = (20 - (current_pick % 10)) + (11 - slot)
                    else:  # Even round  
                        if (11 - (current_pick % 10)) < slot:
                            picks_until = (current_pick % 10) + slot - 11
                        else:
                            picks_until = (11 - slot) - (current_pick % 10)
                    
                    if picks_until > 0:
                        response += f"Your next pick is in **{picks_until} selections**"
            
            return response
        
        # Fetch live rankings if not provided
        if not context.get("available_players"):
            live_rankings = await self._fetch_live_rankings()
            # Filter to only undrafted players (would need draft history)
            context["available_players"] = live_rankings[:100]
        
        # Filter available players based on query
        available = context["available_players"]
        filtered_players = available
        
        # Parse query for specific requests
        if "not" in query_text and "chase" in query_text:
            # User asking for someone other than Jamarr Chase
            filtered_players = [p for p in available if "chase" not in p.get("name", "").lower()]
            print(f"   Filtering out Chase, {len(filtered_players)} players remain")
        elif "rb or wr" in query_text or "wr or rb" in query_text:
            # User asking about RB vs WR decision
            filtered_players = [p for p in available if p.get("position") in ["RB", "WR"]]
            print(f"   Filtering to RB/WR, {len(filtered_players)} players")
        elif "rb" in query_text and "wr" not in query_text:
            # User specifically asking about RBs
            filtered_players = [p for p in available if p.get("position") == "RB"]
            print(f"   Filtering to RBs only, {len(filtered_players)} players")
        elif "wr" in query_text and "rb" not in query_text:
            # User specifically asking about WRs
            filtered_players = [p for p in available if p.get("position") == "WR"]
            print(f"   Filtering to WRs only, {len(filtered_players)} players")
        elif "qb" in query_text:
            # User asking about QBs
            filtered_players = [p for p in available if p.get("position") == "QB"]
            print(f"   Filtering to QBs, {len(filtered_players)} players")
        elif "te" in query_text:
            # User asking about TEs
            filtered_players = [p for p in available if p.get("position") == "TE"]
            print(f"   Filtering to TEs, {len(filtered_players)} players")
        elif "sleeper" in query_text or "late" in query_text:
            # User asking for sleepers/late round values
            filtered_players = [p for p in available if p.get("rank", 999) > 50][:20]
            print(f"   Filtering to sleepers, {len(filtered_players)} players")
        elif "value" in query_text:
            # User asking for value picks - players ranked better than ADP
            filtered_players = sorted(available, 
                                    key=lambda x: x.get("rank", 999) - x.get("adp", x.get("rank", 999)))[:20]
            print(f"   Filtering to value picks, {len(filtered_players)} players")
        else:
            print(f"   No specific filter applied, using top {len(available[:30])} players")
        
        # Update context with filtered players
        context["available_players"] = filtered_players[:30] if filtered_players else available[:30]
        print(f"   Final player list: {len(context['available_players'])} players")
        if context["available_players"]:
            print(f"   Top 3: {[p.get('name', 'Unknown') for p in context['available_players'][:3]]}")
        
        state = SnakeDraftState(
            round=context.get("round", 1),
            pick_number=context.get("pick_number", 1),
            user_roster=context.get("user_roster", {}),
            available_players=context["available_players"],
            wr_priority_score=None,
            rb_pass_catch_scores=None,
            return_specialist_bonus=None,
            position_scarcity=None,
            recommendations=None,
            strategy_notes=None,
            response_time_ms=None
        )
        
        # Add config with thread_id for checkpointer
        config = {"configurable": {"thread_id": "yahoo-snake-draft"}}
        result = await self.app.ainvoke(state, config)
        
        # Add query-specific strategy notes
        if "rb or wr" in query_text:
            result["strategy_notes"] = "In Full PPR, WRs typically have more consistent floors due to reception points. Target WRs unless an elite pass-catching RB is available."
        elif "not" in query_text and "chase" in query_text:
            result["strategy_notes"] = "Looking at alternatives to Chase. In Full PPR, consider other elite WRs or pass-catching RBs."
        elif "sleeper" in query_text:
            result["strategy_notes"] = "Late-round targets in Full PPR: Focus on high-volume pass catchers and slot receivers."
        
        total_ms = int((datetime.now() - start).total_seconds() * 1000)
        
        return {
            "recommendations": result.get("recommendations", []),
            "strategy": result.get("strategy_notes", ""),
            "analysis_time_ms": result.get("response_time_ms", 0),
            "total_time_ms": total_ms,
            "league": "Yahoo Snake - Full PPR (6PT Pass TD)"
        }


# Test function
async def test_snake_agent():
    """Test Yahoo Snake Draft agent"""
    print("\n" + "="*60)
    print("YAHOO SNAKE DRAFT AGENT TEST (League 2 - Full PPR)")
    print("="*60)
    
    test_context = {
        "round": 3,
        "pick_number": 28,
        "user_roster": {
            "QB": [],
            "RB": ["Bijan Robinson"],
            "WR": ["Tyreek Hill"],  # Return specialist!
            "TE": [],
            "K": [],
            "DEF": []
        },
        "available_players": [
            {"name": "Davante Adams", "position": "WR", "rank": 15},
            {"name": "Travis Etienne", "position": "RB", "rank": 18},
            {"name": "Chris Olave", "position": "WR", "rank": 22},
            {"name": "Mark Andrews", "position": "TE", "rank": 5},
            {"name": "Lamar Jackson", "position": "QB", "rank": 3}
        ]
    }
    
    agent = YahooSnakeDraftAgent()
    
    for i in range(2):
        print(f"\n--- Test {i+1} ---")
        result = await agent.get_recommendation(test_context)
        
        print(f"⏱️ Total: {result['total_time_ms']}ms")
        print(f"📊 Analysis: {result['analysis_time_ms']}ms")
        print(f"📋 Strategy: {result['strategy']}")
        print("\n🎯 Recommendations:")
        for j, rec in enumerate(result['recommendations'], 1):
            print(f"  {j}. {rec['name']} ({rec['position']}) - {rec['reason']}")
        
        if result['total_time_ms'] < 3000:
            print("✅ Under 3s target!")


if __name__ == "__main__":
    asyncio.run(test_snake_agent())