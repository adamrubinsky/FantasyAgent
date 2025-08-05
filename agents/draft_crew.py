"""
Fantasy Football Draft Assistant - CrewAI Multi-Agent System
Based on original brainstorming architecture with 4 specialized agents
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM

from core.mcp_integration import MCPClient
from api.sleeper_client import SleeperClient
from core.league_context import league_manager


# Helper function to get live rankings data for agents
async def get_live_rankings_data(position: str = "ALL", limit: int = 50) -> str:
    """
    Fetch current FantasyPros rankings for agents to use in analysis
    
    This function connects to the MCP (Model Context Protocol) server to retrieve
    live fantasy football rankings data. This ensures agents use current rankings
    rather than outdated training data.
    
    Args:
        position: Filter by position ("QB", "RB", "WR", "TE", "K", "DST", or "ALL")
        limit: Maximum number of players to return (default 50)
        
    Returns:
        Formatted string containing live rankings data for agent consumption
        Format: "Player Name (Position) - Rank: X, ADP: Y, Team: Z"
        
    Raises:
        Exception: If MCP server connection fails or data retrieval errors
    """
    try:
        # Create async connection to MCP server for live data
        async with MCPClient() as mcp:
            # Fetch current rankings from FantasyPros via MCP
            rankings = await mcp.get_rankings(limit=limit)
            
            # Filter by position if user requested specific position
            if position != "ALL":
                filtered_players = []
                for player in rankings.get('players', []):
                    # Match exact position (case-sensitive)
                    if player.get('position') == position:
                        filtered_players.append(player)
                # Replace full rankings with filtered subset
                rankings['players'] = filtered_players[:limit]
            
            # Format rankings data for agent consumption
            # Create human-readable list of players with key metrics
            players_data = []
            for player in rankings.get('players', []):
                # Extract player information with fallbacks for missing data
                name = player.get('name', 'Unknown')
                pos = player.get('position', 'Unknown') 
                rank = player.get('rank', 'N/A')
                adp = player.get('adp', 'N/A')
                team = player.get('team', 'N/A')
                
                # Format as readable string for agent to parse
                player_info = f"{name} ({pos}) - Rank: {rank}, ADP: {adp}, Team: {team}"
                players_data.append(player_info)
            
            # Return formatted string with header for agent context
            return f"LIVE RANKINGS ({position}):\n" + "\n".join(players_data[:limit])
            
    except Exception as e:
        return f"Error getting live rankings: {str(e)}"

async def get_player_projections_data(player_names: List[str]) -> str:
    """Get player projections data for agents to use"""
    try:
        async with MCPClient() as mcp:
            projections = await mcp.get_projections(player_names)
            
            # Format for agent consumption
            if 'players' in projections:
                output = []
                for name, data in projections['players'].items():
                    output.append(f"{name}: {data}")
                return "LIVE PLAYER PROJECTIONS:\n" + "\n".join(output)
            else:
                return f"No projections found for: {', '.join(player_names)}"
                
    except Exception as e:
        return f"Error getting player projections: {str(e)}"


class FantasyDraftCrew:
    """
    CrewAI-powered multi-agent system for fantasy football draft assistance
    
    Implements the original 4-agent architecture:
    1. Data Collector Agent - Fetches live draft/player data + rankings
    2. Analysis Agent - Evaluates players based on stats/projections  
    3. Strategy Agent - Considers league settings and roster construction
    4. Recommendation Agent - Synthesizes final pick suggestions
    """
    
    def __init__(self, anthropic_api_key: str = None):
        """
        Initialize the draft crew with all specialized agents
        
        Args:
            anthropic_api_key: Claude API key for agents
        """
        self.api_key = anthropic_api_key
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required for CrewAI agents")
        
        # Configure LLM for all agents
        self.llm = LLM(
            model="claude-3-5-sonnet-20241022",  # Working model
            api_key=self.api_key,
            base_url="https://api.anthropic.com"
        )
        
        # Initialize data clients
        self.sleeper_client = SleeperClient()
        self.mcp_client = None  # Will be created per task
        
        # Create specialized agents
        self.agents = self._create_agents()
        
        # Track conversation context
        self.session_context = {
            "draft_picks": [],
            "available_players": [],
            "user_roster": [],
            "league_context": None
        }
    
    # Remove tools method since we're handling data differently
    
    def _create_agents(self) -> Dict[str, Agent]:
        """Create the four specialized agents"""
        
        # 1. Data Collector Agent - Fetches live data
        data_collector = Agent(
            role="Data Collector",
            goal="Fetch and organize real-time fantasy football data from multiple sources",
            backstory="""You are an expert data collector specializing in fantasy football.
            Your job is to gather the most current information from Sleeper API, FantasyPros 
            rankings, and other sources. You excel at organizing data efficiently and 
            identifying what information is most relevant for draft decisions.
            
            IMPORTANT: You will be provided with live current rankings data. 
            Use this fresh data rather than your training data for accuracy!""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        # 2. Analysis Agent - Evaluates players
        analysis_agent = Agent(
            role="Player Analyst",
            goal="Analyze player performance, projections, and value opportunities",
            backstory="""You are a fantasy football analytics expert with deep knowledge 
            of player performance metrics, statistical trends, and projection models. 
            You excel at identifying undervalued players, injury risks, and performance 
            trends that impact fantasy value.
            
            Use the provided live rankings and projections data to supplement your analysis.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        # 3. Strategy Agent - Considers league settings and roster construction
        strategy_agent = Agent(
            role="Draft Strategist", 
            goal="Develop optimal draft strategy based on league settings and roster needs",
            backstory="""You are a fantasy football draft strategy expert who understands 
            the nuances of different league formats. You excel at SUPERFLEX strategy, 
            positional scarcity analysis, and roster construction. You know when to reach 
            for QBs in SUPERFLEX and how to build balanced rosters.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        # 4. Recommendation Agent - Synthesizes final suggestions
        recommendation_agent = Agent(
            role="Draft Advisor",
            goal="Synthesize all analysis into clear, actionable draft recommendations",
            backstory="""You are the final decision maker who takes input from the data 
            collector, analyst, and strategist to provide clear, confident draft 
            recommendations. You excel at weighing multiple factors and presenting 
            easy-to-understand advice with clear reasoning.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        return {
            "data_collector": data_collector,
            "analyst": analysis_agent,
            "strategist": strategy_agent,
            "advisor": recommendation_agent
        }
    
    async def analyze_draft_question(self, question: str, context: Dict[str, Any] = None) -> str:
        """
        Process any draft-related question through the multi-agent workflow
        
        Args:
            question: User's question about draft strategy
            context: Additional context (draft position, available players, etc.)
            
        Returns:
            Comprehensive analysis and recommendations from the agent crew
        """
        # Update session context
        if context:
            self.session_context.update(context)
        
        # Add league context
        league_context = league_manager.get_current_context()
        if league_context:
            self.session_context["league_context"] = {
                "name": league_context.league_name,
                "scoring": league_context.scoring_format,
                "teams": league_context.total_teams,
                "superflex": league_context.is_superflex,
                "qb_spots": league_context.total_qb_spots,
                "roster_positions": league_context.roster_positions
            }
        
        # Create tasks for each agent
        tasks = await self._create_tasks_for_question(question)
        
        # Create and run the crew
        crew = Crew(
            agents=[
                self.agents["data_collector"],
                self.agents["analyst"], 
                self.agents["strategist"],
                self.agents["advisor"]
            ],
            tasks=tasks,
            process=Process.sequential,  # Run agents in sequence
            verbose=True
        )
        
        try:
            # Execute the crew workflow
            result = crew.kickoff()
            return str(result)
        except Exception as e:
            return f"❌ CrewAI Error: {str(e)}\\n\\nFalling back to basic analysis..."
    
    async def _create_tasks_for_question(self, question: str) -> List[Task]:
        """Create specific tasks for each agent based on the question"""
        
        context_str = json.dumps(self.session_context, indent=2)
        
        # Get live data for agents to use
        live_rankings = await get_live_rankings_data(limit=100)
        
        # Extract player names from question for specific projections
        player_names = []
        for word in question.split():
            # Simple heuristic to find player names (capitalized words)
            if len(word) > 2 and word[0].isupper() and word.isalpha():
                player_names.append(word)
        
        live_projections = ""
        if player_names:
            live_projections = await get_player_projections_data(player_names)
        
        # Task 1: Data Collection
        data_task = Task(
            description=f"""
            Collect current fantasy football data relevant to this question: "{question}"
            
            Current context: {context_str}
            
            LIVE CURRENT DATA:
            {live_rankings}
            
            {live_projections}
            
            Your tasks:
            1. Use the LIVE DATA provided above (not your training data)
            2. Identify what specific players or positions are relevant to the question
            3. Extract relevant rankings and projections from the live data
            4. Note any league-specific settings that matter
            5. Organize the current data for analysis
            
            Focus on factual data collection using the live rankings provided.
            """,
            agent=self.agents["data_collector"],
            expected_output="Organized data summary using live rankings and projections data"
        )
        
        # Task 2: Player Analysis  
        analysis_task = Task(
            description=f"""
            Analyze the players and scenarios relevant to: "{question}"
            
            Use the data collected by the Data Collector to:
            1. Evaluate player performance trends and projections
            2. Identify value opportunities based on ADP vs current rankings
            3. Assess injury risks and reliability factors
            4. Compare players mentioned in the question
            
            Focus on analytical insights - no strategy or final recommendations yet.
            """,
            agent=self.agents["analyst"],
            expected_output="Detailed player analysis with performance metrics, value assessment, and risk evaluation"
        )
        
        # Task 3: Strategy Development
        strategy_task = Task(
            description=f"""
            Develop draft strategy recommendations for: "{question}"
            
            Consider the data and analysis provided to:
            1. Factor in league settings (especially SUPERFLEX impact)
            2. Assess positional needs and scarcity
            3. Evaluate roster construction priorities
            4. Consider timing and future draft strategy
            
            Focus on strategic thinking - build on the analysis but don't make final pick recommendations yet.
            """,
            agent=self.agents["strategist"],
            expected_output="Strategic analysis with positional priorities, timing considerations, and roster construction approach"
        )
        
        # Task 4: Final Recommendation
        recommendation_task = Task(
            description=f"""
            Provide final recommendations for: "{question}"
            
            Synthesize all previous work to:
            1. Give clear, actionable recommendations
            2. Explain the reasoning behind each suggestion
            3. Address the original question directly
            4. Provide 2-3 specific options with pros/cons
            
            This is the final output the user will see - make it clear and confident.
            """,
            agent=self.agents["advisor"],
            expected_output="Clear, actionable draft recommendations with reasoning and multiple options"
        )
        
        return [data_task, analysis_task, strategy_task, recommendation_task]
    
    async def compare_players(self, player1: str, player2: str, context: Dict[str, Any] = None) -> str:
        """
        Compare two players using the multi-agent system
        
        Args:
            player1: First player name
            player2: Second player name  
            context: Additional context
            
        Returns:
            Detailed comparison with recommendation
        """
        question = f"Compare {player1} vs {player2} for my draft. Who should I pick and why?"
        return await self.analyze_draft_question(question, context)
    
    async def get_draft_recommendation(self, current_pick: int, context: Dict[str, Any] = None) -> str:
        """
        Get draft recommendation for current pick using multi-agent system
        
        Args:
            current_pick: Current draft pick number
            context: Additional context
            
        Returns:
            Draft recommendation with reasoning
        """
        question = f"What player should I draft with pick #{current_pick}? Give me your top 3 recommendations with reasoning."
        
        if context is None:
            context = {}
        context["current_pick"] = current_pick
        
        return await self.analyze_draft_question(question, context)
    
    async def analyze_position_strategy(self, position: str, context: Dict[str, Any] = None) -> str:
        """
        Analyze strategy for a specific position
        
        Args:
            position: Position to analyze (QB, RB, WR, TE)
            context: Additional context
            
        Returns:
            Position-specific strategy analysis
        """
        question = f"What's my strategy for drafting {position}s in this league? When should I target them and who are the best values?"
        return await self.analyze_draft_question(question, context)


# Test function
async def test_crew():
    """Test the CrewAI system"""
    from dotenv import load_dotenv
    import os
    
    load_dotenv('.env.local')
    load_dotenv()
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your-claude-api-key-here':
        print("❌ Please add your ANTHROPIC_API_KEY to .env.local first!")
        return
    
    print("🤖 Testing CrewAI Multi-Agent System...")
    
    try:
        crew = FantasyDraftCrew(anthropic_api_key=api_key)
        
        # Test basic question
        response = await crew.analyze_draft_question(
            "Should I draft Josh Allen in the first round of my SUPERFLEX league?"
        )
        
        print("✅ CrewAI Response:")
        print(response)
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_crew())