"""
Unified Fantasy Agent Server - Simplified Version
Uses existing working agents directly
"""

import os
import sys
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# CRITICAL: Load environment variables FIRST before any imports
from dotenv import load_dotenv
load_dotenv('.env.local')
load_dotenv('.env')

# Set environment variable for CrewAI
if os.getenv("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")

# Import draft monitor
from core.draft_monitor import draft_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Fantasy Agent Unified Server")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class PlatformSelection(BaseModel):
    platform: str
    league_id: Optional[str] = None
    draft_id: Optional[str] = None

class DraftQuery(BaseModel):
    platform: str
    query: str
    context: Optional[Dict[str, Any]] = None

class DraftConnection(BaseModel):
    platform: str
    url: str
    draft_slot: Optional[int] = None  # For Sleeper and Yahoo Snake
    team_name: Optional[str] = None   # For Yahoo Auction

class DraftStatusRequest(BaseModel):
    platform: str
    url: Optional[str] = None

# Global state
class ServerState:
    def __init__(self):
        self.active_platform: Optional[str] = None
        self.sleeper_crew = None
        self.yahoo_snake_agent = None
        self.sleeper_auction_agent = None
        
    def get_sleeper_crew(self):
        """Get or create Sleeper CrewAI agent"""
        if self.sleeper_crew is None:
            try:
                from platforms.sleeper.agents.draft_crew import FantasyDraftCrew
                # Pass the API key explicitly
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not found in environment")
                self.sleeper_crew = FantasyDraftCrew(anthropic_api_key=api_key)
                logger.info("Sleeper CrewAI agent initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Sleeper agent: {e}")
                raise
        return self.sleeper_crew
    
    def get_yahoo_snake_agent(self):
        """Get or create Yahoo Snake agent"""
        if self.yahoo_snake_agent is None:
            try:
                from platforms.yahoo.agents.yahoo_snake_agent import YahooSnakeDraftAgent
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not found")
                self.yahoo_snake_agent = YahooSnakeDraftAgent(anthropic_api_key=api_key)
                logger.info("Yahoo Snake agent initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Yahoo Snake agent: {e}")
                # Return a mock agent for now
                class MockAgent:
                    async def get_recommendation(self, query, context):
                        return f"Yahoo Snake agent not available. Your query: {query}"
                self.yahoo_snake_agent = MockAgent()
        return self.yahoo_snake_agent
    
    def get_sleeper_auction_agent(self):
        """Get or create Sleeper Auction agent"""
        if self.sleeper_auction_agent is None:
            try:
                # Use the Sleeper auction agent 
                from platforms.sleeper.agents.sleeper_auction_agent import SleeperAuctionAgent
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not found")
                self.sleeper_auction_agent = SleeperAuctionAgent(anthropic_api_key=api_key)
                logger.info("Sleeper Auction agent initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Sleeper Auction agent: {e}")
                # Return a mock agent for now
                class MockAgent:
                    async def get_bid_recommendation(self, context):
                        return f"Sleeper Auction agent not available: {str(e)}"
                    async def get_recommendation(self, query, context):
                        return f"Sleeper Auction agent not available. Your query: {query}"
                self.sleeper_auction_agent = MockAgent()
        return self.sleeper_auction_agent

# Initialize server state
state = ServerState()

def calculate_next_pick(current_pick: int, user_slot: int, num_teams: int) -> int:
    """Calculate next pick for a user in snake draft"""
    # If draft hasn't started
    if current_pick == 0:
        return user_slot
    
    # Calculate which round we're in
    current_round = ((current_pick - 1) // num_teams) + 1
    pick_in_round = ((current_pick - 1) % num_teams) + 1
    
    # Check if it's currently user's turn
    if current_round % 2 == 1:  # Odd round (forward)
        if pick_in_round == user_slot:
            # User is currently picking, next pick is in next round
            if current_round == 16:  # Last round
                return 0  # No more picks
            return user_slot + (num_teams * 2) - (2 * user_slot) + 1 + (current_pick - user_slot)
    else:  # Even round (reverse)
        reverse_slot = num_teams - user_slot + 1
        if pick_in_round == reverse_slot:
            # User is currently picking
            if current_round == 16:
                return 0
            return current_pick + (2 * user_slot) - 1
    
    # Find next pick for user
    picks_made = current_pick
    
    while picks_made < num_teams * 16:  # 16 rounds total
        picks_made += 1
        round_num = ((picks_made - 1) // num_teams) + 1
        pick_in_round = ((picks_made - 1) % num_teams) + 1
        
        if round_num % 2 == 1:  # Odd round
            if pick_in_round == user_slot:
                return picks_made
        else:  # Even round
            if pick_in_round == (num_teams - user_slot + 1):
                return picks_made
    
    return 0  # No more picks

@app.on_event("startup")
async def startup_event():
    """Initialize server on startup"""
    logger.info("Fantasy Agent Unified Server starting...")
    logger.info(f"ANTHROPIC_API_KEY present: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
    
    # Pre-initialize Sleeper agent for faster first query
    try:
        crew = state.get_sleeper_crew()
        if hasattr(crew, 'agents') and crew.agents is None:
            crew.agents = crew._create_agents()
            logger.info("Sleeper agents pre-initialized")
    except Exception as e:
        logger.warning(f"Could not pre-initialize Sleeper agents: {e}")
    
    logger.info("Server ready!")

@app.get("/")
async def root():
    """Serve the unified UI"""
    with open("templates/unified.html", "r") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.post("/api/select-platform")
async def select_platform(selection: PlatformSelection):
    """Select and initialize the active platform"""
    try:
        state.active_platform = selection.platform
        
        # Test that we can initialize the agent
        if selection.platform == "sleeper":
            state.get_sleeper_crew()
        elif selection.platform == "yahoo-snake":
            state.get_yahoo_snake_agent()
        elif selection.platform == "sleeper-auction":
            state.get_sleeper_auction_agent()
        
        return JSONResponse({
            "status": "success",
            "platform": selection.platform,
            "message": f"Connected to {selection.platform}"
        })
        
    except Exception as e:
        logger.error(f"Failed to select platform: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.post("/api/draft-query")
async def draft_query(query: DraftQuery):
    """Process a draft query for the active platform"""
    try:
        logger.info(f"Processing query for {query.platform}: {query.query}")
        
        # Add draft context if connected
        context = query.context or {}
        if query.platform in draft_monitor.connected_drafts:
            draft_info = draft_monitor.connected_drafts[query.platform]
            context["draft_slot"] = draft_info.get("draft_slot")
            context["draft_id"] = draft_info.get("draft_id")
            
            # Get current draft status
            status = await draft_monitor.get_draft_status(query.platform)
            if status.get("status") == "success":
                context["current_pick"] = status.get("draftStatus", {}).get("currentPick", 1)
                context["current_round"] = status.get("draftStatus", {}).get("round", 1)
                context["round"] = status.get("draftStatus", {}).get("round", 1)  # Yahoo agent expects 'round'
                context["pick_number"] = status.get("draftStatus", {}).get("currentPick", 1)  # Yahoo agent expects 'pick_number'
                context["my_turn"] = status.get("draftStatus", {}).get("myTurn", False)
                context["roster"] = status.get("roster", [])  # Use 'roster' key
                context["my_roster"] = status.get("roster", [])  # Also set my_roster for backward compatibility
                context["user_roster"] = status.get("roster", [])  # Yahoo agent expects user_roster
                
                # CRITICAL: Pass full draft data for CrewAI context
                context["draft_picks"] = status.get("draftPicks", [])
                context["available_players"] = status.get("availablePlayers", [])
                context["recent_picks"] = status.get("recentPicks", [])
                
                # CRITICAL for Yahoo: Pass drafted player names for filtering
                context["drafted_player_names"] = status.get("draftedPlayerNames", [])
                context["all_picks"] = status.get("allPicks", [])
                
                # Add draft completion flag
                total_picks = status.get("draftStatus", {}).get("totalPicks", 204)
                if context["current_pick"] > total_picks:
                    context["draft_complete"] = True
                    logger.info(f"Draft is complete with {len(context['roster'])} players on roster")
        
        if query.platform == "sleeper":
            crew = state.get_sleeper_crew()
            # Use the analyze_draft_question method which is async
            result = await crew.analyze_draft_question(query.query, context)
            
        elif query.platform == "yahoo-snake":
            agent = state.get_yahoo_snake_agent()
            # Pass the query and context
            context["query"] = query.query
            result = await agent.get_recommendation(context)
            
            # Format Yahoo Snake response for natural language display
            if isinstance(result, dict):
                recs = result.get('recommendations', [])
                if recs:
                    formatted = f"Based on your Full PPR league settings, here are my top recommendations:\n\n"
                    for i, rec in enumerate(recs, 1):
                        formatted += f"**{i}. {rec['name']} ({rec['position']})** - {rec['reason']}\n\n"
                    
                    if result.get('strategy_notes'):
                        formatted += f"📊 **Strategy Note:** {result['strategy_notes']}\n"
                    
                    if result.get('response_ms'):
                        formatted += f"\n⚡ Response time: {result['response_ms']}ms"
                else:
                    formatted = "I need more context to provide recommendations. Please specify your round, pick position, and current roster."
                result = formatted
            
        elif query.platform == "sleeper-auction":
            agent = state.get_sleeper_auction_agent()
            # Sleeper Auction agent uses get_bid_recommendation
            context = query.context or {}
            context["query"] = query.query
            
            # Get current draft status if connected
            if query.platform in draft_monitor.connected_drafts:
                draft_status = await draft_monitor.get_draft_status(query.platform)
                if draft_status.get("status") == "success":
                    # Add auction-specific context
                    my_roster = draft_status.get("myRoster", [])
                    context.update({
                        "current_player": draft_status.get("draftStatus", {}).get("currentPlayer"),
                        "current_bid": draft_status.get("draftStatus", {}).get("currentBid", 0),
                        "my_budget": draft_status.get("draftStatus", {}).get("myBudget", 200),
                        "avg_budget": draft_status.get("draftStatus", {}).get("avgBudget", 200),
                        "user_roster": my_roster,
                        "roster_size": len(my_roster),
                        "recent_purchases": draft_status.get("recentPurchases", []),
                        "team_budgets": draft_status.get("teamBudgets", {})
                    })
                    logger.info(f"Auction context: Budget ${context['my_budget']}, Roster size: {len(my_roster)}")
            
            result = await agent.get_bid_recommendation(context)
            
            # Format Yahoo Auction response for natural language display
            if isinstance(result, dict):
                formatted = ""
                
                # Handle bid recommendations
                if result.get('bid'):
                    bid = result['bid']
                    if bid.get('amount'):
                        formatted = f"I recommend bidding **{bid['amount']}** on this player"
                        if bid.get('max'):
                            formatted += f" (max: {bid['max']})"
                        if bid.get('reason'):
                            formatted += f". {bid['reason']}"
                        formatted += "\n\n"
                
                # Handle nomination suggestions
                if result.get('nomination'):
                    nom = result['nomination']
                    if nom.get('type') == 'DRAIN':
                        formatted += f"💡 **Nomination Strategy:** I suggest nominating a {', '.join(nom.get('positions', ['player']))} "
                        formatted += f"in the {nom.get('price_range', '$20-30')} range to drain opponent budgets. "
                        formatted += f"{nom.get('reason', '')}\n\n"
                    elif nom.get('type') == 'VALUE':
                        formatted += f"🎯 **Value Nomination:** Target {', '.join(nom.get('positions', ['players']))} "
                        formatted += f"in the {nom.get('price_range', '$10-20')} range. "
                        formatted += f"{nom.get('reason', '')}\n\n"
                    else:
                        formatted += f"Consider nominating {', '.join(nom.get('positions', ['players']))} "
                        formatted += f"for {nom.get('price_range', 'market value')}. "
                        formatted += f"{nom.get('reason', '')}\n\n"
                
                # Add strategy context
                if result.get('phase'):
                    formatted += f"📈 Current auction phase: **{result['phase']}**\n"
                
                if not formatted:
                    formatted = "Please provide more context about the auction (current player, your budget, roster needs) for specific recommendations."
                
                result = formatted
        else:
            result = "Unknown platform"
        
        return JSONResponse({
            "status": "success",
            "response": result,
            "platform": query.platform
        })
        
    except Exception as e:
        logger.error(f"Draft query error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    logger.info(f"WebSocket connected")
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "platform_select":
                await websocket.send_json({
                    "type": "platform_changed",
                    "platform": data.get("platform")
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

@app.get("/api/rankings/{platform}")
async def get_rankings(platform: str):
    """Get rankings for specific platform"""
    try:
        from core.official_fantasypros import OfficialFantasyProsMCP
        
        # Platform-specific settings - CRITICAL: Only Sleeper uses OP for SUPERFLEX!
        settings = {
            "sleeper": {"position": "OP", "scoring": "HALF"},      # SUPERFLEX rankings
            "yahoo-snake": {"position": "ALL", "scoring": "PPR"},   # Standard Full PPR (uses FLEX internally)
            "sleeper-auction": {"position": "ALL", "scoring": "HALF"} # Standard Half PPR (uses FLEX internally)
        }
        
        platform_settings = settings.get(platform, {"position": "ALL", "scoring": "HALF"})
        
        client = OfficialFantasyProsMCP()
        # Use async method to get rankings (returns a list directly)
        rankings = await client.get_rankings(
            position=platform_settings["position"],
            scoring=platform_settings["scoring"],
            limit=500  # Get top 500 players for UI
        )
        # Rankings is already a list
        if not rankings:
            rankings = []
        
        return JSONResponse(rankings if rankings else [])
        
    except Exception as e:
        logger.error(f"Rankings error: {e}")
        # Return mock data so UI doesn't break
        return JSONResponse([
            {"player_id": 1, "player_name": "Christian McCaffrey", "player_position_id": "RB", "player_team_id": "SF", "rank_ecr": 1},
            {"player_id": 2, "player_name": "CeeDee Lamb", "player_position_id": "WR", "player_team_id": "DAL", "rank_ecr": 2},
            {"player_id": 3, "player_name": "Tyreek Hill", "player_position_id": "WR", "player_team_id": "MIA", "rank_ecr": 3},
        ])

@app.post("/api/connect-draft")
async def connect_draft(connection: DraftConnection):
    """Connect to a live draft"""
    try:
        result = await draft_monitor.connect(
            connection.platform, 
            connection.url,
            draft_slot=connection.draft_slot,
            team_name=connection.team_name
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Draft connection error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.post("/api/draft-status")
async def get_draft_status(request: DraftStatusRequest):
    """Get current draft status"""
    try:
        status = await draft_monitor.get_draft_status(request.platform, request.url)
        
        # Transform data for UI if successful
        if status.get("status") == "success":
            draft_status = status.get('draftStatus', {})
            
            # Calculate next pick for snake draft
            if request.platform == "yahoo-snake":
                current_pick = draft_status.get('currentPick', 1)
                user_slot = draft_status.get('userSlot', 10)
                teams = draft_status.get('teams', 10)
                
                # Calculate next pick number for user
                next_pick = calculate_next_pick(current_pick, user_slot, teams)
                draft_status['nextPick'] = next_pick
            
            # Transform recent picks to match UI expectations
            recent_picks = status.get('recentPicks', [])
            transformed_recent = []
            for i, pick in enumerate(recent_picks):
                transformed_recent.append({
                    'id': f"pick_{i}",
                    'player': pick.get('player', 'Unknown Player'),
                    'team': pick.get('team', ''),
                    'pick': pick.get('pick', 0),
                    'position': pick.get('position', '')
                })
            status['recentPicks'] = transformed_recent
            
            # Ensure userRoster is set for UI (alias for roster)
            status['userRoster'] = status.get('roster', [])
            
            # For Yahoo, fetch top available players from FantasyPros for UI display
            if request.platform == "yahoo-snake" and not status.get('availablePlayers'):
                try:
                    from core.official_fantasypros import OfficialFantasyProsMCP
                    client = OfficialFantasyProsMCP()
                    all_rankings = await client.get_rankings(position="ALL", scoring="PPR", limit=300)
                    
                    # Filter out drafted players
                    drafted_names = status.get('draftedPlayerNames', [])
                    available = []
                    for p in all_rankings:
                        if p.get('player_name') not in drafted_names:
                            available.append({
                                'name': p.get('player_name'),
                                'position': p.get('player_position_id'),
                                'rank': p.get('rank_ecr'),
                                'team': p.get('player_team_id', '')
                            })
                            if len(available) >= 10:  # Just top 10 for UI
                                break
                    
                    status['availablePlayers'] = available
                except Exception as e:
                    logger.warning(f"Could not fetch available players for UI: {e}")
                    status['availablePlayers'] = []
            
            logger.info(f"=== DRAFT STATUS RESPONSE ===")
            logger.info(f"Current Pick: {draft_status.get('currentPick')}")
            logger.info(f"Next Pick: {draft_status.get('nextPick')}")
            logger.info(f"User Slot: {draft_status.get('userSlot')}")
            logger.info(f"Roster Count: {len(status.get('userRoster', []))}")
            
            # Get proactive recommendation if available
            recommendation = await draft_monitor.get_proactive_recommendation(
                request.platform, status
            )
            if recommendation:
                status["recommendation"] = recommendation
        
        return JSONResponse(status)
    except Exception as e:
        logger.error(f"Draft status error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.get("/api/roster/{platform}")
async def get_roster(platform: str):
    """Get user's current roster"""
    try:
        if platform not in draft_monitor.connected_drafts:
            return JSONResponse({"status": "error", "message": "Not connected to draft"})
        
        # Get draft status which includes roster
        status = await draft_monitor.get_draft_status(platform)
        
        if status.get("status") == "success":
            # Return just the roster data
            return JSONResponse({
                "status": "success",
                "roster": status.get("myRoster", []),
                "allPicks": status.get("allPicks", [])
            })
        else:
            return JSONResponse({"status": "error", "message": "Failed to get roster"})
            
    except Exception as e:
        logger.error(f"Get roster error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.get("/api/available-players/{platform}")
async def get_available_players(platform: str):
    """Get top available players (undrafted)"""
    try:
        # Get rankings for the platform
        from core.official_fantasypros import OfficialFantasyProsMCP
        
        settings = {
            "sleeper": {"position": "OP", "scoring": "HALF"},
            "yahoo-snake": {"position": "ALL", "scoring": "PPR"},
            "sleeper-auction": {"position": "ALL", "scoring": "HALF"}
        }
        
        platform_settings = settings.get(platform, {"position": "ALL", "scoring": "HALF"})
        
        client = OfficialFantasyProsMCP()
        all_rankings = await client.get_rankings(
            position=platform_settings["position"],
            scoring=platform_settings["scoring"],
            limit=300
        )
        
        # Get drafted players if connected
        drafted_players = set()
        if platform in draft_monitor.connected_drafts:
            status = await draft_monitor.get_draft_status(platform)
            if status.get("status") == "success":
                # Get all drafted player names
                all_picks = status.get("allPicks", [])
                for pick in all_picks:
                    player_name = pick.get("player", "").lower()
                    if player_name:
                        drafted_players.add(player_name)
        
        # Filter out drafted players
        available = []
        for player in all_rankings:
            player_name = player.get("player_name", "").lower()
            if player_name not in drafted_players:
                available.append(player)
            
            # Return top 50 available
            if len(available) >= 50:
                break
        
        return JSONResponse({
            "status": "success",
            "available": available,
            "totalDrafted": len(drafted_players)
        })
        
    except Exception as e:
        logger.error(f"Get available players error: {e}")
        # Return mock data so UI doesn't break
        return JSONResponse({
            "status": "success",
            "available": [],
            "totalDrafted": 0
        })

@app.post("/api/manual-pick")
async def record_manual_pick(pick: Dict[str, Any]):
    """Manually record a draft pick"""
    try:
        platform = pick.get("platform")
        player_name = pick.get("player")
        team_slot = pick.get("team")
        pick_number = pick.get("pick")
        
        # TODO: Implement manual tracking
        logger.info(f"Manual pick recorded: {player_name} to team {team_slot}")
        
        return JSONResponse({
            "status": "success",
            "message": f"Recorded {player_name}"
        })
        
    except Exception as e:
        logger.error(f"Manual pick error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_platform": state.active_platform,
        "api_key_present": bool(os.getenv("ANTHROPIC_API_KEY")),
        "timestamp": datetime.now().isoformat()
    }

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("Fantasy Agent Unified Server")
    print("="*50)
    print(f"Starting server on http://localhost:3001")
    print(f"ANTHROPIC_API_KEY present: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=3001, reload=False)