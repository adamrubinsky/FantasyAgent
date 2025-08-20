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
async def get_cached_rankings_data(position: str = "OP", limit: int = 50, cache_minutes: int = 240) -> str:
    """Cached version of live rankings data to reduce API calls during rapid queries
    
    Default cache is 4 hours (240 minutes) since rankings rarely change more than daily.
    This prevents overusing the API while still getting updates if needed.
    """
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

async def get_live_rankings_data(position: str = "OP", limit: int = 50) -> str:
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
        # Check for cached data from today first
        import time
        from pathlib import Path
        import json
        
        # Try different cache file names (with and without limit in filename)
        cache_files = [
            Path(__file__).parent.parent / "data" / f"fantasypros_rankings_NFL_OP_HALF_{limit}.json",
            Path(__file__).parent.parent / "data" / "fantasypros_rankings_NFL_OP_HALF_50.json",
            Path(__file__).parent.parent / "data" / "fantasypros_rankings_NFL_OP_HALF_200.json"
        ]
        
        rankings = None
        for cache_file in cache_files:
            if cache_file.exists():
                cache_age = time.time() - cache_file.stat().st_mtime
                # Use cache if it's from today (less than 24 hours old)
                if cache_age < 86400:  # 24 hours
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)
                        print(f"✅ Using cached FantasyPros data ({cache_file.name}, {cache_age/3600:.1f}h old)")
                        rankings = cached_data
                        break
        
        if not rankings:
            # No cache or cache is old, fetch fresh data
            from core.official_fantasypros import OfficialFantasyProsMCP
            
            client = OfficialFantasyProsMCP()
            if await client.is_server_available():
                print("🔄 Cache expired, fetching fresh FantasyPros rankings")
                rankings = await client.get_rankings(
                    sport="NFL",
                    position=position if position != "ALL" else "OP",  # Use OP for SUPERFLEX
                    scoring="HALF",
                    limit=limit
                )
            else:
                # Fall back to MCP if API not available
                async with MCPClient() as mcp:
                    # Fetch current rankings from FantasyPros via MCP
                    rankings = await mcp.get_rankings(limit=limit)
        
        # If still no rankings after all attempts, return fallback
        if not rankings:
            print("❌ Failed to get rankings from any source")
            return get_sync_rankings_fallback()
            
        # Filter by position if user requested specific position
        if position not in ["ALL", "OP"]:  # OP is SUPERFLEX, don't filter
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
                # Extract player information with correct FantasyPros field names
                name = player.get('player_name', player.get('name', 'Unknown'))
                pos = player.get('player_position_id', player.get('player_positions', player.get('position', 'Unknown')))
                rank = player.get('rank_ecr', player.get('rank', 'N/A'))
                pos_rank = player.get('pos_rank', '')
                team = player.get('player_team_id', player.get('team', 'N/A'))
                tier = player.get('tier', '')
                
                # Format as readable string for agent to parse
                player_info = f"{name} ({pos}) - Rank: {rank}, Pos: {pos_rank}, Team: {team}"
                if tier:
                    player_info += f", Tier: {tier}"
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
        
        # Track conversation context with enhanced analytics
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
            "last_proactive_pick": None,
            "recent_picks": [],  # Track last 6 picks for run detection
            "player_adps": {}    # Store ADP values for value detection
        }
        
        # Draft monitoring state
        self.draft_active = False
        self.last_pick_count = 0
        
        # Performance caching - optimized for speed
        self._cached_rankings = None
        self._cache_timestamp = None
        self._cache_ttl = 14400  # 4 hours - good balance for rankings updates
    
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
        import time
        total_start = time.time()
        
        # Update session context
        if context:
            self.session_context.update(context)
            # LOG CONTEXT for debugging
            print(f"📊 Context updated with {len(context.get('draft_picks', []))} draft picks")
            print(f"📊 Context has {len(context.get('available_players', []))} available players")
            print(f"📊 User roster: {len(context.get('roster', []))} players")
        
        # If we have an active draft connection, update with live data
        if self.draft_active:
            update_start = time.time()
            await self.update_draft_state()
            print(f"⏱️ Draft state update: {time.time() - update_start:.2f}s")
        
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
            simple_start = time.time()
            result = await self._handle_simple_question(question)
            print(f"⏱️ Simple question handling: {time.time() - simple_start:.2f}s")
            print(f"⏱️ TOTAL TIME: {time.time() - total_start:.2f}s")
            return result
        
        # Use full multi-agent workflow for complex questions
        try:
            task_start = time.time()
            tasks = await self._create_optimized_tasks(question)
            print(f"⏱️ Task creation: {time.time() - task_start:.2f}s")
            
            crew_setup_start = time.time()
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
            print(f"⏱️ Crew setup: {time.time() - crew_setup_start:.2f}s")
            
            # No timeout - let it complete properly
            print("🚀 Starting CrewAI analysis (this may take 20-30 seconds)...")
            kickoff_start = time.time()
            result = crew.kickoff()
            print(f"⏱️ Crew kickoff: {time.time() - kickoff_start:.2f}s")
            print(f"⏱️ TOTAL TIME: {time.time() - total_start:.2f}s")
            print("✅ CrewAI analysis complete")
            return str(result)
                
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
        """Fast single-agent response for simple questions with enhanced strategy"""
        print("🚀 Using optimized single-agent response with advanced analytics...")
        import time
        handler_start = time.time()
        
        # Check if this is a keeper-specific question
        question_lower = question.lower()
        if any(term in question_lower for term in ["keeper", "keep", "dynasty", "next year", "2026"]):
            return await self._handle_keeper_question(question)
        
        try:
            # Get SUPERFLEX rankings with ADP data - essential for value detection
            rankings_start = time.time()
            raw_live_data = await get_cached_rankings_data(position="OP", limit=200)  # Get 200 for full draft coverage
            print(f"  ⏱️ Rankings fetch: {time.time() - rankings_start:.2f}s")
            
            # Get draft context with enhancements
            draft_context = ""
            
            # Check if we have draft data from context (even without active connection)
            draft_picks = self.session_context.get('draft_picks', [])
            if draft_picks or self.draft_active:
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
                
                # Filter user's picks - try multiple methods
                # Method 1: Use draft_slot (works for mock drafts)
                user_roster = [pick for pick in draft_picks if pick.get('draft_slot') == user_roster_id]
                
                # Method 2: If that doesn't work, try picked_by with user ID
                if not user_roster and user_sleeper_id:
                    user_roster = [pick for pick in draft_picks if pick.get('picked_by') == user_sleeper_id]
                    print(f"✅ Found {len(user_roster)} picks using picked_by field")
                
                # Method 3: Fallback to roster_id
                if not user_roster:
                    user_roster = [pick for pick in draft_picks if pick.get('roster_id') == user_roster_id]
                    print(f"⚠️ Using roster_id fallback, found {len(user_roster)} picks")
                
                if user_roster:
                    print(f"✅ Found {len(user_roster)} picks for roster slot {user_roster_id}")
                    # Log the actual players on the user's roster for debugging
                    roster_names = []
                    for pick in user_roster[:10]:  # Show first 10
                        metadata = pick.get('metadata', {})
                        name = f"{metadata.get('first_name', '')} {metadata.get('last_name', '')}".strip()
                        if name:
                            roster_names.append(name)
                    if roster_names:
                        print(f"📋 User's roster includes: {', '.join(roster_names)}")
                
                # Extract drafted player IDs from Sleeper draft picks 
                # Sleeper API provides player_id directly in each draft pick
                # IMPORTANT: Include keepers which may have metadata.is_keeper = true
                drafted_sleeper_ids = set()
                keeper_count = 0
                for pick in draft_picks:
                    sleeper_player_id = pick.get('player_id')
                    if sleeper_player_id:
                        drafted_sleeper_ids.add(str(sleeper_player_id))
                        # Check if this is a keeper pick
                        metadata = pick.get('metadata', {})
                        if metadata.get('is_keeper'):
                            keeper_count += 1
                
                print(f"📊 Drafted players: {len(drafted_sleeper_ids)} total ({keeper_count} keepers)")
                
                # The available_players from session_context are already filtered by Sleeper client
                # They already exclude drafted players and only include active players with teams
                # We just need to ensure they're fantasy-relevant positions
                truly_available = available_players  # Already filtered by Sleeper API
                
                print(f"📊 Available players from Sleeper: {len(truly_available)}")
                
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
                
                # Player mapping stats disabled for now (mapper not imported)
                
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
                            
                            # For now, include all players that aren't obviously drafted
                            # TODO: Add player mapping to verify draft status across platforms
                            filtered_lines.append(line)
                    
                    # Create the formatted text data that the AI will read
                    # Show enough players for good recommendations but not too many for speed
                    if len(filtered_lines) > 0:
                        live_data = "AVAILABLE PLAYERS (EXCLUDING DRAFTED):\n" + "\n".join(filtered_lines[:30])
                        print(f"🎯 Text filtering: {len(filtered_lines)} available from {len(lines)} total, showing top 30")
                    else:
                        # If no filtered lines, something went wrong - show unfiltered as fallback
                        print(f"⚠️ No players after filtering! Showing unfiltered list")
                        live_data = raw_live_data
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
                
                # Calculate round and parse ADPs for advanced analytics
                round_num = ((current_pick - 1) // 12) + 1
                
                # Store recent picks for run detection
                self.session_context['recent_picks'] = draft_picks[-6:] if len(draft_picks) >= 6 else draft_picks
                
                # Parse ADPs if not already done
                if not self.session_context.get('player_adps') and raw_live_data:
                    self._parse_and_store_adps(raw_live_data)
                
                # Detect value picks
                value_picks = []
                for player in truly_available[:20]:
                    player_name = player.get('player_name', player.get('name', ''))
                    adp_value = self._calculate_adp_value(player_name, current_pick)
                    if adp_value >= 10:
                        value_picks.append(f"{player_name} (falling {adp_value:.0f} spots)")
                
                # Check for runs and stacks
                run_position = self._detect_positional_run()
                stack_opportunities = self._get_qb_wr_stacks(truly_available)
                round_strategy = self._get_superflex_round_strategy(round_num)
                
                draft_context = f"""
                LIVE DRAFT CONTEXT - ROUND {round_num}:
                • Overall Pick: #{current_pick} 
                • {user_turn_info}
                • Your Picks So Far: {len(user_roster)}
                • Truly Available Players: {len(truly_available)} (excluding drafted)
                
                {round_strategy}
                
                📊 VALUE ALERTS: {', '.join(value_picks[:3]) if value_picks else 'No major values'}
                🏃 RUN DETECTION: {f'{run_position} run happening - fade for value!' if run_position else 'No runs'}
                🔗 STACKING: {f"{stack_opportunities[0]['player_name']} stacks with {stack_opportunities[0]['qb_name']}" if stack_opportunities else 'None'}
                
                Your Current Roster: {', '.join([f"{(p.get('metadata', {}).get('first_name', '') + ' ' + p.get('metadata', {}).get('last_name', '')).strip() or 'Unknown'} ({p.get('metadata', {}).get('position', '?')})" for p in user_roster]) if user_roster else 'None yet'}
                
                Position Summary: {self._get_roster_position_summary(user_roster) if user_roster else 'No picks yet - recommend based on SUPERFLEX value'}
                
                Bye Week Analysis: {self._get_bye_week_analysis(user_roster, truly_available).get('message', 'N/A') if user_roster else 'No roster yet'}
                
                Recently Drafted: {', '.join([f"{(p.get('metadata', {}).get('first_name', '') + ' ' + p.get('metadata', {}).get('last_name', '')).strip() or 'Unknown'} (Pick {p.get('pick_no')})" for p in draft_picks[-3:]]) if draft_picks else 'None yet'}
                
                Top 30 Available Players (sorted by rank):
                {chr(10).join([f"  • {p.get('name', 'Unknown')} ({', '.join(p.get('positions', ['?']))})" for p in truly_available[:30]]) if truly_available else 'Loading...'}
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
                
                KEY RULES:
                1. ONLY recommend players from the AVAILABLE PLAYERS list above
                2. Follow the Position Summary priorities
                3. For SUPERFLEX: Balance QB value with roster needs
                4. DO NOT REACH: Only recommend players within 10-15 picks of their ADP/rank
                5. WATCHLIST DISCIPLINE: Do NOT prioritize watchlist/starred players unless they're within 10 picks of ADP
                
                RECOMMENDATION LOGIC:
                • ADP AWARENESS: Don't recommend players more than 15 picks before their ADP - that's reaching!
                • WATCHLIST RULE: Just because a player is on the watchlist does NOT mean draft them early
                • If a player's rank is 50 and we're at pick 20, that's a 30-pick reach - TOO EARLY
                • Good value = player available at or after their ADP (THIS is when to draft watchlist players)
                • Acceptable reach = within 10-15 picks of ADP (for high-priority needs only)
                • POSITION ELIGIBILITY: Only recommend QB, RB, WR, TE, K, DST (no individual defensive players)
                • ROSTER CONSTRUCTION: Consider specific starting lineup needs (1QB, 2RB, 3WR, 1TE, 1FLEX, 1SUPERFLEX)
                • WR PREMIUM LEAGUE: Need 3 starting WRs + FLEX eligibility = HIGH WR demand
                • If user has 3+ QBs: Prioritize RB, WR, TE over additional QBs (QB scoring is lower than typical SUPERFLEX)
                • If user lacks RB depth (<4 RBs): Strongly favor RBs for RB1/RB2/FLEX needs
                • If user lacks WR depth (<5 WRs): Strongly favor WRs for WR1/WR2/WR3/FLEX needs  
                • Use FantasyPros SUPERFLEX rankings as primary guide (more accurate than Sleeper for SUPERFLEX)
                • Consider bye week diversity to avoid stacking same-week players
                • K and DST typically drafted in final rounds (rounds 15-17)
                
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
                verbose=True  # Enable verbose to see what's happening
            )
            
            print("🤖 Executing single-agent analysis...")
            result = mini_crew.kickoff()
            print(f"✅ Got result: {str(result)[:100]}...")  # Show first 100 chars
            
            # Check if we got a valid result
            if result:
                return str(result)  # Return the raw result without wrapping
            else:
                print("⚠️ No result from CrewAI")
                return "No result from CrewAI"
            
        except Exception as e:
            # Better fallback with actual player data
            print(f"⚠️ CrewAI execution failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Get available players for a useful fallback
            available_players = self.session_context.get('available_players', [])
            draft_picks = self.session_context.get('draft_picks', [])
            user_roster_id = self.session_context.get('user_roster_id')
            current_pick = self.session_context.get('current_pick', 1)
            
            # Get user's roster
            user_roster = [p for p in draft_picks if p.get('roster_id') == user_roster_id]
            
            # Count positions
            position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'K': 0, 'DEF': 0}
            for pick in user_roster:
                pos = pick.get('metadata', {}).get('position', '')
                if pos in position_counts:
                    position_counts[pos] += 1
            
            # Get top available players
            top_players = available_players[:20] if available_players else []
            player_list = '\n'.join([f"• {p.get('name', 'Unknown')} ({', '.join(p.get('positions', ['?']))})" for p in top_players[:10]])
            
            # Determine primary need - respect round-based strategy
            current_round = (current_pick - 1) // 12 + 1  # Assuming 12 teams
            
            # Core positions first, K/DEF only in late rounds
            if position_counts['QB'] < 2:
                primary_need = "QB (for SUPERFLEX)"
            elif position_counts['RB'] < 3:
                primary_need = "RB"
            elif position_counts['WR'] < 4:
                primary_need = "WR"
            elif position_counts['TE'] == 0:
                primary_need = "TE"
            elif current_round >= 15 and position_counts['K'] == 0:
                primary_need = "KICKER (appropriate round for K)"
            elif current_round >= 15 and position_counts['DEF'] == 0:
                primary_need = "DEFENSE (appropriate round for DEF)"
            else:
                primary_need = "Best Player Available"
            
            return f"""
📊 **Pick #{current_pick} Recommendation**

**Your Roster**: {position_counts['QB']} QB, {position_counts['RB']} RB, {position_counts['WR']} WR, {position_counts['TE']} TE

**Primary Need**: {primary_need}

**Top Available Players**:
{player_list}

**Quick Recommendation**: 
Based on your roster needs and available players, consider drafting from the list above, prioritizing {primary_need}.

⚠️ AI analysis temporarily unavailable - showing direct player data instead.
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
        # Common words to exclude that aren't player names
        exclude_words = {
            'Should', 'Who', 'What', 'When', 'Where', 'Why', 'How', 'The', 'They',
            'Draft', 'Round', 'Pick', 'Team', 'Week', 'Start', 'Bench', 'Trade',
            'Keep', 'Drop', 'Add', 'Which', 'Between', 'Compare', 'Versus',
            'Looking', 'Need', 'Want', 'Have', 'Think', 'Consider', 'Help',
            'Best', 'Top', 'Good', 'Great', 'Elite', 'Value', 'Sleeper',
            'Rankings', 'Projections', 'Points', 'Score', 'Season', 'Year'
        }
        
        words = question.split()
        names = []
        
        for i, word in enumerate(words):
            # Clean word of punctuation
            clean_word = word.strip('?,.')
            
            if clean_word and clean_word[0].isupper() and len(clean_word) > 2:
                # Skip if it's a common non-name word
                if clean_word in exclude_words:
                    continue
                    
                # Check if next word is also capitalized (likely full name)
                if i + 1 < len(words):
                    next_word = words[i + 1].strip('?,.')
                    if next_word and next_word[0].isupper() and next_word not in exclude_words:
                        full_name = f"{clean_word} {next_word}"
                        names.append(full_name)
                        # Skip the next word since we've used it
                        continue
        
        return list(set(names))  # Remove duplicates
    
    async def _create_tasks_for_question(self, question: str) -> List[Task]:
        """Create specific tasks for each agent based on the question"""
        
        context_str = json.dumps(self.session_context, indent=2)
        
        # Get BOTH datasets for comprehensive analysis
        # 1. Full FantasyPros rankings (for reference and ADP values)
        full_rankings = await get_live_rankings_data(limit=200)  # Get 200 for better coverage
        
        # 2. Filtered available players (who's actually available to draft)
        draft_picks = self.session_context.get('draft_picks', [])
        available_players = self.session_context.get('available_players', [])
        
        available_section = ""
        if draft_picks and available_players:
            # We have draft context - show who's actually available
            print(f"📊 Using filtered available players: {len(available_players)} available")
            # Format available players as rankings text
            available_lines = []
            for player in available_players[:50]:  # Top 50 available
                name = player.get('player_name', player.get('name', 'Unknown'))
                pos_list = player.get('positions', [])
                pos = pos_list[0] if pos_list else player.get('player_position_id', '?')
                team = player.get('team', 'N/A')
                # Try to find their overall rank from the full rankings
                overall_rank = "N/A"
                if "LIVE RANKINGS" in full_rankings:
                    for line in full_rankings.split('\n'):
                        if name in line and "Rank:" in line:
                            try:
                                overall_rank = line.split("Rank:")[1].split(",")[0].strip()
                                break
                            except:
                                pass
                available_lines.append(f"{name} ({pos}) - Overall Rank: {overall_rank}, Team: {team}")
            
            available_section = "\n\nACTUALLY AVAILABLE TO DRAFT (Top 50):\n" + "\n".join(available_lines)
            
            # Add drafted count for context
            available_section = f"\n\n📊 DRAFT STATUS: {len(draft_picks)} players drafted, {len(available_players)} available" + available_section
        
        # Combine both datasets - but if we have draft context, prioritize available players
        if draft_picks and available_players:
            # Get user's roster for explicit exclusion
            user_roster = self.session_context.get('roster', [])
            user_players = []
            for player in user_roster:
                name = player.get('player_name', player.get('name', ''))
                if name:
                    user_players.append(name)
            
            roster_warning = ""
            if user_players:
                roster_warning = f"\n\n🚨 USER ALREADY HAS THESE PLAYERS - DO NOT RECOMMEND THEM:\n" + "\n".join(f"  - {p}" for p in user_players)
            
            # When draft is active, focus on available players
            live_rankings = f"""
🚨 CRITICAL INSTRUCTIONS:
1. This is an ACTIVE/COMPLETED draft with {len(draft_picks)} picks made
2. ONLY recommend players from the "ACTUALLY AVAILABLE TO DRAFT" list below
3. DO NOT recommend any player from the "Full Rankings" section unless they appear in the AVAILABLE list
4. The user has already drafted {len(user_roster)} players - do not recommend them again
{roster_warning}

{available_section}

Full Rankings (FOR VALUE REFERENCE ONLY - most are already drafted):
{full_rankings}"""
        else:
            # No draft context, use full rankings
            live_rankings = full_rankings + available_section
        
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
            
            LIVE CURRENT DATA FROM FANTASYPROS (USE THESE RANKINGS!):
            {live_rankings}
            
            {live_projections}
            
            Your tasks:
            1. CRITICAL: Use the data provided above - both full rankings AND available players
            2. If there's an "ACTUALLY AVAILABLE TO DRAFT" section, focus on those players
            3. When asked about "best available", use the AVAILABLE section, not the full rankings
            4. ALWAYS REPORT THE ACTUAL RANK NUMBER from the live data
            5. Note which players are drafted (in full rankings but NOT in available section)
            
            IMPORTANT: If draft is active, many top players are already drafted!
            Focus on the "ACTUALLY AVAILABLE TO DRAFT" section for recommendations.
            Report the EXACT rank numbers you find in the data.
            """,
            agent=self.agents["data_collector"],
            expected_output="Exact rankings from FantasyPros data with specific rank numbers"
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
            1. BASE YOUR RECOMMENDATION ON THE ACTUAL FANTASYPROS RANKINGS
            2. Always mention the player's actual rank (e.g., "ranked #31 overall" or "WR9")
            3. If recommending a lower-ranked player over a higher-ranked one, explain why
            4. Give clear, actionable recommendations with rank-based reasoning
            5. Provide your primary pick and a backup option with their ranks
            
            Remember: Lower rank number = better player. Use the actual rank numbers from the data.
            This is the final output the user will see - make it clear and include rankings.
            """,
            agent=self.agents["advisor"],
            expected_output="Clear recommendation with FantasyPros rankings explicitly mentioned"
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
    
    async def get_quick_fallback_response(self, message: str) -> str:
        """
        Quick fallback response when AI times out - uses cached data without AI processing
        
        Args:
            message: User's question
            
        Returns:
            Quick helpful response based on current draft state
        """
        try:
            # Get current draft state if available
            if self.draft_active and self.session_context.get('draft_id'):
                available_players = self.session_context.get('available_players', [])
                draft_picks = self.session_context.get('draft_picks', [])
                user_roster_id = self.session_context.get('user_roster_id')
                current_pick = self.session_context.get('current_pick', 1)
                
                # Get user's roster using draft_slot (correct field)
                user_roster = [p for p in draft_picks if p.get('draft_slot') == user_roster_id]
                
                # Count positions
                position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'K': 0, 'DEF': 0}
                for pick in user_roster:
                    pos = pick.get('metadata', {}).get('position', '')
                    if pos in position_counts:
                        position_counts[pos] += 1
                
                # Get top available players
                top_players = available_players[:15] if available_players else []
                player_list = '\n'.join([f"• {p.get('name', 'Unknown')} ({', '.join(p.get('positions', ['?']))})" for p in top_players[:10]])
                
                # Determine primary needs for SUPERFLEX
                needs = []
                if position_counts['QB'] < 2:
                    needs.append("QB (for SUPERFLEX)")
                if position_counts['RB'] < 3:
                    needs.append("RB")
                if position_counts['WR'] < 4:
                    needs.append("WR (need 3 starters + FLEX)")
                if position_counts['TE'] == 0:
                    needs.append("TE")
                
                primary_need = needs[0] if needs else "Best Player Available"
                
                return f"""📊 **Quick Analysis for Pick #{current_pick}**

**Your Roster**: {position_counts['QB']} QB, {position_counts['RB']} RB, {position_counts['WR']} WR, {position_counts['TE']} TE

**Primary Needs**: {', '.join(needs) if needs else 'Balanced roster - go BPA'}

**Top 10 Available Players**:
{player_list}

**SUPERFLEX Strategy**: 
• QBs are premium - target 2-3 total
• Need 3 starting WRs + FLEX
• RB depth crucial for injuries

💡 *AI detailed analysis temporarily unavailable - showing quick roster analysis*"""
            else:
                # No draft context - give generic SUPERFLEX advice
                return """📚 **SUPERFLEX Draft Strategy**

**Key Positions**:
• QB: Most valuable - target 2-3 early
• RB: Get 2 starters + depth  
• WR: Need 3 starters + FLEX (4-5 total)
• TE: Elite or wait (huge tier drop)

**Round Strategy**:
• Rounds 1-3: Elite QB/RB/WR
• Rounds 4-6: Fill starters  
• Rounds 7-10: Depth & upside
• Rounds 11-14: Handcuffs & rookies
• Rounds 15-16: K & DEF

💡 *Connect to a draft for personalized recommendations*"""
                
        except Exception as e:
            print(f"❌ Error in fallback response: {e}")
            return "I can help with your SUPERFLEX draft! Connect to a draft for personalized recommendations, or ask about specific players or strategies."
    
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
            
            # Get current picks - ALWAYS fresh from API
            picks = await self.sleeper_client.get_draft_picks(draft_id)
            
            # CRITICAL: Store picks in session context so other methods can use them
            self.session_context['draft_picks'] = picks
            
            # Calculate actual next pick number - handle both mock and real drafts
            pick_numbers = [p.get('pick_no', 0) for p in picks if p.get('pick_no')]
            
            if pick_numbers:
                highest_pick = max(pick_numbers)
                pick_set = set(pick_numbers)
                
                # Check if there are gaps (mock draft issue)
                expected_picks = set(range(1, highest_pick + 1))
                missing_picks = expected_picks - pick_set
                
                if missing_picks:
                    # Mock draft with gaps - find first missing pick
                    current_pick_count = min(missing_picks) - 1
                    print(f"⚠️ Mock draft detected - gaps in picks: {sorted(list(missing_picks))[:5]}...")
                else:
                    # Real draft or complete sequence - use highest pick
                    current_pick_count = highest_pick
            else:
                current_pick_count = 0
            
            # Debug: Show actual current state
            print(f"📊 Fresh draft state: Next pick #{current_pick_count + 1} (found {len(picks)} picks, highest #{max(pick_numbers) if pick_numbers else 0})")
            
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
                
                # Find user's next pick with better logging
                current_round = (current_pick_count // teams) + 1
                print(f"🔄 Snake draft calculation: Current round {current_round}, pick #{current_pick_count + 1}")
                
                for round_check in range(current_round, current_round + 3):  # Check next few rounds
                    user_pick_in_round = get_user_pick_in_round(round_check, user_roster_id, teams)
                    print(f"  Round {round_check}: User picks at #{user_pick_in_round}")
                    
                    if user_pick_in_round > current_pick_count:
                        user_next_pick_number = user_pick_in_round
                        picks_until_user = user_pick_in_round - current_pick_count - 1
                        print(f"✅ Next user pick: #{user_next_pick_number} ({picks_until_user} picks away)")
                        break
                else:
                    print(f"⚠️ Could not calculate next pick for user in slot {user_roster_id}")
                
            # Extract user's roster from picks
            user_roster = [p for p in picks if p.get('draft_slot') == user_roster_id]
            if not user_roster:  # Fallback to roster_id field
                user_roster = [p for p in picks if p.get('roster_id') == user_roster_id]
            
            print(f"👤 User roster: {len(user_roster)} picks for slot {user_roster_id}")
            
            # Update context
            self.session_context.update({
                "draft_picks": picks,
                "available_players": available_players,  # Already limited to 50
                "current_pick": current_pick_count + 1,
                "user_next_pick": user_next_pick_number,
                "picks_until_user": picks_until_user,
                "user_roster": user_roster  # Add user roster to context
            })
            
            # Track new picks
            new_picks = []
            if current_pick_count > self.last_pick_count:
                new_picks = picks[self.last_pick_count:]
                self.last_pick_count = current_pick_count
            
            # Check for proactive recommendations
            proactive_result = await self.check_proactive_recommendations()
            
            # Debug logging for proactive
            if proactive_result.get("proactive_generated"):
                print(f"✅ PROACTIVE GENERATED: {proactive_result.get('trigger_type')} at {proactive_result.get('picks_ahead')} picks away")
            else:
                print(f"⏭️ No proactive generated - picks_until: {picks_until_user}, current: {current_pick_count + 1}, last_proactive: {self.session_context.get('last_proactive_pick')}")
            
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
        # Always log the check attempt
        print(f"🔍 Proactive check attempt - draft_active: {self.draft_active}, picks_until_user: {self.session_context.get('picks_until_user')}")
        
        if not self.draft_active or self.session_context.get("picks_until_user") is None:
            print(f"🚫 Proactive check skipped - draft not active or picks_until_user is None")
            return {}
        
        picks_until_user = self.session_context.get("picks_until_user", 999)
        current_pick = self.session_context.get("current_pick", 1)
        last_proactive = self.session_context.get("last_proactive_pick")
        
        print(f"🔍 Proactive check - picks_until: {picks_until_user}, current: {current_pick}, last_proactive: {last_proactive}")
        
        # Generate proactive recommendations at 6 picks and 3 picks ahead
        # Use <= to handle cases where polling might miss exact number
        should_generate = False
        trigger_type = None
        
        # Check if we should generate initial recommendation (around 6 picks ahead)
        if picks_until_user <= 6 and picks_until_user >= 5 and (not last_proactive or current_pick - last_proactive > 3):
            should_generate = True
            trigger_type = "initial"
        # Check if we should generate revision recommendation (around 3 picks ahead)
        elif picks_until_user <= 3 and picks_until_user >= 2 and (not last_proactive or current_pick - last_proactive > 2):
            should_generate = True
            trigger_type = "revision"
        # Check if it's user's turn RIGHT NOW (0 picks away)
        elif picks_until_user == 0 and (not last_proactive or current_pick - last_proactive > 0):
            should_generate = True
            trigger_type = "at_pick"
        
        if not should_generate:
            return {}
        
        try:
            print(f"🎯 Generating proactive recommendations ({trigger_type}) - {picks_until_user} picks until your turn")
            
            # Generate recommendations proactively - ensure we have player data
            # First, make sure we have available players
            available_players = self.session_context.get('available_players', [])
            if not available_players:
                print("⚠️ No available players in context, fetching fresh data...")
                draft_id = self.session_context.get("draft_id")
                if draft_id:
                    available_players = await self.sleeper_client.get_available_players(draft_id)
                    available_players = available_players[:50] if available_players else []
                    self.session_context['available_players'] = available_players
            
            # FAST proactive recommendation - skip AI for speed, just format available players
            # Get user's roster to understand needs
            draft_picks = self.session_context.get('draft_picks', [])
            user_roster_id = self.session_context.get('user_roster_id')
            user_next_pick = self.session_context.get('user_next_pick', current_pick + picks_until_user + 1)
            
            # Sleeper uses 'draft_slot' which matches our roster_id
            user_roster = [p for p in draft_picks if p.get('draft_slot') == user_roster_id]
            
            # If that doesn't work, try roster_id
            if not user_roster:
                user_roster = [p for p in draft_picks if p.get('roster_id') == user_roster_id]
            
            print(f"📊 Found {len(user_roster)} picks for user roster {user_roster_id}")
            
            # Debug: Show what we found
            if user_roster:
                for p in user_roster[:3]:
                    name = f"{p.get('metadata', {}).get('first_name', '')} {p.get('metadata', {}).get('last_name', '')}"
                    pos = p.get('metadata', {}).get('position', '?')
                    print(f"  - {name} ({pos})")
            
            # Count positions in roster
            position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'K': 0, 'DEF': 0}
            for pick in user_roster:
                pos = pick.get('metadata', {}).get('position', '')
                if pos in position_counts:
                    position_counts[pos] += 1
            
            # Determine needs based on roster - PRIORITY ORDER MATTERS!
            # Get current round (assuming 12 teams)
            current_round = (current_pick - 1) // 12 + 1
            
            needs = []
            # Core positions first (never K/DEF early)
            if position_counts['QB'] < 2:  # SUPERFLEX needs 2+ QBs
                needs.append('QB')
            if position_counts['WR'] < 5:  # 3 WR league needs depth
                needs.append('WR')
            if position_counts['RB'] < 4:
                needs.append('RB')
            if position_counts['TE'] < 2:  # Need starter + backup
                needs.append('TE')
            
            # Only consider K/DEF in late rounds (15+)
            if current_round >= 15:
                if position_counts['K'] == 0:
                    needs.append('K')
                if position_counts['DEF'] == 0:
                    needs.append('DEF')
            
            # Get top 3 recommendations in proper format
            recommendations = []
            available_by_need = []
            
            # In rounds 9+, start blending keeper value with rankings (graduated scale)
            if current_round >= 9:
                # Determine keeper value weight based on round
                if current_round <= 10:
                    keeper_weight = 0.1  # 10% keeper, 90% rankings
                    keeper_multiplier = 1.0
                elif current_round <= 12:
                    keeper_weight = 0.3  # 30% keeper, 70% rankings
                    keeper_multiplier = 1.2
                elif current_round <= 14:
                    keeper_weight = 0.5  # 50% keeper, 50% rankings
                    keeper_multiplier = 1.4
                else:  # Rounds 15-17
                    keeper_weight = 0.7  # 70% keeper, 30% rankings
                    keeper_multiplier = 1.6
                
                ranking_weight = 1.0 - keeper_weight
                
                # Apply round-based multipliers and calculate blended scores
                for player in available_players[:30]:  # Check top 30 for keeper value
                    positions = player.get('positions', [])
                    
                    # K and DEF have no keeper value - use pure rankings
                    if 'K' in positions or 'DEF' in positions:
                        keeper_base = 0
                        actual_keeper_weight = 0
                        actual_ranking_weight = 1.0
                    else:
                        keeper_base = player.get('keeper_base_score', 0) * keeper_multiplier
                        actual_keeper_weight = keeper_weight
                        actual_ranking_weight = ranking_weight
                    
                    # Convert rank to score (lower rank = higher score)
                    rank_score = 200 - min(player.get('rank', 999), 200)
                    
                    # Calculate blended score
                    player['blended_score'] = (actual_ranking_weight * rank_score) + (actual_keeper_weight * keeper_base)
                    player['adjusted_keeper_score'] = keeper_base  # Store for display
                
                # Re-sort by blended score for rounds 9+
                available_players = sorted(available_players[:30], key=lambda x: x.get('blended_score', 0), reverse=True)
            
            for i, pos in enumerate(needs[:3]):  # Top 3 needs
                pos_players = [p for p in available_players if pos in p.get('positions', [])]
                if pos_players:
                    # Format like the chat recommendations
                    emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else "•"
                    best_player = pos_players[0]
                    player_name = best_player.get('name', 'Unknown')
                    
                    # Add keeper indicator based on keeper value and round
                    if current_round >= 9:
                        keeper_score = best_player.get('keeper_base_score', 0)
                        if keeper_score >= 150:
                            player_name += " 🔥"  # Elite keeper value
                        elif keeper_score >= 100:
                            player_name += " 🔒"  # Great keeper value
                        elif keeper_score >= 60:
                            player_name += " 📈"  # Good keeper value
                    
                    # Add to list for formatting
                    available_by_need.append((pos, player_name, pos_players[:3]))
            
            # Build formatted recommendations with reasoning
            if available_by_need:
                for i, (pos, player_full, alternatives) in enumerate(available_by_need):
                    emoji = ["🥇", "🥈", "🥉"][i]
                    
                    # Extract player name without emoji for lookup
                    player_clean = player_full.split(' 🔥')[0].split(' 🔒')[0].split(' 📈')[0]
                    
                    # Find the player data to get reasoning
                    player_data = None
                    for p in alternatives:
                        if p.get('name', '') == player_clean:
                            player_data = p
                            break
                    
                    # Build reasoning based on round and player attributes
                    reasoning = []
                    if current_round >= 9 and player_data:
                        # Skip keeper reasoning for K and DEF
                        positions = player_data.get('positions', [])
                        if 'K' not in positions and 'DEF' not in positions:
                            keeper_score = player_data.get('keeper_base_score', 0)
                            if keeper_score >= 150:
                                reasoning.append("elite keeper")
                            elif keeper_score >= 100:
                                reasoning.append("strong keeper")
                            elif keeper_score >= 60:
                                reasoning.append("keeper upside")
                        
                        # Add rookie/age context (skip for K/DEF)
                        if 'K' not in positions and 'DEF' not in positions:
                            years_exp = player_data.get('years_exp', 99)
                            if years_exp == 0:
                                reasoning.append("rookie")
                            elif years_exp <= 2:
                                reasoning.append(f"year {years_exp + 1}")
                    
                    # Add value context
                    player_rank = player_data.get('rank', 999) if player_data else 999
                    if player_rank < current_pick - 10:
                        reasoning.append("good value")
                    
                    # Add position-specific reasoning
                    if pos == 'QB' and position_counts['QB'] < 2:
                        reasoning.append("SUPERFLEX need")
                    elif pos == 'WR' and position_counts['WR'] < 5:
                        reasoning.append("need 3 starters")
                    elif pos == 'RB' and position_counts['RB'] < 4:
                        reasoning.append("FLEX depth")
                    elif pos == 'TE' and position_counts['TE'] < 2:
                        reasoning.append("backup TE")
                    
                    # Check for stack opportunities
                    if player_data and pos in ['WR', 'TE']:
                        # Check if player stacks with user's QBs
                        for qb_pick in user_roster:
                            if qb_pick.get('metadata', {}).get('position') == 'QB':
                                qb_team = qb_pick.get('metadata', {}).get('team')
                                player_team = player_data.get('team')
                                if qb_team and player_team and qb_team == player_team:
                                    qb_name = f"{qb_pick.get('metadata', {}).get('first_name', '')} {qb_pick.get('metadata', {}).get('last_name', '')}".strip()
                                    reasoning.append(f"stacks w/{qb_name}")
                                    break
                    
                    reason_str = f" ({', '.join(reasoning)})" if reasoning else ""
                    alt_names = ', '.join([p.get('name', 'Unknown') for p in alternatives[1:3]]) if len(alternatives) > 1 else ''
                    
                    if alt_names:
                        rec_text = f"\n{emoji} **{player_full} ({pos})**{reason_str}\n   Alternatives: {alt_names}"
                        recommendations.append(rec_text)
                    else:
                        rec_text = f"\n{emoji} **{player_full} ({pos})**{reason_str}"
                        recommendations.append(rec_text)
            
            # Build fast recommendation
            roster_summary = f"{position_counts['QB']} QB, {position_counts['RB']} RB, {position_counts['WR']} WR, {position_counts['TE']} TE"
            if position_counts['K'] > 0 or position_counts['DEF'] > 0:
                roster_summary += f", {position_counts['K']} K, {position_counts['DEF']} DEF"
            
            # Add keeper value context for rounds 9+
            keeper_context = ""
            if current_round >= 9:
                if current_round <= 10:
                    keeper_context = "\n**Strategy**: Starting to consider keeper value (10% weight) 📊"
                elif current_round <= 12:
                    keeper_context = "\n**Strategy**: Balancing talent with keeper upside (30% weight) 🎯"
                elif current_round <= 14:
                    keeper_context = "\n**Strategy**: Equal focus on 2025 and keeper value (50% weight) ⚖️"
                else:
                    keeper_context = "\n**Strategy**: Prioritizing 2026 keeper potential (70% weight) 🚀"
            
            recommendation = f"""
📊 **Proactive Analysis** (Pick #{user_next_pick} - {picks_until_user} picks away)

**Your Roster**: {roster_summary}
**Current Round**: {current_round}{keeper_context}

**Top 3 Recommendations**:
{''.join(recommendations) if recommendations else '⏳ Analyzing available players...'}

**Position Priorities**:
• {"✅" if position_counts['QB'] >= 2 else "⚠️"} QB: {"Good depth" if position_counts['QB'] >= 2 else "Need starter/depth"}
• {"✅" if position_counts['WR'] >= 4 else "⚠️"} WR: {"Good depth" if position_counts['WR'] >= 4 else "CRITICAL - need 3 starters + FLEX"}
• {"✅" if position_counts['RB'] >= 3 else "⚠️"} RB: {"Good depth" if position_counts['RB'] >= 3 else "Need depth for injuries"}
• {"✅" if position_counts['TE'] >= 1 else "⚠️"} TE: {"Starter secured" if position_counts['TE'] >= 1 else "Need starter"}
{"• K/DEF: Wait until rounds 15-17" if current_round < 15 else f"• K/DEF: Time to draft ({position_counts['K']} K, {position_counts['DEF']} DEF) - {'✅ K filled' if position_counts['K'] > 0 else '⚠️ Need K'} | {'✅ DEF filled' if position_counts['DEF'] > 0 else '⚠️ Need DEF'}"}

**Available Players** (Top 10):
{chr(10).join([f"• {p.get('name', 'Unknown')} ({', '.join(p.get('positions', ['?']))})" for p in available_players[:10]])}
"""
            
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

    def _parse_and_store_adps(self, rankings_data: str):
        """
        Parse ADP values from rankings data and store in session context
        
        Args:
            rankings_data: Raw rankings text with ADP values
        """
        if not rankings_data:
            print("⚠️ No rankings data to parse for ADPs")
            return
            
        adps = {}
        lines = rankings_data.split('\n')
        
        for line in lines:
            if 'ADP:' in line:
                try:
                    # Parse line like "Player Name (POS) - Rank: X, ADP: Y, Team: Z"
                    name_part = line.split(' (')[0].strip()
                    adp_part = line.split('ADP:')[1].split(',')[0].strip()
                    adps[name_part] = float(adp_part)
                except:
                    continue
        
        # Store in session context for later use
        self.session_context['player_adps'] = adps
        print(f"📊 Parsed {len(adps)} player ADPs for value detection")
    
    def _calculate_adp_value(self, player_name: str, current_pick: int) -> float:
        """
        Calculate how much value a player represents based on ADP vs current pick
        
        Positive score = player falling (good value)
        Negative score = reaching for player
        
        Args:
            player_name: Name of the player
            current_pick: Current draft pick number
            
        Returns:
            Value score from -50 to +50
        """
        # Get player's ADP from stored data
        player_adp = self.session_context.get('player_adps', {}).get(player_name, current_pick)
        
        # Calculate how many picks the player has fallen or risen
        value_differential = player_adp - current_pick
        
        # Scale the value score
        if value_differential > 0:
            # Player has fallen - this is good value!
            # Log scale for significance (falling 20 picks is better than linear)
            import math
            value_score = min(50, math.log(1 + value_differential) * 10)
        else:
            # We're reaching for this player
            value_score = max(-50, value_differential / 2)
            
        return value_score
    
    def _detect_positional_run(self) -> Optional[str]:
        """
        Check if a positional run is happening (3+ of same position in last 6 picks)
        
        Returns:
            Position being run on (e.g., "RB") or None
        """
        recent_picks = self.session_context.get('recent_picks', [])
        if len(recent_picks) < 6:
            return None
            
        # Count positions in last 6 picks
        position_counts = {}
        for pick in recent_picks[-6:]:
            pos = pick.get('metadata', {}).get('position', '')
            if pos:
                position_counts[pos] = position_counts.get(pos, 0) + 1
        
        # Check if any position has 3+ selections (that's a run!)
        for pos, count in position_counts.items():
            if count >= 3:
                return pos
                
        return None
    
    def _get_qb_wr_stacks(self, available_players: List[Dict]) -> List[Dict]:
        """
        Find QB-WR/TE stacking opportunities with QBs on roster
        
        Stacking QB with pass catchers increases ceiling for both
        
        Args:
            available_players: List of available players
            
        Returns:
            List of stacking opportunities with bonus scores
        """
        stacking_opportunities = []
        user_roster = self.session_context.get('user_roster', [])
        
        # Find QBs on our roster
        roster_qbs = []
        for player in user_roster:
            if player.get('metadata', {}).get('position') == 'QB':
                roster_qbs.append({
                    'name': f"{player.get('metadata', {}).get('first_name', '')} {player.get('metadata', {}).get('last_name', '')}",
                    'team': player.get('metadata', {}).get('team', '')
                })
        
        # Look for available WRs/TEs from same team
        for qb in roster_qbs:
            if not qb['team']:
                continue
                
            for player in available_players[:30]:  # Check top 30 available
                player_team = player.get('team', '')
                player_positions = player.get('positions', [])
                
                if player_team == qb['team'] and any(pos in ['WR', 'TE'] for pos in player_positions):
                    stacking_opportunities.append({
                        'player_name': player.get('name', 'Unknown'),
                        'qb_name': qb['name'],
                        'team': player_team,
                        'stack_bonus': 5.0  # Bonus points for stacking
                    })
                    
        return stacking_opportunities
    
    def _evaluate_keeper_value(self, player_name: str, current_round: int) -> float:
        """
        Evaluate a player's keeper value for next year
        Focus on late-round values and breakout candidates
        
        Args:
            player_name: Name of the player
            current_round: Current draft round
            
        Returns:
            Keeper value score (0-20)
        """
        keeper_score = 0.0
        
        # Late round multiplier (rounds 8+ have more keeper value)
        if current_round >= 8:
            keeper_score += (current_round - 7) * 2
        
        # Look for rookie/young player indicators in name
        # (In production, would use actual age/experience data)
        rookie_indicators = ['jr', 'iii', 'ii', 'rookie']
        name_lower = player_name.lower()
        
        if any(indicator in name_lower for indicator in rookie_indicators):
            keeper_score += 5
            
        # Max keeper score at 20
        return min(20, keeper_score)
    
    def _get_superflex_round_strategy(self, round_num: int) -> str:
        """
        Get SUPERFLEX-specific strategy for current round based on decision tree
        
        Args:
            round_num: Current round number (1-16)
            
        Returns:
            Strategy string with specific priorities
        """
        user_roster = self.session_context.get('user_roster', [])
        
        # Count positions on roster
        qb_count = sum(1 for p in user_roster if p.get('metadata', {}).get('position') == 'QB')
        rb_count = sum(1 for p in user_roster if p.get('metadata', {}).get('position') == 'RB')
        wr_count = sum(1 for p in user_roster if p.get('metadata', {}).get('position') == 'WR')
        te_count = sum(1 for p in user_roster if p.get('metadata', {}).get('position') == 'TE')
        
        # Round-specific SUPERFLEX strategy based on your decision tree
        strategies = {
            1: "🎯 ROUND 1: Target elite QB (Allen/Hurts/Lamar/Mahomes) if available, else elite RB/WR",
            
            2: f"🎯 ROUND 2: {('MUST GET QB - Target Tier 1-2 (Herbert/Stroud/Burrow)' if qb_count == 0 else 'Elite QB if available OR top-tier RB/WR')}",
            
            3: f"🎯 ROUND 3: {('CRITICAL - Secure QB2 now (even slight reach)' if qb_count < 2 else 'Best RB/WR by tier value')}",
            
            4: f"🎯 ROUND 4: {('LAST CHANCE - Take ANY starting QB!' if qb_count < 2 else 'Target bell-cow RB or high-volume WR')}",
            
            5: "🎯 ROUND 5: High-upside RB/WR, consider QB3 only if injury-prone starters",
            
            6: "🎯 ROUND 6: Continue building RB/WR depth, QB3 only at extreme value",
            
            7: f"🎯 ROUND 7: RB/WR depth priority{', grab top-8 TE if available' if te_count == 0 else ''}",
            
            8: "🎯 ROUND 8: Depth picks with keeper value - target young breakouts",
            
            9: "🎯 ROUND 9: Last chance for potential starters",
            
            10: "🎯 ROUND 10: Handcuffs for your RBs + high-upside WRs",
            
            11: "🎯 ROUND 11: Rookie QBs with starting potential + breakout WRs",
            
            12: "🎯 ROUND 12: Pure upside plays - swing for ceiling",
            
            13: "🎯 ROUND 13: Continue skill position depth - high upside rookies/handcuffs",
            
            14: "🎯 ROUND 14: Final skill position lottery tickets before K/DEF",
            
            15: "🎯 ROUND 15: DST with easy Weeks 1-3 schedule (weak opposing QBs)",
            
            16: "🎯 ROUND 16: Kicker from high-scoring offense (prefer dome/warm weather)"
        }
        
        return strategies.get(round_num, "Best player available with upside")
    
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
    
    async def _handle_keeper_question(self, question: str) -> str:
        """
        Handle questions specifically about keeper value
        
        Returns top keeper targets from available players
        """
        print("🔒 Analyzing keeper value specifically...")
        
        available_players = self.session_context.get('available_players', [])
        current_pick = self.session_context.get('current_pick', 1)
        current_round = (current_pick - 1) // 12 + 1  # Assuming 12 teams
        
        if not available_players:
            return "No available players to analyze for keeper value."
        
        # Filter and score players by keeper value
        keeper_candidates = []
        for player in available_players[:50]:  # Check top 50 available
            keeper_base = player.get('keeper_base_score', 0)
            if keeper_base > 0:  # Only consider players with keeper value
                # Apply round multiplier for accurate current value
                if current_round >= 11:
                    keeper_base *= 1.2
                if current_round >= 14:
                    keeper_base *= 1.5
                
                keeper_candidates.append({
                    'name': player.get('name', 'Unknown'),
                    'positions': player.get('positions', []),
                    'years_exp': player.get('years_exp', 99),
                    'keeper_score': keeper_base,
                    'rank': player.get('rank', 999)
                })
        
        # Sort by keeper score
        keeper_candidates.sort(key=lambda x: x['keeper_score'], reverse=True)
        
        # Build response
        response = f"""
🔒 **Top Keeper Targets Available**

**Current Round**: {current_round}
**Keeper Strategy**: {"Heavy focus (rounds 15+)" if current_round >= 15 else "Balanced approach (rounds 11-14)" if current_round >= 11 else "Starting to consider (rounds 9-10)" if current_round >= 9 else "Focus on 2025 value first"}

**Top 10 Keeper Value Players**:
"""
        
        for i, player in enumerate(keeper_candidates[:10], 1):
            emoji = "🔥" if player['keeper_score'] >= 150 else "🔒" if player['keeper_score'] >= 100 else "📈"
            years_str = "Rookie" if player['years_exp'] == 0 else f"Year {player['years_exp'] + 1}"
            pos_str = "/".join(player['positions'])
            response += f"\n{i}. **{player['name']}** ({pos_str}) - {years_str} {emoji}"
            response += f"\n   Keeper Score: {player['keeper_score']:.0f} | Current Rank: {player['rank']}"
        
        # Add keeper rules reminder
        response += """

**Your League's Keeper Rules**:
• 3 keepers allowed each season
• Rounds 1-3: Cannot be kept
• Rounds 4-10: Keep for 1 round earlier
• Rounds 11-17: Keep for 2 rounds earlier

**Key Targets**:
• Rookie QBs (highest SUPERFLEX value)
• Rookie RBs with opportunity
• 2nd/3rd year WR breakouts
• Young TEs with upside
"""
        
        return response


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