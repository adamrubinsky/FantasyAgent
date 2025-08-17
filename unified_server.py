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

# Global state
class ServerState:
    def __init__(self):
        self.active_platform: Optional[str] = None
        self.sleeper_crew = None
        self.yahoo_snake_agent = None
        self.yahoo_auction_agent = None
        
    def get_sleeper_crew(self):
        """Get or create Sleeper CrewAI agent"""
        if self.sleeper_crew is None:
            try:
                from agents.draft_crew import FantasyDraftCrew
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
                from yahoo_agents.agents.yahoo_snake_agent import YahooSnakeAgent
                self.yahoo_snake_agent = YahooSnakeAgent()
                logger.info("Yahoo Snake agent initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Yahoo Snake agent: {e}")
                # Return a mock agent for now
                class MockAgent:
                    async def get_recommendation(self, query, context):
                        return f"Yahoo Snake agent not available. Your query: {query}"
                self.yahoo_snake_agent = MockAgent()
        return self.yahoo_snake_agent
    
    def get_yahoo_auction_agent(self):
        """Get or create Yahoo Auction agent"""
        if self.yahoo_auction_agent is None:
            try:
                from yahoo_agents.agents.yahoo_auction_agent import YahooAuctionAgent
                self.yahoo_auction_agent = YahooAuctionAgent()
                logger.info("Yahoo Auction agent initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Yahoo Auction agent: {e}")
                # Return a mock agent for now
                class MockAgent:
                    async def get_recommendation(self, query, context):
                        return f"Yahoo Auction agent not available. Your query: {query}"
                self.yahoo_auction_agent = MockAgent()
        return self.yahoo_auction_agent

# Initialize server state
state = ServerState()

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
        elif selection.platform == "yahoo-auction":
            state.get_yahoo_auction_agent()
        
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
        
        if query.platform == "sleeper":
            crew = state.get_sleeper_crew()
            # Use the analyze_draft_question method which is async
            result = await crew.analyze_draft_question(query.query, query.context or {})
            
        elif query.platform == "yahoo-snake":
            agent = state.get_yahoo_snake_agent()
            result = await agent.get_recommendation(
                query=query.query,
                context=query.context or {}
            )
            
        elif query.platform == "yahoo-auction":
            agent = state.get_yahoo_auction_agent()
            result = await agent.get_recommendation(
                query=query.query,
                context=query.context or {}
            )
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
        from core.official_fantasypros import OfficialFantasyProsClient
        
        # Platform-specific settings
        settings = {
            "sleeper": {"position": "OP", "scoring": "HALF"},  # SUPERFLEX
            "yahoo-snake": {"position": "ALL", "scoring": "PPR"},  # Full PPR
            "yahoo-auction": {"position": "ALL", "scoring": "HALF"}  # Half PPR
        }
        
        platform_settings = settings.get(platform, {"position": "ALL", "scoring": "HALF"})
        
        client = OfficialFantasyProsClient()
        rankings = client.get_rankings_sync(
            position=platform_settings["position"],
            scoring=platform_settings["scoring"]
        )
        
        return JSONResponse(rankings if rankings else [])
        
    except Exception as e:
        logger.error(f"Rankings error: {e}")
        # Return mock data so UI doesn't break
        return JSONResponse([
            {"player_id": 1, "player_name": "Christian McCaffrey", "player_position_id": "RB", "player_team_id": "SF", "rank_ecr": 1},
            {"player_id": 2, "player_name": "CeeDee Lamb", "player_position_id": "WR", "player_team_id": "DAL", "rank_ecr": 2},
            {"player_id": 3, "player_name": "Tyreek Hill", "player_position_id": "WR", "player_team_id": "MIA", "rank_ecr": 3},
        ])

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