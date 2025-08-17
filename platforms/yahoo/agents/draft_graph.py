"""
Yahoo Fantasy Draft Agent using LangGraph
Optimized for <3s response time with parallel execution and streaming
"""

import asyncio
import os
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
import json
from enum import Enum

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from langgraph.checkpoint import MemorySaver

# LangChain imports
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Local imports
from yahoo_client import YahooFantasyClient


# Define the state for our graph
class DraftState(TypedDict):
    """State that flows through the draft recommendation graph"""
    # Input context
    round: int
    pick_number: int
    user_roster: Dict[str, List]
    available_players: List[Dict]
    league_settings: Dict
    
    # Analysis results (populated in parallel)
    position_needs: Optional[Dict]
    player_valuations: Optional[List]
    scarcity_analysis: Optional[Dict]
    
    # Final output
    recommendations: Optional[List[Dict]]
    confidence_score: Optional[float]
    analysis_time_ms: Optional[int]


class AnalysisType(Enum):
    """Types of analysis we can run in parallel"""
    POSITION_NEEDS = "position_needs"
    PLAYER_VALUE = "player_value"
    SCARCITY = "scarcity"
    QUICK_PICK = "quick_pick"


class YahooDraftGraph:
    """
    LangGraph-based draft recommendation system
    Target: <3s response time for 95% of queries
    """
    
    def __init__(self, anthropic_api_key: str = None):
        """Initialize the draft graph"""
        self.api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        
        # Initialize LLMs - use different models for different tasks
        self.fast_llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            api_key=self.api_key,
            temperature=0.3,
            max_tokens=500
        )
        
        self.smart_llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022", 
            api_key=self.api_key,
            temperature=0.5,
            max_tokens=1000
        )
        
        # Build the graph
        self.graph = self._build_graph()
        
        # Compile with memory for session persistence
        self.memory = MemorySaver()
        self.app = self.graph.compile(checkpointer=self.memory)
        
        # Cache for pre-computed scenarios
        self.scenario_cache = {}
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(DraftState)
        
        # Add nodes
        workflow.add_node("check_cache", self.check_cache)
        workflow.add_node("parallel_analysis", self.parallel_analysis)
        workflow.add_node("synthesize", self.synthesize_recommendations)
        workflow.add_node("format_output", self.format_output)
        
        # Add edges with conditions
        workflow.add_conditional_edges(
            "check_cache",
            self.route_from_cache,
            {
                "cached": "format_output",
                "analyze": "parallel_analysis"
            }
        )
        
        workflow.add_edge("parallel_analysis", "synthesize")
        workflow.add_edge("synthesize", "format_output")
        workflow.add_edge("format_output", END)
        
        # Set entry point
        workflow.set_entry_point("check_cache")
        
        return workflow
    
    # -----------------
    # Graph Nodes
    # -----------------
    
    async def check_cache(self, state: DraftState) -> DraftState:
        """Check if we have a cached recommendation for this scenario"""
        cache_key = self._generate_cache_key(state)
        
        if cache_key in self.scenario_cache:
            cached = self.scenario_cache[cache_key]
            # Check if cache is fresh (< 30 seconds old)
            if (datetime.now() - cached["time"]).total_seconds() < 30:
                state["recommendations"] = cached["recommendations"]
                state["confidence_score"] = cached["confidence"]
                state["analysis_time_ms"] = 0  # Instant from cache
                return state
        
        return state
    
    async def parallel_analysis(self, state: DraftState) -> DraftState:
        """Run multiple analyses in parallel for speed"""
        start_time = datetime.now()
        
        # Create parallel runnables for each analysis
        parallel_tasks = RunnableParallel(
            position_needs=self._analyze_position_needs,
            player_values=self._analyze_player_values,
            scarcity=self._analyze_scarcity
        )
        
        # Execute all analyses in parallel
        results = await parallel_tasks.ainvoke({
            "roster": state["user_roster"],
            "available": state["available_players"][:50],  # Limit for speed
            "round": state["round"],
            "settings": state["league_settings"]
        })
        
        # Update state with results
        state["position_needs"] = results["position_needs"]
        state["player_valuations"] = results["player_values"]
        state["scarcity_analysis"] = results["scarcity"]
        
        # Track timing
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        state["analysis_time_ms"] = elapsed_ms
        
        return state
    
    async def synthesize_recommendations(self, state: DraftState) -> DraftState:
        """Synthesize all analyses into final recommendations"""
        
        # Use smart LLM for final synthesis
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a fantasy football draft expert.
            Synthesize the analyses into exactly 3 player recommendations.
            Be concise and decisive. Format as JSON array."""),
            HumanMessage(content=f"""
            Round {state['round']}, Pick {state['pick_number']}
            
            Position Needs: {json.dumps(state['position_needs'])}
            Top Values: {json.dumps(state['player_valuations'][:10])}
            Scarcity: {json.dumps(state['scarcity_analysis'])}
            
            Recommend exactly 3 players with format:
            [{{"name": "Player Name", "position": "POS", "reason": "Brief reason"}}]
            """)
        ])
        
        chain = prompt | self.smart_llm | JsonOutputParser()
        recommendations = await chain.ainvoke({})
        
        state["recommendations"] = recommendations
        state["confidence_score"] = self._calculate_confidence(state)
        
        # Cache the result
        self._update_cache(state)
        
        return state
    
    async def format_output(self, state: DraftState) -> DraftState:
        """Format final output for display"""
        # Output is already formatted in recommendations
        return state
    
    # -----------------
    # Analysis Functions (run in parallel)
    # -----------------
    
    async def _analyze_position_needs(self, data: Dict) -> Dict:
        """Quick position needs analysis using Haiku"""
        roster = data["roster"]
        
        # Count current positions
        counts = {
            "QB": len(roster.get("QB", [])),
            "RB": len(roster.get("RB", [])),
            "WR": len(roster.get("WR", [])),
            "TE": len(roster.get("TE", []))
        }
        
        # Determine needs based on Yahoo Full PPR settings
        needs = {
            "QB": "LOW" if counts["QB"] >= 1 else "HIGH",
            "RB": "HIGH" if counts["RB"] < 3 else "MEDIUM" if counts["RB"] < 5 else "LOW",
            "WR": "HIGH" if counts["WR"] < 3 else "MEDIUM" if counts["WR"] < 5 else "LOW",
            "TE": "HIGH" if counts["TE"] == 0 else "LOW"
        }
        
        return needs
    
    async def _analyze_player_values(self, data: Dict) -> List[Dict]:
        """Analyze player values using fast LLM"""
        available = data["available"]
        round_num = data["round"]
        
        # Quick value calculation
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="Rate players for Full PPR. Return JSON array."),
            HumanMessage(content=f"""
            Round {round_num}. Rate top 10 players by value:
            {json.dumps(available[:15])}
            
            Return: [{{"name": "Player", "value_score": 0-100}}]
            """)
        ])
        
        chain = prompt | self.fast_llm | JsonOutputParser()
        values = await chain.ainvoke({})
        
        return values
    
    async def _analyze_scarcity(self, data: Dict) -> Dict:
        """Analyze positional scarcity"""
        available = data["available"]
        
        # Count available by position
        position_counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}
        
        for player in available:
            pos = player.get("position", "")
            if pos in position_counts:
                position_counts[pos] += 1
        
        # Determine scarcity
        scarcity = {}
        for pos, count in position_counts.items():
            if count < 5:
                scarcity[pos] = "CRITICAL"
            elif count < 10:
                scarcity[pos] = "HIGH"
            elif count < 20:
                scarcity[pos] = "MEDIUM"
            else:
                scarcity[pos] = "LOW"
        
        return scarcity
    
    # -----------------
    # Helper Methods
    # -----------------
    
    def route_from_cache(self, state: DraftState) -> str:
        """Routing function to determine if we use cache or analyze"""
        if state.get("recommendations"):
            return "cached"
        return "analyze"
    
    def _generate_cache_key(self, state: DraftState) -> str:
        """Generate cache key from state"""
        roster = state["user_roster"]
        key_parts = [
            str(state["round"]),
            str(state["pick_number"]),
            str(len(roster.get("QB", []))),
            str(len(roster.get("RB", []))),
            str(len(roster.get("WR", []))),
            str(len(roster.get("TE", [])))
        ]
        return "_".join(key_parts)
    
    def _update_cache(self, state: DraftState):
        """Update scenario cache"""
        cache_key = self._generate_cache_key(state)
        self.scenario_cache[cache_key] = {
            "recommendations": state["recommendations"],
            "confidence": state["confidence_score"],
            "time": datetime.now()
        }
    
    def _calculate_confidence(self, state: DraftState) -> float:
        """Calculate confidence score based on analysis agreement"""
        # Simple confidence based on having all analyses
        confidence = 0.5
        
        if state.get("position_needs"):
            confidence += 0.2
        if state.get("player_valuations"):
            confidence += 0.2
        if state.get("scarcity_analysis"):
            confidence += 0.1
            
        return min(confidence, 1.0)
    
    # -----------------
    # Public Interface
    # -----------------
    
    async def get_recommendation(self, 
                                context: Dict,
                                stream: bool = False) -> Dict:
        """
        Get draft recommendation with <3s target latency
        
        Args:
            context: Draft context with roster, available players, etc.
            stream: Whether to stream results as they come in
            
        Returns:
            Dict with recommendations and metadata
        """
        start_time = datetime.now()
        
        # Convert context to DraftState
        state = DraftState(
            round=context.get("round", 1),
            pick_number=context.get("pick_number", 1),
            user_roster=context.get("user_roster", {}),
            available_players=context.get("available_players", []),
            league_settings=context.get("league_settings", {
                "scoring": "FULL_PPR",
                "positions": ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX"]
            }),
            position_needs=None,
            player_valuations=None,
            scarcity_analysis=None,
            recommendations=None,
            confidence_score=None,
            analysis_time_ms=None
        )
        
        # Run the graph
        if stream:
            # Stream results as they come in
            result = None
            async for event in self.app.astream(state):
                result = event
                # Could yield intermediate results here
        else:
            # Get final result only
            result = await self.app.ainvoke(state)
        
        # Calculate total time
        total_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return {
            "recommendations": result.get("recommendations", []),
            "confidence": result.get("confidence_score", 0),
            "analysis_time_ms": result.get("analysis_time_ms", 0),
            "total_time_ms": total_ms,
            "from_cache": result.get("analysis_time_ms", 1) == 0
        }


# Quick test function
async def test_yahoo_graph():
    """Test the Yahoo draft graph"""
    print("\n" + "="*60)
    print("TESTING YAHOO DRAFT GRAPH (LangGraph)")
    print("="*60)
    
    # Test context
    test_context = {
        "round": 5,
        "pick_number": 52,
        "user_roster": {
            "QB": ["Dak Prescott"],
            "RB": ["Christian McCaffrey", "Derrick Henry"],
            "WR": ["Justin Jefferson"],
            "TE": [],
            "K": [],
            "DEF": []
        },
        "available_players": [
            {"name": "Chris Olave", "position": "WR", "rank": 24},
            {"name": "Tua Tagovailoa", "position": "QB", "rank": 9},
            {"name": "Mark Andrews", "position": "TE", "rank": 4},
            {"name": "DeVonta Smith", "position": "WR", "rank": 28},
            {"name": "James Conner", "position": "RB", "rank": 30}
        ],
        "league_settings": {
            "scoring": "FULL_PPR"
        }
    }
    
    # Initialize graph
    graph = YahooDraftGraph()
    
    # Test multiple times to check cache
    for i in range(3):
        print(f"\n--- Test {i+1} ---")
        start = datetime.now()
        
        result = await graph.get_recommendation(test_context)
        
        elapsed = (datetime.now() - start).total_seconds()
        
        print(f"⏱️ Total Time: {elapsed:.2f}s")
        print(f"📊 Analysis Time: {result['analysis_time_ms']}ms")
        print(f"💾 From Cache: {result['from_cache']}")
        print(f"🎯 Confidence: {result['confidence']:.1%}")
        print(f"\n📋 Recommendations:")
        for j, rec in enumerate(result['recommendations'], 1):
            print(f"  {j}. {rec['name']} ({rec['position']}) - {rec['reason']}")
        
        if elapsed < 3:
            print("✅ Target latency achieved!")
        else:
            print("⚠️ Over 3 second target")


if __name__ == "__main__":
    asyncio.run(test_yahoo_graph())