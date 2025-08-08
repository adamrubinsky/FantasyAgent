"""
Fantasy Football Draft Assistant - CrewAI Multi-Agent System
Based on original brainstorming architecture with 4 specialized agents
"""

import asyncio
import json
import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM

from core.mcp_integration import MCPClient
from api.sleeper_client import SleeperClient
from core.league_context import league_manager


# Helper function to get live rankings data for agents
async def get_cached_rankings_data(position: str = "ALL", limit: int = 50, cache_minutes: int = 5) -> str:
    """Cached version of live rankings data to reduce API calls during rapid queries"""
    import time
    
    cache_key = f"{position}_{limit}"
    current_time = time.time()
    
    # Check if we have cached data that's still fresh
    if (hasattr(get_cached_rankings_data, '_cache') and 
        cache_key in get_cached_rankings_data._cache):
        
        cached_data, cache_time = get_cached_rankings_data._cache[cache_key]
        if current_time - cache_time < (cache_minutes * 60):
            print(f"📍 Using cached rankings data ({position}, limit={limit})")
            return cached_data
    
    # Fetch fresh data
    print(f"🔄 Fetching fresh rankings data ({position}, limit={limit})")
    fresh_data = await get_live_rankings_data(position, limit)
    
    # Cache the result
    if not hasattr(get_cached_rankings_data, '_cache'):
        get_cached_rankings_data._cache = {}
    get_cached_rankings_data._cache[cache_key] = (fresh_data, current_time)
    
    return fresh_data

def get_sync_rankings_fallback() -> str:
    """
    Synchronous fallback to get current rankings from FantasyPros API
    This bypasses the async event loop issue and gets real current data
    """
    import requests
    import os
    
    # Load environment variables from .env.local
    from dotenv import load_dotenv
    load_dotenv('.env.local')  # Load from .env.local first
    load_dotenv()  # Then load from .env as fallback
    
    # Check if we have API key
    api_key = os.getenv('FANTASYPROS_API_KEY')
    if not api_key:
        print("⚠️ No FantasyPros API key found in .env.local or .env")
        return "ERROR: No FantasyPros API key configured. Please set FANTASYPROS_API_KEY in .env.local"
    
    # TEMPORARY: Remove forced failure for testing (can be removed later)
    # print("🧪 TESTING: Forcing FantasyPros API failure to test Sleeper fallback")
    # return "ERROR: Forced API failure for testing"
    
    try:
        # Call FantasyPros API using correct parameters from official documentation
        from datetime import datetime
        current_year = datetime.now().year
        
        # According to the API docs, the correct URL structure is:
        # https://api.fantasypros.com/public/v2/json/{sport}/{season}/consensus-rankings
        url = f"https://api.fantasypros.com/public/v2/json/nfl/{current_year}/consensus-rankings"
        
        # Parameters must use uppercase values per API documentation
        # CRITICAL: Use 'OP' (Offensive Player) position to get SUPERFLEX rankings!
        # This properly values QBs high while including all offensive positions
        params = {
            'position': 'OP',       # OP = Offensive Player = SUPERFLEX rankings!
            'scoring': 'HALF',      # HALF for Half-PPR (uppercase required)
            'type': 'DRAFT',        # DRAFT for draft rankings (must be uppercase)
            'week': 0               # 0 for season-long rankings
        }
        headers = {
            'x-api-key': api_key,   # API key goes in header, not query params
            'User-Agent': 'FantasyAgent/1.0',
            'Accept': 'application/json'
        }
        
        print(f"🔗 Trying URL: {url}")
        print(f"📋 Params: {params}")
        
        print(f"🔄 Fetching live FantasyPros SUPERFLEX rankings...")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            rankings = []
            
            # Parse the actual FantasyPros API response structure
            for player in data.get('players', []):
                # Extract fields using correct field names from API
                name = player.get('player_name', 'Unknown')
                pos = player.get('player_position_id', 'Unknown')  # Correct field name
                team = player.get('player_team_id', 'Unknown')     # Correct field name
                rank = player.get('rank_ecr', 999)                 # ECR (Expert Consensus Ranking)
                
                # Calculate rough ADP from average rank
                rank_ave = float(player.get('rank_ave', rank))
                
                rankings.append(f"{name} ({pos}) - Rank: {rank}, ADP: {rank_ave:.1f}, Team: {team}")
            
            print(f"✅ Retrieved {len(rankings)} live FantasyPros SUPERFLEX rankings")
            
            # SUCCESS: Using 'OP' position gives us true SUPERFLEX rankings!
            # QBs are properly valued high, WRs like Tyreek Hill at correct spots
            return "LIVE FANTASYPROS SUPERFLEX HALF-PPR RANKINGS:\n" + "\n".join(rankings)
        
        else:
            print(f"❌ FantasyPros API error: {response.status_code}")
            return f"ERROR: FantasyPros API returned {response.status_code}"
            
    except Exception as e:
        print(f"❌ Failed to fetch live FantasyPros data: {e}")
        return f"ERROR: Failed to fetch live rankings - {str(e)}"

def get_sleeper_rankings_fallback() -> str:
    """
    Fallback to get current player rankings from Sleeper API
    This provides a reliable backup when FantasyPros API is unavailable
    """
    try:
        import requests
        import asyncio
        from api.sleeper_client import SleeperClient
        
        print("🔄 Fetching live rankings from Sleeper API as fallback...")
        
        # Use Sleeper client to get all players
        sleeper_client = SleeperClient()
        
        # Create a new event loop for this synchronous fallback
        # Since we might be called from within an existing async context
        try:
            # Try to run in current event loop if it exists
            players_task = sleeper_client.get_all_players()
            players = asyncio.run(players_task)
        except RuntimeError:
            # If we're already in an async context, use the current loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new thread for the async operation
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, sleeper_client.get_all_players())
                    players = future.result(timeout=10)
            else:
                players = loop.run_until_complete(sleeper_client.get_all_players())
        
        if not players:
            return "ERROR: Could not fetch players from Sleeper API"
        
        # Filter to current active NFL players with fantasy relevance
        # Sleeper provides search_rank which indicates fantasy relevance
        active_players = []
        for player_id, player_data in players.items():
            # Filter criteria for current fantasy-relevant players
            if (player_data.get('active') == True and 
                player_data.get('sport') == 'nfl' and
                player_data.get('fantasy_positions') and
                player_data.get('search_rank') is not None):
                
                # Only include standard fantasy positions
                positions = player_data.get('fantasy_positions', [])
                standard_positions = {'QB', 'RB', 'WR', 'TE', 'K', 'DEF'}
                if any(pos in standard_positions for pos in positions):
                    
                    # Additional filter: must have a current team (exclude free agents and retired players)
                    team = player_data.get('team')
                    if team and team != 'None' and team != '':
                        # Also exclude players with very high search_rank (likely retired/inactive)
                        search_rank = player_data.get('search_rank', 9999)
                        if search_rank < 1000:  # Only include reasonably ranked players
                            active_players.append((player_id, player_data))
        
        # Sort by Sleeper's search_rank (lower is better, like ADP)
        active_players.sort(key=lambda x: x[1].get('search_rank', 9999))
        
        # Take top 300 players for full draft coverage
        top_players = active_players[:300]
        
        # Format for agent consumption (same format as FantasyPros)
        rankings = []
        for i, (player_id, player) in enumerate(top_players, 1):
            name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
            if not name or name == ' ':
                name = 'Unknown Player'
            
            # Get primary position
            positions = player.get('fantasy_positions', [])
            pos = positions[0] if positions else 'Unknown'
            
            # Use search_rank as ADP equivalent
            search_rank = player.get('search_rank', i * 10)
            team = player.get('team', 'FA')
            
            ranking_line = f"{name} ({pos}) - Rank: {i}, ADP: {search_rank}, Team: {team}"
            rankings.append(ranking_line)
        
        print(f"✅ Retrieved {len(rankings)} live Sleeper player rankings")
        return "LIVE SLEEPER RANKINGS (FALLBACK):\n" + "\n".join(rankings)
        
    except Exception as e:
        print(f"❌ Sleeper fallback also failed: {e}")
        return f"ERROR: Both FantasyPros and Sleeper APIs failed - {str(e)}"

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
            
            # Handle different response formats
            players_list = []
            if isinstance(rankings, list):
                # Direct list format
                players_list = rankings
            elif isinstance(rankings, dict) and 'players' in rankings:
                # Dict with players key
                players_list = rankings['players']
            else:
                return f"Error: Unexpected rankings format: {type(rankings)}"
            
            # Format rankings data for agent consumption
            # Create human-readable list of players with key metrics
            players_data = []
            for player in players_list[:limit]:
                if isinstance(player, dict):
                    # Extract player information with fallbacks for missing data
                    name = player.get('name', player.get('player_name', 'Unknown'))
                    pos = player.get('position', player.get('pos', 'Unknown'))
                    rank = player.get('rank', player.get('overall_rank', 'N/A'))
                    adp = player.get('adp', 'N/A')
                    team = player.get('team', 'N/A')
                    
                    # Format as readable string for agent to parse
                    player_info = f"{name} ({pos}) - Rank: {rank}, ADP: {adp}, Team: {team}"
                    players_data.append(player_info)
            
            # Return formatted string with header for agent context
            return f"LIVE RANKINGS ({position}):\n" + "\n".join(players_data)
            
    except Exception as e:
        print(f"❌ MCP rankings failed: {e}")
        print("🔄 Attempting direct FantasyPros API call...")
        fallback_result = get_sync_rankings_fallback()
        
        # If API call failed, fall back to Sleeper rankings
        if "ERROR:" in fallback_result:
            print("⚠️ FantasyPros API unavailable, falling back to Sleeper rankings")
            return get_sleeper_rankings_fallback()
        else:
            return fallback_result

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
        
        # Configure LLM for all agents - litellm needs specific format for Anthropic
        # CRITICAL: Set environment variable - CrewAI/litellm ignores api_key parameter!
        os.environ["ANTHROPIC_API_KEY"] = self.api_key
        
        # Use Claude Sonnet 4 (latest model available as of May 2025)
        # Note: Do NOT pass api_key parameter - it's ignored and causes auth errors
        self.llm = LLM(
            model="claude-sonnet-4-20250514",  # Claude 4 Sonnet - no anthropic/ prefix needed
            temperature=0.7,
            max_tokens=4000
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
            "league_context": None,
            "draft_id": None,
            "user_roster_id": None,
            "current_pick": 1,
            "picks_until_user": None,
            "proactive_recommendations": {},
            "last_proactive_pick": None
        }
        
        # Draft monitoring state
        self.draft_active = False
        self.last_pick_count = 0
        
        # Performance caching - optimized for speed
        self._cached_rankings = None
        self._cache_timestamp = None
        self._cache_ttl = 180  # 3 minutes for faster updates
    
    # Remove tools method since we're handling data differently
    
    def _create_agents(self) -> Dict[str, Agent]:
        """Create the five specialized agents including draft monitor"""
        
        # 1. Draft Monitor Agent - NEW: Tracks live draft state
        draft_monitor = Agent(
            role="Draft Monitor",
            goal="Track live draft picks, available players, and draft context in real-time",
            backstory="""You are a specialized draft monitoring agent who tracks every pick 
            as it happens in real-time. You know exactly which players have been drafted, 
            who's still available, whose turn it is, and how many picks until the user's turn.
            
            You excel at providing current draft context to other agents, tracking positional 
            runs, and identifying when key players are being taken off the board. You're the 
            "eyes and ears" of the draft room.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        # 2. Data Collector Agent - Fetches live rankings data
        data_collector = Agent(
            role="Data Collector", 
            goal="Fetch and organize real-time fantasy football rankings and player data",
            backstory="""You are an expert data collector specializing in fantasy football.
            Your job is to gather the most current information from FantasyPros rankings,
            player projections, and other sources. You work closely with the Draft Monitor
            to understand which players are still available.
            
            IMPORTANT: You will be provided with live current rankings data. 
            Use this fresh data rather than your training data for accuracy!""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        # 3. Analysis Agent - Evaluates players
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
        
        # 4. Strategy Agent - Considers league settings and roster construction
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
        
        # 5. Recommendation Agent - Synthesizes final suggestions
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
            "draft_monitor": draft_monitor,
            "data_collector": data_collector,
            "analyst": analysis_agent,
            "strategist": strategy_agent,
            "advisor": recommendation_agent
        }
    
    async def analyze_draft_question(self, question: str, context: Dict[str, Any] = None) -> str:
        """
        Process any draft-related question through the multi-agent workflow
        
        OPTIMIZED VERSION: Reduced complexity, faster execution, smart caching
        
        Args:
            question: User's question about draft strategy
            context: Additional context (draft position, available players, etc.)
            
        Returns:
            Comprehensive analysis and recommendations from the agent crew
        """
        # Update session context
        if context:
            self.session_context.update(context)
        
        # If we have an active draft connection, update with live data
        if self.draft_active:
            await self.update_draft_state()
        
        # Add league context (cached)
        league_context = league_manager.get_current_context()
        if league_context:
            self.session_context["league_context"] = {
                "name": league_context.league_name,
                "scoring": league_context.scoring_format,
                "teams": league_context.total_teams,
                "superflex": league_context.is_superflex,
                "qb_spots": league_context.total_qb_spots
            }
        
        # Try fast single-agent approach first for simple questions
        if self._is_simple_question(question):
            return await self._handle_simple_question(question)
        
        # Use full multi-agent workflow for complex questions
        try:
            tasks = await self._create_optimized_tasks(question)
            
            crew = Crew(
                agents=[
                    self.agents["data_collector"],
                    self.agents["analyst"], 
                    self.agents["strategist"],
                    self.agents["advisor"]
                ],
                tasks=tasks,
                process=Process.sequential,
                verbose=False  # Reduce output for speed
            )
            
            # Set shorter timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("CrewAI execution timed out")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(25)  # 25 second timeout for speed
            
            try:
                result = crew.kickoff()
                signal.alarm(0)  # Cancel timeout
                return str(result)
            except TimeoutError:
                signal.alarm(0)
                return await self._handle_simple_question(question)
                
        except Exception as e:
            print(f"⚠️ Multi-agent workflow failed: {e}")
            return await self._handle_simple_question(question)
    
    def _is_simple_question(self, question: str) -> bool:
        """Determine if question can be handled by single agent for speed"""
        simple_patterns = [
            "who should i draft",
            "what should i draft",
            "my next pick",
            "vs",  # player comparisons
            "better",
            "pick between",
            "recommend",
            "rankings",
            "tier",
            "tee higgins",
            "jayden daniels", 
            "josh allen",
            "lamar jackson"
        ]
        
        question_lower = question.lower()
        # Most questions are simple for speed - only use complex multi-agent for very specific scenarios
        is_simple = any(pattern in question_lower for pattern in simple_patterns)
        
        # Override: Always treat as simple if it's asking about recommendations
        if any(word in question_lower for word in ["recommend", "draft", "pick", "should"]):
            is_simple = True
            
        return is_simple
    
    async def _handle_simple_question(self, question: str) -> str:
        """Fast single-agent response for simple questions"""
        print("🚀 Using optimized single-agent response...")
        
        try:
            # Get SUPERFLEX rankings (cached for 5 minutes) - reduced for speed
            raw_live_data = await get_cached_rankings_data(position="ALL", limit=30)  # Get more, then filter
            
            # Get draft context if available
            draft_context = ""
            if self.draft_active:
                draft_picks = self.session_context.get('draft_picks', [])
                available_players = self.session_context.get('available_players', [])
                current_pick = self.session_context.get('current_pick', 1)
                user_next_pick = self.session_context.get('user_next_pick')
                picks_until_user = self.session_context.get('picks_until_user')
                # Get user's actual Sleeper user ID from draft info
                # The user_roster_id from the web interface needs to be converted to the actual Sleeper user ID
                user_roster_id = self.session_context.get('user_roster_id')
                user_sleeper_id = None
                
                # Get draft info to map roster_id to actual Sleeper user ID
                draft_id = self.session_context.get('draft_id')
                if draft_id and user_roster_id:
                    try:
                        import requests
                        draft_info_response = requests.get(f"https://api.sleeper.app/v1/draft/{draft_id}")
                        if draft_info_response.status_code == 200:
                            draft_info = draft_info_response.json()
                            # The draft_order maps user_id to draft_slot, we need to find the user_id for our roster_id
                            draft_order = draft_info.get('draft_order', {})
                            for sleeper_user_id, draft_slot in draft_order.items():
                                if draft_slot == user_roster_id:
                                    user_sleeper_id = sleeper_user_id
                                    break
                    except Exception as e:
                        print(f"⚠️ Could not fetch draft info for user ID mapping: {e}")
                
                # Filter user's picks using the correct Sleeper user ID
                # Sleeper uses 'picked_by' field, not 'roster_id', for identifying who made each pick
                if user_sleeper_id:
                    user_roster = [pick for pick in draft_picks if pick.get('picked_by') == user_sleeper_id]
                    print(f"✅ Found {len(user_roster)} picks for user (Sleeper ID: {user_sleeper_id})")
                else:
                    # Fallback to the original logic if we can't map the IDs
                    user_roster = [pick for pick in draft_picks if pick.get('roster_id') == user_roster_id]
                    print(f"⚠️ Using fallback roster_id filtering, found {len(user_roster)} picks")
                
                # Extract drafted player IDs from Sleeper draft picks 
                # Sleeper API provides player_id directly in each draft pick
                drafted_sleeper_ids = set()
                for pick in draft_picks:
                    sleeper_player_id = pick.get('player_id')
                    if sleeper_player_id:
                        drafted_sleeper_ids.add(str(sleeper_player_id))
                
                # Use our unified player mapping system for robust filtering
                # This solves the core issue of ID mismatches between platforms
                from utils.player_mapping import player_mapper
                
                # Filter available players using the mapping system
                # This will properly exclude drafted players by cross-referencing
                # Sleeper IDs (from draft picks) with FantasyPros data (rankings)
                truly_available = player_mapper.filter_available_players(
                    all_players=available_players,
                    drafted_sleeper_ids=drafted_sleeper_ids
                )
                
                # Filter out IDP positions - only keep standard fantasy positions
                # This prevents AI from recommending individual defensive players
                standard_fantasy_positions = {'QB', 'RB', 'WR', 'TE', 'K', 'DST'}
                fantasy_eligible = []
                
                for player in truly_available:
                    position = player.get('position', '')
                    # Include players with standard fantasy positions only
                    if position in standard_fantasy_positions:
                        fantasy_eligible.append(player)
                
                # Update truly_available to only include fantasy-eligible positions
                before_idp_filter = len(truly_available)
                truly_available = fantasy_eligible
                print(f"🏈 IDP Filter: {before_idp_filter} → {len(truly_available)} players (removed {before_idp_filter - len(truly_available)} IDP)")
                
                # Debug output to track filtering effectiveness
                print(f"🔍 Drafted Sleeper IDs ({len(drafted_sleeper_ids)}): {list(drafted_sleeper_ids)[:5]}")
                print(f"📊 Draft picks count: {len(draft_picks)}")
                print(f"📊 Available players before filtering: {len(available_players)}")
                print(f"📊 Available players after filtering: {len(truly_available)}")
                print(f"📍 Current pick: {current_pick}, User next pick: {user_next_pick}")
                print(f"👤 User roster: {len(user_roster)} picks")
                
                # Debug the filtering effectiveness by showing which players remain
                if truly_available:
                    sample_names = [p.get('player_name', p.get('name', 'Unknown')) for p in truly_available[:5]]
                    print(f"🔍 First 5 truly available players: {sample_names}")
                else:
                    print("⚠️ No players remain after filtering - this indicates a problem!")
                
                # Show player mapping statistics for debugging
                mapping_stats = player_mapper.get_stats()
                print(f"🎯 Player mapping stats: {mapping_stats['fantasypros_matched']}/{mapping_stats['total_players']} matched ({mapping_stats['match_rate']:.1f}%)")
                
                # Filter the text-based rankings data to exclude drafted players
                # This creates the formatted text that the AI agent will read and analyze
                if raw_live_data and "LIVE RANKINGS" in raw_live_data:
                    lines = raw_live_data.split('\n')[1:]  # Skip the header line
                    filtered_lines = []
                    
                    # Process each ranking line to check if the player has been drafted AND is fantasy-eligible
                    standard_fantasy_positions = {'QB', 'RB', 'WR', 'TE', 'K', 'DST'}
                    
                    for line in lines:
                        if ' (' in line:
                            # Extract player name and position from line format: "Name (POS) - Rank: X, ADP: Y, Team: Z"
                            player_name = line.split(' (')[0].strip()
                            position_part = line.split(' (')[1].split(')')[0]
                            
                            # Skip IDP positions - only include standard fantasy positions
                            if position_part not in standard_fantasy_positions:
                                continue
                            
                            # Use our player mapping to check if this player has been drafted
                            # This provides robust checking across platform ID mismatches
                            player_data = player_mapper.get_player_by_name(player_name)
                            
                            # If we found the player and they haven't been drafted, include them
                            if player_data:
                                sleeper_id = player_data.get('sleeper_id')
                                if sleeper_id not in drafted_sleeper_ids:
                                    filtered_lines.append(line)
                            else:
                                # If not in our mapping, include by default (might be newer player)
                                # This prevents losing players due to incomplete mapping data
                                filtered_lines.append(line)
                    
                    # Create the formatted text data that the AI will read
                    live_data = "AVAILABLE PLAYERS (EXCLUDING DRAFTED):\n" + "\n".join(filtered_lines[:15])
                    print(f"🎯 Text filtering: {len(filtered_lines)} available from {len(lines)} total")
                else:
                    live_data = raw_live_data
                
                user_turn_info = ""
                if user_next_pick:
                    if picks_until_user == 0:
                        user_turn_info = f"🚨 YOUR TURN NOW! (Pick #{user_next_pick})"
                    elif picks_until_user is not None and picks_until_user <= 3:
                        user_turn_info = f"⏰ Your next pick: #{user_next_pick} ({picks_until_user} picks away)"
                    else:
                        user_turn_info = f"📍 Your next pick: #{user_next_pick}"
                
                draft_context = f"""
                LIVE DRAFT CONTEXT:
                • Overall Pick: #{current_pick} 
                • {user_turn_info}
                • Your Picks So Far: {len(user_roster)}
                • Truly Available Players: {len(truly_available)} (excluding drafted)
                
                Your Current Roster: {', '.join([f"{(p.get('metadata', {}).get('first_name', '') + ' ' + p.get('metadata', {}).get('last_name', '')).strip() or 'Unknown'} ({p.get('metadata', {}).get('position', '?')})" for p in user_roster]) if user_roster else 'None yet'}
                
                Position Summary: {self._get_roster_position_summary(user_roster) if user_roster else 'No picks yet - recommend based on SUPERFLEX value'}
                
                Bye Week Analysis: {self._get_bye_week_analysis(user_roster, truly_available).get('message', 'N/A') if user_roster else 'No roster yet'}
                
                Recently Drafted: {', '.join([f"{(p.get('metadata', {}).get('first_name', '') + ' ' + p.get('metadata', {}).get('last_name', '')).strip() or 'Unknown'} (Pick {p.get('pick_no')})" for p in draft_picks[-3:]]) if draft_picks else 'None yet'}
                
                Top Available Players: {', '.join([p.get('name', 'Unknown') for p in truly_available[:10]]) if truly_available else 'Loading...'}
                """
            else:
                # No draft context available, use raw data
                live_data = raw_live_data
                print(f"📊 Passing {len(live_data)} chars of rankings data to AI")
                if "Josh Allen" in live_data and "Tyreek Hill" in live_data:
                    print("✅ Data includes both Josh Allen and Tyreek Hill")
            
            # Create single comprehensive task
            task = Task(
                description=f"""
                Answer this fantasy football question: "{question}"
                
                League: {self.session_context.get('league_context', {}).get('name', 'SUPERFLEX') if self.session_context.get('league_context') else 'SUPERFLEX'} 
                Format: SUPERFLEX Half-PPR (NO IDP - Individual Defensive Players)
                
                ROSTER CONSTRUCTION (User's Sleeper League):
                Starting Lineup:
                • 1 QB (required)
                • 2 RB (required)  
                • 3 WR (required) ⚠️ MORE THAN STANDARD
                • 1 TE (required)
                • 1 FLEX (RB/WR/TE)
                • 1 SUPERFLEX (QB/RB/WR/TE) - QBs get full points here
                • 1 K (Kicker)
                • 1 DST (Defense/Special Teams)
                • Bench + 1 IR slot
                
                ELIGIBLE POSITIONS FOR RECOMMENDATIONS:
                ✅ QB, RB, WR, TE, K, DST (only these positions)
                ❌ NEVER recommend IDP: LB, CB, S, DE, DT, etc. (league doesn't use individual defensive players)
                
                {draft_context}
                
                CURRENT TOP PLAYERS:
                {live_data}
                
                CRITICAL RULES FOR RECOMMENDATIONS:
                1. **MANDATORY**: ONLY recommend players from the AVAILABLE PLAYERS list above - NEVER suggest players not in this list
                2. **STRICTLY FORBIDDEN**: Do NOT recommend retired/inactive players like Todd Gurley, Antonio Brown, etc.
                3. **VERIFICATION REQUIRED**: Before suggesting any player, confirm they appear in the AVAILABLE PLAYERS list
                4. DO NOT recommend any players listed in "Recently Drafted" section  
                5. PAY CLOSE ATTENTION to the "Position Summary" - it tells you what positions to prioritize or avoid
                6. If Position Summary says "Avoid: QB" - DO NOT recommend QBs as primary picks
                7. Focus on positions listed in "Top Priorities" from Position Summary
                8. For SUPERFLEX: QBs are valuable, but after 3 QBs, focus on RB/WR/TE depth
                
                RECOMMENDATION LOGIC:
                • POSITION ELIGIBILITY: Only recommend QB, RB, WR, TE, K, DST (no individual defensive players)
                • ROSTER CONSTRUCTION: Consider specific starting lineup needs (1QB, 2RB, 3WR, 1TE, 1FLEX, 1SUPERFLEX)
                • WR PREMIUM LEAGUE: Need 3 starting WRs + FLEX eligibility = HIGH WR demand
                • If user has 3+ QBs: Prioritize RB, WR, TE over additional QBs (QB scoring is lower than typical SUPERFLEX)
                • If user lacks RB depth (<4 RBs): Strongly favor RBs for RB1/RB2/FLEX needs
                • If user lacks WR depth (<5 WRs): Strongly favor WRs for WR1/WR2/WR3/FLEX needs  
                • Use FantasyPros SUPERFLEX rankings as primary guide (more accurate than Sleeper for SUPERFLEX)
                • Consider bye week diversity to avoid stacking same-week players
                • K and DST typically drafted in final rounds (picks 13-16)
                
                Provide multiple recommendations with:
                1. Top 3 AVAILABLE player recommendations (following position priorities above)
                2. Key reasoning for each player (2-3 points including FantasyPros ranking)
                3. Why this position fits user's current roster needs
                4. Alternative options if primary picks get drafted
                
                Format as:
                🥇 **Primary Pick**: Player Name (Position) - Reasoning
                🥈 **Backup Option**: Player Name (Position) - Reasoning  
                🥉 **Third Choice**: Player Name (Position) - Reasoning
                
                FINAL VALIDATION: Before submitting your recommendations, double-check that EVERY player you suggest appears in the AVAILABLE PLAYERS list above. If not, replace with a different player from the list.
                
                REMEMBER: Follow the position priorities from Position Summary above - don't just default to QBs!
                """,
                agent=self.agents["advisor"],  # Use most capable agent
                expected_output="Concise recommendation with clear reasoning"
            )
            
            # Execute single task using crew (needed for proper execution)
            mini_crew = Crew(
                agents=[self.agents["advisor"]],
                tasks=[task],
                process=Process.sequential,
                verbose=False
            )
            
            result = mini_crew.kickoff()
            # Check if we got a valid result
            if result:
                return str(result)  # Return the raw result without wrapping
            else:
                return "No result from CrewAI"
            
        except Exception as e:
            # Ultra-fast fallback
            print(f"⚠️ CrewAI execution failed: {e}")
            import traceback
            traceback.print_exc()
            return f"""
🎯 **Quick Analysis** (Fallback):

Based on your question: "{question}"

For SUPERFLEX leagues, remember:
- QBs are premium (Josh Allen, Lamar Jackson worth early picks)
- Positional scarcity matters more than standard leagues
- Target 2-3 QBs by round 7

Current recommendation: Focus on proven performers with high floors in SUPERFLEX format.

⚠️ For detailed analysis, the full multi-agent system is available but may take longer.
            """
    
    async def _create_optimized_tasks(self, question: str) -> List[Task]:
        """Create streamlined tasks with reduced context for speed"""
        # Get targeted data only
        relevant_players = self._extract_player_names(question)
        if relevant_players:
            live_data = await get_player_projections_data(relevant_players[:5])  # Max 5 players
        else:
            live_data = await get_cached_rankings_data(limit=15)  # Reduced from 100, cached
        
        # Streamlined tasks with shorter prompts
        tasks = [
            Task(
                description=f'Identify key players and data for: "{question}". Use: {live_data[:500]}...',  # Truncated
                agent=self.agents["data_collector"],
                expected_output="Key player data summary"
            ),
            Task(
                description=f'Analyze players for: "{question}". Focus on main comparison points.',
                agent=self.agents["analyst"],
                expected_output="Player analysis summary"
            ),
            Task(
                description=f'Strategy for: "{question}". Consider SUPERFLEX league format.',
                agent=self.agents["strategist"],
                expected_output="Strategic recommendation"
            ),
            Task(
                description=f'Final answer for: "{question}". Be concise and actionable.',
                agent=self.agents["advisor"],
                expected_output="Clear recommendation with reasoning"
            )
        ]
        
        return tasks
    
    def _extract_player_names(self, question: str) -> List[str]:
        """Extract likely player names from question"""
        # Simple name extraction - look for capitalized words
        words = question.split()
        names = []
        
        for i, word in enumerate(words):
            if word[0].isupper() and len(word) > 2:
                # Check if next word is also capitalized (likely full name)
                if i + 1 < len(words) and words[i + 1][0].isupper():
                    names.append(f"{word} {words[i + 1]}")
                elif word not in ['Should', 'Who', 'What', 'The', 'Josh', 'Allen'] and len(word) > 3:
                    names.append(word)
        
        return list(set(names))  # Remove duplicates
    
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
            Draft recommendation with reasoning (3 players)
        """
        question = f"What player should I draft with pick #{current_pick}? Give me your top 3 recommendations with reasoning for each. Format as: 1. Player Name (Position) - Reasoning, 2. Player Name (Position) - Reasoning, 3. Player Name (Position) - Reasoning."
        
        if context is None:
            context = {}
        context["current_pick"] = current_pick
        context["multiple_recommendations"] = True
        
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
    
    async def connect_to_draft(self, draft_url: str, user_roster_id: int = None) -> Dict[str, Any]:
        """
        Connect to a live Sleeper draft using URL
        
        Args:
            draft_url: Full Sleeper draft URL
            user_roster_id: User's roster ID in the draft (1-12)
            
        Returns:
            Dictionary with connection status and draft info
        """
        try:
            # Extract draft ID from URL
            # Handle different Sleeper URL formats
            sleeper_patterns = [
                r'sleeper\.com/draft/nfl/(\d{15,20})',    # Your format: sleeper.com/draft/nfl/ID
                r'sleeper\.com/draft/[^/]+/(\d{15,20})',  # Other main format
                r'sleeper\.app/draft/[^/]+/(\d{15,20})',  # App format
                r'draft_id[=:](\d{15,20})',               # Direct ID format
                r'^(\d{15,20})$'                          # Just the ID number
            ]
            
            draft_id = None
            for pattern in sleeper_patterns:
                match = re.search(pattern, draft_url)
                if match:
                    draft_id = match.group(1)
                    break
            
            if not draft_id:
                return {"success": False, "error": "Could not extract draft ID from URL"}
            
            print(f"🎯 Connecting to draft ID: {draft_id}")
            
            # Initialize Sleeper client if not already done
            if not hasattr(self, '_sleeper_client_initialized'):
                await self.sleeper_client.__aenter__()
                self._sleeper_client_initialized = True
            
            # Get draft info
            draft_info = await self.sleeper_client.get_draft_info(draft_id)
            if not draft_info:
                return {"success": False, "error": "Draft not found or not accessible"}
            
            # Use provided roster ID or try to detect it
            if user_roster_id is not None:
                print(f"📍 Using provided roster ID: {user_roster_id}")
            else:
                # Fallback: try to detect from username (less reliable)
                username = os.getenv('SLEEPER_USERNAME', '').lower()
                if username:
                    try:
                        league_id = draft_info.get('league_id')
                        if league_id:
                            league_info = await self.sleeper_client.get_league_info(league_id)
                            rosters = await self.sleeper_client.get_league_rosters(league_id)
                            print(f"🔍 Looking for username '{username}' in {len(rosters)} rosters")
                            user_roster_id = 1  # Default fallback
                            print(f"📍 Using default roster ID: {user_roster_id}")
                    except Exception as e:
                        print(f"⚠️ Could not determine roster ID: {e}")
                        user_roster_id = 1
            
            # Update session context
            self.session_context.update({
                "draft_id": draft_id,
                "user_roster_id": user_roster_id,
                "league_context": {
                    "name": draft_info.get('league_name', 'Unknown'),
                    "teams": draft_info.get('teams', 12),
                    "rounds": draft_info.get('rounds', 16),
                    "is_superflex": True  # Assume SUPERFLEX for your league
                }
            })
            
            self.draft_active = True
            print(f"✅ Connected to draft: {draft_info.get('league_name', 'Unknown')}")
            
            # Get initial draft state
            await self.update_draft_state()
            
            return {
                "success": True,
                "draft_id": draft_id,
                "league_name": draft_info.get('league_name', 'Unknown'),
                "user_roster_id": user_roster_id,
                "teams": draft_info.get('teams', 12)
            }
            
        except Exception as e:
            print(f"❌ Error connecting to draft: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_draft_state(self) -> Dict[str, Any]:
        """
        Update the current draft state with latest picks and available players
        
        Returns:
            Dictionary with current draft state
        """
        if not self.draft_active or not self.session_context.get("draft_id"):
            return {"error": "No active draft connection"}
        
        try:
            draft_id = self.session_context["draft_id"]
            
            # Get current picks
            picks = await self.sleeper_client.get_draft_picks(draft_id)
            current_pick_count = len(picks)
            
            # Get available players (limited for performance)
            all_available = await self.sleeper_client.get_available_players(
                draft_id, enhanced=False  # Basic data for speed
            )
            # Limit to top 50 available players for performance
            available_players = all_available[:50] if all_available else []
            
            # Calculate user's turn and actual draft position
            user_roster_id = self.session_context.get("user_roster_id")
            picks_until_user = None
            user_next_pick_number = None
            
            if user_roster_id:
                teams = self.session_context.get("league_context", {}).get("teams", 12)
                
                # Calculate user's actual pick positions in snake draft
                def get_user_pick_in_round(round_num, user_roster_id, teams):
                    if round_num % 2 == 1:  # Odd rounds: normal order
                        return (round_num - 1) * teams + user_roster_id
                    else:  # Even rounds: reverse order  
                        return (round_num - 1) * teams + (teams - user_roster_id + 1)
                
                # Find user's next pick
                current_round = (current_pick_count // teams) + 1
                for round_check in range(current_round, current_round + 3):  # Check next few rounds
                    user_pick_in_round = get_user_pick_in_round(round_check, user_roster_id, teams)
                    if user_pick_in_round > current_pick_count:
                        user_next_pick_number = user_pick_in_round
                        picks_until_user = user_pick_in_round - current_pick_count - 1
                        break
                
            # Update context
            self.session_context.update({
                "draft_picks": picks,
                "available_players": available_players,  # Already limited to 50
                "current_pick": current_pick_count + 1,
                "user_next_pick": user_next_pick_number,
                "picks_until_user": picks_until_user
            })
            
            # Track new picks
            new_picks = []
            if current_pick_count > self.last_pick_count:
                new_picks = picks[self.last_pick_count:]
                self.last_pick_count = current_pick_count
            
            # Check for proactive recommendations
            proactive_result = await self.check_proactive_recommendations()
            
            return {
                "current_pick": current_pick_count + 1,
                "user_next_pick": user_next_pick_number,
                "new_picks": new_picks,
                "available_count": len(available_players),
                "picks_until_user": picks_until_user,
                "proactive_recommendation": proactive_result
            }
            
        except Exception as e:
            print(f"❌ Error updating draft state: {e}")
            return {"error": str(e)}

    async def check_proactive_recommendations(self) -> Dict[str, Any]:
        """
        Check if we should proactively generate recommendations
        
        Returns:
            Dict with proactive recommendation data if needed
        """
        if not self.draft_active or not self.session_context.get("picks_until_user"):
            return {}
        
        picks_until_user = self.session_context.get("picks_until_user", 999)
        current_pick = self.session_context.get("current_pick", 1)
        last_proactive = self.session_context.get("last_proactive_pick")
        
        # Generate proactive recommendations at 6 picks and 3 picks ahead
        should_generate = False
        trigger_type = None
        
        if picks_until_user == 6:
            should_generate = True
            trigger_type = "initial"
        elif picks_until_user == 3 and last_proactive != current_pick:
            should_generate = True
            trigger_type = "revision"
        
        if not should_generate:
            return {}
        
        try:
            print(f"🎯 Generating proactive recommendations ({trigger_type}) - {picks_until_user} picks until your turn")
            
            # Generate recommendations proactively
            question = f"My next pick is in {picks_until_user} picks. Based on the current draft state and likely picks that will happen, what are my top 3 realistic options? Consider which players might still be available."
            
            context = {
                "proactive": True,
                "trigger_type": trigger_type,
                "picks_ahead": picks_until_user,
                "multiple_recommendations": True
            }
            
            recommendation = await self._handle_simple_question(question)
            
            # Cache the recommendation
            self.session_context["proactive_recommendations"][current_pick] = {
                "picks_ahead": picks_until_user,
                "trigger_type": trigger_type,
                "recommendation": recommendation,
                "generated_at": current_pick
            }
            self.session_context["last_proactive_pick"] = current_pick
            
            return {
                "proactive_generated": True,
                "picks_ahead": picks_until_user,
                "trigger_type": trigger_type,
                "recommendation": recommendation
            }
            
        except Exception as e:
            print(f"❌ Error generating proactive recommendations: {e}")
            return {"error": str(e)}
    
    async def get_proactive_recommendation(self) -> str:
        """
        Get the most recent proactive recommendation if available
        
        Returns:
            Proactive recommendation string or empty if none available
        """
        proactive_recs = self.session_context.get("proactive_recommendations", {})
        if not proactive_recs:
            return ""
        
        # Get the most recent recommendation
        latest_pick = max(proactive_recs.keys())
        latest_rec = proactive_recs[latest_pick]
        
        picks_ahead = self.session_context.get("picks_until_user", 999)
        
        return f"""
🎯 **Proactive Analysis** (Generated when {latest_rec['picks_ahead']} picks ahead):

{latest_rec['recommendation']}

---
⏰ Current Status: {picks_ahead} picks until your turn
📊 Analysis Type: {latest_rec['trigger_type'].title()} proactive generation
        """.strip()

    def _get_roster_position_summary(self, user_roster):
        """
        Create a position summary for the user's current roster to help AI make contextual recommendations.
        This analyzes what positions the user has and what they might need next.
        
        Args:
            user_roster: List of draft picks made by the user
        
        Returns:
            String describing current roster composition and needs
        """
        if not user_roster:
            return "No picks yet"
        
        # Count positions in user's roster
        position_counts = {}
        for pick in user_roster:
            position = pick.get('metadata', {}).get('position', 'Unknown')
            position_counts[position] = position_counts.get(position, 0) + 1
        
        # Create summary with strategic recommendations
        summary_parts = []
        for pos, count in sorted(position_counts.items()):
            summary_parts.append(f"{pos}: {count}")
        
        position_summary = ", ".join(summary_parts)
        
        # Add strategic context for SUPERFLEX format
        qb_count = position_counts.get('QB', 0)
        rb_count = position_counts.get('RB', 0)
        wr_count = position_counts.get('WR', 0)
        te_count = position_counts.get('TE', 0)
        
        # Strategic recommendations based on current roster composition
        # This provides explicit guidance to AI about position priorities
        needs = []
        avoid_positions = []
        
        # QB Assessment for SUPERFLEX (need 1 starter + 1 SUPERFLEX, 3+ for depth)
        if qb_count == 0:
            needs.append("QB (critical - need starter for QB slot)")
        elif qb_count == 1:
            needs.append("2nd QB (important - need SUPERFLEX starter)")
        elif qb_count == 2:
            needs.append("3rd QB (valuable depth for SUPERFLEX)")
        elif qb_count >= 3:
            avoid_positions.append("QB (sufficient depth - focus on skill positions)")
        
        # RB Assessment (need 2 starters + FLEX eligibility)
        if rb_count < 2:
            needs.append("RB (critical - need starters for RB1/RB2 slots)")
        elif rb_count < 4:
            needs.append("RB (important - need FLEX depth and handcuffs)")
        elif rb_count < 6:
            needs.append("RB (depth for injuries and matchups)")
            
        # WR Assessment (need 3 starters + FLEX eligibility - WR PREMIUM LEAGUE!)  
        if wr_count < 3:
            needs.append("WR (critical - need starters for WR1/WR2/WR3 slots)")
        elif wr_count < 5:
            needs.append("WR (important - need FLEX depth, have 3 WR starters)")
        elif wr_count < 7:
            needs.append("WR (depth for injuries and matchups)")
            
        # TE Assessment (need 1 starter + potential FLEX)
        if te_count == 0:
            needs.append("TE (critical - need starter for TE slot)")
        elif te_count == 1:
            needs.append("2nd TE (insurance and potential FLEX play)")
        
        # K and DST Assessment (usually drafted late)
        k_count = position_counts.get('K', 0)
        dst_count = position_counts.get('DST', 0)
        
        if len(user_roster) > 12:  # Late rounds
            if k_count == 0:
                needs.append("K (need for starting lineup)")
            if dst_count == 0:
                needs.append("DST (need for starting lineup)")
        
        # Build strategic message with explicit priorities
        strategy_parts = []
        if needs:
            # Prioritize the top 2-3 most critical needs
            priority_needs = needs[:3]
            strategy_parts.append(f"Top Priorities: {', '.join(priority_needs)}")
        
        if avoid_positions:
            strategy_parts.append(f"Avoid: {', '.join(avoid_positions)}")
        
        if strategy_parts:
            return f"{position_summary}. {' | '.join(strategy_parts)}"
        else:
            return f"{position_summary}. Well-rounded roster, focus on BPA or positional depth"

    def _get_bye_week_analysis(self, user_roster, available_players):
        """
        Analyze bye week distribution to help avoid stacking players with same bye weeks.
        This helps maintain roster flexibility throughout the season.
        
        Args:
            user_roster: List of user's current picks
            available_players: List of available players to consider
            
        Returns:
            Dict with bye week analysis and recommendations
        """
        if not user_roster:
            return {"message": "No current roster to analyze bye weeks"}
        
        # Count bye weeks from current roster
        bye_week_counts = {}
        for pick in user_roster:
            bye_week = pick.get('metadata', {}).get('bye_week')
            if bye_week:
                bye_week_counts[bye_week] = bye_week_counts.get(bye_week, 0) + 1
        
        # Find weeks with 3+ players (problematic for lineup setting)
        problematic_weeks = [week for week, count in bye_week_counts.items() if count >= 3]
        
        # Analyze available players to avoid adding to problematic weeks
        avoid_players = []
        if problematic_weeks and available_players:
            for player in available_players[:20]:  # Check top 20 available
                player_bye = player.get('bye_week')
                if player_bye in problematic_weeks:
                    avoid_players.append(f"{player.get('name', 'Unknown')} (Bye {player_bye})")
        
        analysis = {
            "bye_week_distribution": bye_week_counts,
            "problematic_weeks": problematic_weeks,
            "players_to_avoid": avoid_players[:5],  # Limit to top 5 for readability
            "message": ""
        }
        
        if problematic_weeks:
            analysis["message"] = f"⚠️ Avoid Week {', '.join(map(str, problematic_weeks))} bye players"
        else:
            analysis["message"] = "✅ Good bye week distribution"
            
        return analysis


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