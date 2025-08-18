"""
Sleeper Fantasy Auction Draft Agent (League 3 - HALF PPR)
Using LangGraph for real-time bidding decisions

League 3 Specific Settings (Now on Sleeper):
- HALF PPR (0.5 points per reception)
- $200 budget auction format
- 4 PT passing TDs (QB less valuable)
- NO KICKER position
- Stars & Scrubs strategy recommended
- 12-team league
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
from data_providers import AuctionValueCalculator


# League 3 specific constants
LEAGUE_3_SETTINGS = {
    "scoring": "HALF_PPR",
    "passing_td": 4,  # Lower QB value
    "budget": 200,
    "positions": {
        "QB": 1,
        "RB": 2,
        "WR": 2,
        "TE": 1,
        "FLEX": 1,  # W/R/T Flex
        "DEF": 1,
        "BENCH": 5,
        "IR": 1
        # NO KICKER
    },
    "strategy": "STARS_AND_SCRUBS"
}


class AuctionState(TypedDict):
    """State for Yahoo Auction Draft (League 3)"""
    # Budget tracking
    remaining_budget: int
    spent_budget: int
    avg_remaining_per_slot: float
    
    # Roster state
    user_roster: Dict[str, List]
    roster_slots_filled: int
    roster_slots_remaining: int
    
    # Current bidding
    player_up: Dict  # Player being bid on
    current_bid: int
    suggested_max: Optional[int]
    
    # Market analysis (parallel)
    market_inflation: Optional[float]  # Are players going over/under value?
    positional_runs: Optional[Dict]  # Position run detection
    opponent_budgets: Optional[List[Dict]]  # Track opponent spending
    value_targets: Optional[List[Dict]]  # Undervalued players to target
    
    # Strategy state
    stars_acquired: int  # How many high-$ players we have
    strategy_phase: str  # "STARS", "VALUE", "SCRUBS"
    
    # Output
    bid_recommendation: Optional[Dict]
    nomination_suggestion: Optional[Dict]
    strategy_notes: Optional[str]
    response_time_ms: Optional[int]


class SleeperAuctionAgent:
    """
    Auction draft agent for Sleeper League 3
    Optimized for Half-PPR with Stars & Scrubs strategy
    """
    
    def __init__(self, anthropic_api_key: str = None):
        self.api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        
        # Fast model for real-time bidding
        self.fast_llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            api_key=self.api_key,
            temperature=0.1,  # Low temp for consistent bidding
            max_tokens=200
        )
        
        # Smart model for strategy decisions
        self.strategy_llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=self.api_key,
            temperature=0.3,
            max_tokens=400
        )
        
        self.graph = self._build_auction_graph()
        self.memory = MemorySaver()
        self.app = self.graph.compile(checkpointer=self.memory)
        
        # Auction-specific data
        self.player_values = self._load_auction_values()
        
        # Advanced auction calculator
        self.auction_calculator = AuctionValueCalculator(
            budget=200,
            num_teams=12,
            roster_spots=15
        )
        
        # FantasyPros MCP client
        self.fp_client = get_direct_fantasypros_client()
        
        # Cache for calculated values
        self.calculated_values_cache = None
        
    def _build_auction_graph(self) -> StateGraph:
        """Build graph for auction decisions"""
        workflow = StateGraph(AuctionState)
        
        # Nodes
        workflow.add_node("budget_check", self.check_budget_constraints)
        workflow.add_node("parallel_market_analysis", self.analyze_market_parallel)
        workflow.add_node("bid_decision", self.make_bid_decision)
        workflow.add_node("nomination_strategy", self.suggest_nomination)
        
        # Conditional routing based on auction phase
        workflow.add_conditional_edges(
            "budget_check",
            self.route_by_phase,
            {
                "immediate_bid": "bid_decision",
                "analyze_first": "parallel_market_analysis",
                "nomination": "nomination_strategy"
            }
        )
        
        workflow.add_edge("parallel_market_analysis", "bid_decision")
        workflow.add_edge("bid_decision", END)
        workflow.add_edge("nomination_strategy", END)
        
        workflow.set_entry_point("budget_check")
        
        return workflow
    
    async def check_budget_constraints(self, state: AuctionState) -> AuctionState:
        """Quick budget and roster checks"""
        # Calculate budget per remaining slot
        slots_left = state["roster_slots_remaining"]
        budget_left = state["remaining_budget"]
        
        if slots_left > 0:
            state["avg_remaining_per_slot"] = budget_left / slots_left
        else:
            state["avg_remaining_per_slot"] = 0
        
        # Determine strategy phase
        if state["stars_acquired"] < 2 and budget_left > 120:
            state["strategy_phase"] = "STARS"
        elif state["stars_acquired"] >= 2 and budget_left > 40:
            state["strategy_phase"] = "VALUE"
        else:
            state["strategy_phase"] = "SCRUBS"
        
        # Quick bid limits based on phase
        if state.get("player_up"):
            player_pos = state["player_up"].get("position", "")
            
            # Half-PPR specific: RB/WR balanced, QB cheap
            if state["strategy_phase"] == "STARS":
                max_bids = {"RB": 65, "WR": 60, "TE": 35, "QB": 15}
            elif state["strategy_phase"] == "VALUE":
                max_bids = {"RB": 25, "WR": 20, "TE": 12, "QB": 8}
            else:  # SCRUBS
                max_bids = {"RB": 5, "WR": 4, "TE": 2, "QB": 2}
            
            state["suggested_max"] = max_bids.get(player_pos, 1)
        
        return state
    
    async def analyze_market_parallel(self, state: AuctionState) -> AuctionState:
        """Parallel market analysis for auction"""
        start = datetime.now()
        
        analyses = RunnableParallel(
            inflation=self._check_market_inflation,
            runs=self._detect_position_runs,
            opponents=self._analyze_opponent_budgets,
            values=self._find_value_targets
        )
        
        results = await analyses.ainvoke({
            "spent": state["spent_budget"],
            "remaining": state["remaining_budget"],
            "roster": state["user_roster"],
            "opponents": state.get("opponent_budgets", [])
        })
        
        state["market_inflation"] = results["inflation"]
        state["positional_runs"] = results["runs"]
        state["opponent_budgets"] = results["opponents"]
        state["value_targets"] = results["values"]
        
        state["response_time_ms"] = int((datetime.now() - start).total_seconds() * 1000)
        
        return state
    
    async def make_bid_decision(self, state: AuctionState) -> AuctionState:
        """Make real-time bidding decision"""
        player = state.get("player_up", {})
        current_bid = state.get("current_bid", 0)
        max_bid = state.get("suggested_max", 0)
        
        # Adjust for market inflation
        inflation = state.get("market_inflation", 1.0)
        adjusted_max = int(max_bid * inflation)
        
        # Check if we should bid
        should_bid = False
        bid_amount = 0
        
        if current_bid < adjusted_max:
            # We're under our max
            should_bid = True
            # Bid increment logic
            if current_bid < 10:
                bid_amount = current_bid + 1
            elif current_bid < 30:
                bid_amount = current_bid + 2
            else:
                bid_amount = current_bid + 3
            
            # Don't exceed our max
            bid_amount = min(bid_amount, adjusted_max)
        
        # Stars & Scrubs specific logic
        if state["strategy_phase"] == "STARS":
            # Be aggressive on elite players
            if player.get("rank", 100) <= 15:
                bid_amount = min(bid_amount * 1.1, state["remaining_budget"] - 50)
                should_bid = True
        elif state["strategy_phase"] == "SCRUBS":
            # Only $1-2 players
            if current_bid > 2:
                should_bid = False
        
        state["bid_recommendation"] = {
            "should_bid": should_bid,
            "amount": int(bid_amount) if should_bid else 0,
            "max_bid": adjusted_max,
            "reason": f"{state['strategy_phase']} phase - {'Bid' if should_bid else 'Pass'}"
        }
        
        return state
    
    async def suggest_nomination(self, state: AuctionState) -> AuctionState:
        """Suggest player to nominate"""
        # Stars & Scrubs nomination strategy
        if state["strategy_phase"] == "STARS":
            # Nominate expensive players we DON'T want to drain budgets
            suggestion = {
                "type": "DRAIN",
                "positions": ["QB"],  # Expensive QBs we don't want
                "price_range": "$25-40",
                "reason": "Drain opponent budgets on QBs (low value in 4PT TD)"
            }
        elif state["strategy_phase"] == "VALUE":
            # Nominate mid-tier players at our positions of need
            needs = self._get_position_needs(state["user_roster"])
            suggestion = {
                "type": "TARGET",
                "positions": needs[:2],
                "price_range": "$8-20",
                "reason": "Target value at positions of need"
            }
        else:  # SCRUBS
            # Nominate $1 players we want
            suggestion = {
                "type": "SLEEPER",
                "positions": ["WR", "RB"],
                "price_range": "$1-2",
                "reason": "Get sleepers before others realize"
            }
        
        state["nomination_suggestion"] = suggestion
        state["strategy_notes"] = f"Auction Strategy: {state['strategy_phase']}"
        
        return state
    
    def route_by_phase(self, state: AuctionState) -> str:
        """Route based on auction context"""
        if state.get("player_up") and state.get("current_bid") is not None:
            # Active bidding - need quick decision
            if state["response_time_ms"] is None:
                return "analyze_first"
            return "immediate_bid"
        else:
            # Nomination phase
            return "nomination"
    
    async def _check_market_inflation(self, data: Dict) -> float:
        """Check if market is inflated or deflated"""
        # Simple heuristic: if >30% spent and <30% roster filled = inflation
        spent_pct = data["spent"] / LEAGUE_3_SETTINGS["budget"]
        
        if spent_pct > 0.3:
            return 1.15  # Inflated market
        elif spent_pct < 0.15:
            return 0.85  # Deflated market
        return 1.0
    
    async def _detect_position_runs(self, data: Dict) -> Dict:
        """Detect if position run is happening"""
        # Would track recent picks in real implementation
        return {
            "QB": False,
            "RB": False,
            "WR": True,  # Mock: WR run happening
            "TE": False
        }
    
    async def _analyze_opponent_budgets(self, data: Dict) -> List[Dict]:
        """Track opponent spending patterns"""
        # Mock opponent data
        return [
            {"team": "Team1", "budget_left": 150, "needs": ["RB", "WR"]},
            {"team": "Team2", "budget_left": 45, "needs": ["QB", "TE"]},
            {"team": "Team3", "budget_left": 180, "needs": ["RB", "RB"]}
        ]
    
    async def _find_value_targets(self, data: Dict) -> List[Dict]:
        """Find undervalued players to target"""
        # Half-PPR value targets
        return [
            {"name": "Rachaad White", "position": "RB", "target_price": 18},
            {"name": "Diontae Johnson", "position": "WR", "target_price": 15},
            {"name": "Dallas Goedert", "position": "TE", "target_price": 8}
        ]
    
    def _get_position_needs(self, roster: Dict) -> List[str]:
        """Determine position needs"""
        needs = []
        
        if len(roster.get("QB", [])) < 1:
            needs.append("QB")
        if len(roster.get("RB", [])) < 3:
            needs.append("RB")
        if len(roster.get("WR", [])) < 3:
            needs.append("WR")
        if len(roster.get("TE", [])) < 1:
            needs.append("TE")
        
        return needs
    
    def _load_auction_values(self) -> Dict:
        """Load Half-PPR auction values"""
        return {
            "budget_allocation": {
                "stars": 140,  # 70% on 3-4 studs
                "value": 50,   # 25% on mid-tier
                "scrubs": 10   # 5% on $1 players
            },
            "position_values": {
                "QB": 0.10,  # 10% of budget max (4PT TDs)
                "RB": 0.35,  # 35% max on one RB
                "WR": 0.32,  # 32% max on one WR
                "TE": 0.15   # 15% max on TE
            }
        }
    
    async def get_bid_recommendation(self, context: Dict) -> Dict:
        """Get real-time bidding recommendation"""
        # Log what context we're receiving
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Auction agent received context: {context.keys()}")
        logger.info(f"My budget: ${context.get('my_budget')}")
        logger.info(f"My roster size: {context.get('roster_size', 0)}")
        
        # Get roster and budget info
        my_budget = context.get("my_budget", 200)
        my_roster = context.get("user_roster", [])
        roster_size = len(my_roster)
        
        # Parse the query to understand what user is asking
        query_text = context.get("query", "").lower()
        
        # Check for roster questions
        if ("roster" in query_text or "team" in query_text or "who do i have" in query_text):
            if roster_size == 0:
                return {"message": "Your roster is empty. Time to start bidding!"}
            else:
                roster_summary = f"You have {roster_size} players for ${200 - my_budget} total"
                return {
                    "message": f"**Your Roster**: {roster_summary}",
                    "budget": f"Remaining: ${my_budget} (avg per slot: ${my_budget / max(1, 16-roster_size):.0f})",
                    "recommendation": "Focus on value picks with your remaining budget"
                }
        
        # Handle explicit player bidding questions (e.g., "Tyreek Hill is up for $45")
        import re
        player_pattern = r"([A-Z][a-z]+ [A-Z][a-z]+|[A-Z]\.[A-Z]\. [A-Z][a-z]+).*\$(\d+)"
        match = re.search(player_pattern, query_text.title())
        if match:
            player_name = match.group(1)
            current_bid = int(match.group(2))
            
            # Smarter value check based on budget and roster needs
            slots_remaining = max(1, 16 - roster_size)
            avg_per_slot = my_budget / slots_remaining
            
            # Don't spend more than 40% on one player unless it's a stud and you have budget
            if roster_size < 3:  # Early, can spend on studs
                max_bid = min(current_bid + 15, my_budget * 0.4)
            else:  # Later, be more conservative
                max_bid = min(current_bid + 5, avg_per_slot * 2)
            
            return {
                "message": f"For **{player_name}** at ${current_bid}:",
                "recommendation": f"Max bid: **${max_bid}**",
                "reasoning": f"Budget: ${my_budget}, {slots_remaining} slots left (${avg_per_slot:.0f}/slot avg)",
                "verdict": "✅ BID" if current_bid < max_bid - 5 else "⚠️ PASS"
            }
        
        # Check if asking about current player
        if "who" in query_text and ("up" in query_text or "auction" in query_text or "current" in query_text):
            # Can't determine from API, ask user to provide info
            return {
                "message": "I can't see who's currently up in the mock draft. Tell me who's up and for how much (e.g., 'Tyreek Hill is up for $45')",
                "tip": "Or ask me who to nominate next!"
            }
        
        # Initialize state with defaults
        state = AuctionState(
            remaining_budget=context.get("remaining_budget", 200),
            spent_budget=context.get("spent_budget", 0),
            avg_remaining_per_slot=0,
            user_roster=context.get("user_roster", {}),
            roster_slots_filled=context.get("slots_filled", 0),
            roster_slots_remaining=context.get("slots_remaining", 15),
            player_up=context.get("player_up"),
            current_bid=context.get("current_bid", 0),
            suggested_max=None,
            market_inflation=None,
            positional_runs=None,
            opponent_budgets=None,
            value_targets=None,
            stars_acquired=context.get("stars_acquired", 0),
            strategy_phase="",
            bid_recommendation=None,
            nomination_suggestion=None,
            strategy_notes=None,
            response_time_ms=None
        )
        
        # Parse query for specific auction requests
        if "rb or wr" in query_text or "wr or rb" in query_text:
            # User asking about position to nominate
            state["nomination_suggestion"] = {
                "type": "VALUE",
                "positions": ["RB", "WR"],
                "price_range": "$15-25",
                "reason": "In Half PPR, both RBs and WRs have value. Target whichever position has better value at current market prices."
            }
        elif "qb" in query_text and "nominate" in query_text:
            # User asking about nominating QBs
            state["nomination_suggestion"] = {
                "type": "DRAIN",
                "positions": ["QB"],
                "price_range": "$20-30",
                "reason": "Nominate expensive QBs to drain budgets. With 4PT passing TDs, QBs are overvalued by others."
            }
        elif "cheap" in query_text or "value" in query_text or "$1" in query_text:
            # User asking about cheap players
            state["nomination_suggestion"] = {
                "type": "SLEEPER",
                "positions": ["WR", "RB"],
                "price_range": "$1-3",
                "reason": "Target high-upside bench players and handcuffs in the $1-3 range."
            }
        elif "stars" in query_text or "stud" in query_text:
            # User asking about stars strategy
            state["nomination_suggestion"] = {
                "type": "TARGET",
                "positions": ["RB", "WR"],
                "price_range": "$50-70",
                "reason": "Stars & Scrubs: Spend big on 2-3 elite players, then fill roster with $1 players."
            }
        elif "te" in query_text:
            # User asking about TEs
            state["nomination_suggestion"] = {
                "type": "VALUE",
                "positions": ["TE"],
                "price_range": "$8-15",
                "reason": "In Half PPR, target mid-tier TEs for value. Elite TEs are often overpriced."
            }
        
        # Add config with thread_id for checkpointer
        config = {"configurable": {"thread_id": "yahoo-auction-draft"}}
        result = await self.app.ainvoke(state, config)
        
        # Override with query-specific suggestions if we parsed something
        if state.get("nomination_suggestion") and not result.get("player_up"):
            result["nomination_suggestion"] = state["nomination_suggestion"]
        
        # Add query-specific strategy notes
        if "rb or wr" in query_text:
            result["strategy_notes"] = "Half PPR Nomination: Target the position with better value. RBs for floor, WRs for ceiling."
        elif "qb" in query_text:
            result["strategy_notes"] = "4PT Passing TDs make QBs less valuable. Never spend more than $15 on a QB."
        elif "cheap" in query_text:
            result["strategy_notes"] = "End game strategy: Target high-upside rookies and backup RBs for $1."
        
        return {
            "bid": result.get("bid_recommendation", {}),
            "nomination": result.get("nomination_suggestion", {}),
            "strategy": result.get("strategy_notes", ""),
            "phase": result.get("strategy_phase", ""),
            "response_ms": result.get("response_time_ms", 0),
            "league": "Yahoo Auction - Half PPR"
        }


# Test function
async def test_auction_agent():
    """Test Yahoo Auction agent"""
    print("\n" + "="*60)
    print("YAHOO AUCTION AGENT TEST (League 3 - Half PPR)")
    print("="*60)
    
    # Test bidding scenario
    bid_context = {
        "remaining_budget": 145,
        "spent_budget": 55,
        "user_roster": {
            "QB": [],
            "RB": ["Jonathan Taylor"],  # Got our first star
            "WR": [],
            "TE": [],
            "DEF": []
        },
        "slots_filled": 1,
        "slots_remaining": 14,
        "stars_acquired": 1,
        "player_up": {
            "name": "Justin Jefferson",
            "position": "WR",
            "rank": 3
        },
        "current_bid": 48
    }
    
    agent = YahooAuctionAgent()
    
    print("\n--- Bidding Decision Test ---")
    result = await agent.get_bid_recommendation(bid_context)
    
    print(f"⏱️ Response: {result['response_ms']}ms")
    print(f"📊 Strategy Phase: {result['phase']}")
    print(f"💰 Bid Decision: {result['bid']}")
    print(f"📝 Strategy: {result['strategy']}")
    
    # Test nomination scenario
    nom_context = {
        "remaining_budget": 90,
        "spent_budget": 110,
        "user_roster": {
            "QB": [],
            "RB": ["Jonathan Taylor", "Breece Hall"],
            "WR": ["Justin Jefferson"],
            "TE": [],
            "DEF": []
        },
        "slots_filled": 3,
        "slots_remaining": 12,
        "stars_acquired": 3
    }
    
    print("\n--- Nomination Test ---")
    result2 = await agent.get_bid_recommendation(nom_context)
    
    print(f"📊 Strategy Phase: {result2['phase']}")
    print(f"🎯 Nomination: {result2['nomination']}")
    print(f"📝 Strategy: {result2['strategy']}")


if __name__ == "__main__":
    asyncio.run(test_auction_agent())