"""
Unified Fantasy Agent Server
Handles routing between Sleeper, Yahoo Snake, and Yahoo Auction platforms
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

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Fantasy Agent Multi-Platform Server")

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
    platform: str  # "sleeper", "yahoo-snake", "yahoo-auction"
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
        self.active_league_id: Optional[str] = None
        self.active_draft_id: Optional[str] = None
        self.platform_agents: Dict[str, Any] = {}
        self.websocket_connections: Dict[str, WebSocket] = {}
        
    async def initialize_platform(self, platform: str):
        """Initialize the selected platform's agent system"""
        if platform in self.platform_agents:
            return self.platform_agents[platform]
            
        try:
            if platform == "sleeper":
                # Load config FIRST
                from dotenv import load_dotenv
                load_dotenv('.env.local')
                
                # Set API key in environment
                import os
                if not os.getenv("ANTHROPIC_API_KEY"):
                    # Try to load from .env if not set
                    load_dotenv()
                
                # Import Sleeper agent system from platforms location
                from platforms.sleeper.agents.draft_crew import FantasyDraftCrew
                from api.sleeper_client import SleeperClient
                
                # Get API key
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not found in environment")
                
                client = SleeperClient()
                agent = FantasyDraftCrew(anthropic_api_key=api_key)
                
                # Pre-initialize agents for faster first query
                if hasattr(agent, 'agents') and agent.agents is None:
                    agent.agents = agent._create_agents()
                    logger.info("Sleeper agents pre-initialized")
                
                self.platform_agents[platform] = {
                    "client": client,
                    "agent": agent,
                    "type": "crewai"
                }
                
            elif platform == "yahoo-snake":
                # Import Yahoo Snake agent from original location
                from yahoo_agents.agents.yahoo_snake_agent import YahooSnakeAgent
                
                # For now, create agent without client (no live monitoring yet)
                agent = YahooSnakeAgent()
                
                self.platform_agents[platform] = {
                    "client": None,  # No live monitoring yet
                    "agent": agent,
                    "type": "langgraph"
                }
                
            elif platform == "yahoo-auction":
                # Import Yahoo Auction agent from original location
                from yahoo_agents.agents.yahoo_auction_agent import YahooAuctionAgent
                
                # For now, create agent without client (no live monitoring yet)
                agent = YahooAuctionAgent()
                
                self.platform_agents[platform] = {
                    "client": None,  # No live monitoring yet
                    "agent": agent,
                    "type": "langgraph"
                }
                
            else:
                raise ValueError(f"Unknown platform: {platform}")
                
            logger.info(f"Successfully initialized {platform} platform")
            return self.platform_agents[platform]
            
        except Exception as e:
            logger.error(f"Failed to initialize {platform}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize {platform}: {str(e)}")

# Initialize server state
state = ServerState()

@app.on_event("startup")
async def startup_event():
    """Initialize server on startup"""
    logger.info("Fantasy Agent Multi-Platform Server starting up...")
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    
    logger.info("Server ready to accept platform connections")

@app.get("/")
async def root():
    """Serve the main application page"""
    with open("templates/unified.html", "r") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.post("/api/select-platform")
async def select_platform(selection: PlatformSelection):
    """Select and initialize the active platform"""
    try:
        # Set active platform
        state.active_platform = selection.platform
        state.active_league_id = selection.league_id
        state.active_draft_id = selection.draft_id
        
        # Initialize platform
        platform_data = await state.initialize_platform(selection.platform)
        
        # Get league-specific settings
        league_settings = {
            "sleeper": {
                "name": "Sleeper SUPERFLEX",
                "type": "snake",
                "scoring": "half-ppr",
                "teams": 12,
                "superflex": True,
                "draft_date": "Past (Aug 14)"
            },
            "yahoo-snake": {
                "name": "Yahoo Snake Draft", 
                "type": "snake",
                "scoring": "full-ppr",
                "teams": 10,
                "superflex": False,
                "draft_date": "Aug 19, 2025"
            },
            "yahoo-auction": {
                "name": "Yahoo Auction Draft",
                "type": "auction",
                "scoring": "half-ppr",
                "teams": 12,
                "superflex": False,
                "draft_date": "Aug 24, 2025",
                "budget": 200
            }
        }
        
        return JSONResponse({
            "status": "success",
            "platform": selection.platform,
            "settings": league_settings.get(selection.platform, {}),
            "message": f"Successfully connected to {selection.platform}"
        })
        
    except Exception as e:
        logger.error(f"Failed to select platform: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.post("/api/draft-query")
async def draft_query(query: DraftQuery):
    """Process a draft query for the active platform"""
    if not state.active_platform:
        return JSONResponse(
            status_code=400,
            content={"error": "No platform selected"}
        )
    
    try:
        platform_data = state.platform_agents.get(query.platform)
        if not platform_data:
            platform_data = await state.initialize_platform(query.platform)
        
        agent = platform_data["agent"]
        
        # Route to appropriate agent based on type
        if platform_data["type"] == "crewai":
            # Sleeper CrewAI agent - use the analyze_draft_question method
            result = await agent.analyze_draft_question(
                query.query,
                query.context or {}
            )
        else:
            # Yahoo LangGraph agents
            result = await agent.get_recommendation(
                query=query.query,
                context=query.context or {}
            )
        
        return JSONResponse({
            "status": "success",
            "response": result,
            "platform": query.platform
        })
        
    except Exception as e:
        logger.error(f"Draft query error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Unified WebSocket endpoint for all platforms"""
    await websocket.accept()
    connection_id = f"{websocket.client.host}:{websocket.client.port}"
    state.websocket_connections[connection_id] = websocket
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                
            elif data.get("type") == "platform_select":
                # Switch platform
                platform = data.get("platform")
                await select_platform(PlatformSelection(
                    platform=platform,
                    league_id=data.get("league_id"),
                    draft_id=data.get("draft_id")
                ))
                await websocket.send_json({
                    "type": "platform_changed",
                    "platform": platform
                })
                
            elif data.get("type") == "draft_query":
                # Process draft query
                response = await draft_query(DraftQuery(
                    platform=state.active_platform,
                    query=data.get("query"),
                    context=data.get("context")
                ))
                await websocket.send_json({
                    "type": "draft_response",
                    "response": response
                })
                
            elif data.get("type") == "draft_update":
                # Handle draft updates (picks, etc)
                if state.active_platform:
                    # Broadcast to other connections
                    for conn_id, ws in state.websocket_connections.items():
                        if conn_id != connection_id:
                            await ws.send_json(data)
                            
    except WebSocketDisconnect:
        del state.websocket_connections[connection_id]
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        del state.websocket_connections[connection_id]

@app.get("/api/rankings/{platform}")
async def get_rankings(platform: str, position: str = "ALL", scoring: str = "HALF"):
    """Get rankings for specific platform settings"""
    try:
        # Use existing rankings manager  
        from core.official_fantasypros import OfficialFantasyProsClient
        
        # Platform-specific settings
        settings = {
            "sleeper": {"position": "OP", "scoring": "HALF"},  # SUPERFLEX
            "yahoo-snake": {"position": "ALL", "scoring": "PPR"},  # Full PPR
            "yahoo-auction": {"position": "ALL", "scoring": "HALF"}  # Half PPR
        }
        
        platform_settings = settings.get(platform, {"position": position, "scoring": scoring})
        
        client = OfficialFantasyProsClient()
        rankings = client.get_rankings_sync(
            position=platform_settings["position"],
            scoring=platform_settings["scoring"]
        )
        
        return JSONResponse(rankings if rankings else [])
        
    except Exception as e:
        logger.error(f"Rankings error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_platform": state.active_platform,
        "platforms_loaded": list(state.platform_agents.keys()),
        "timestamp": datetime.now().isoformat()
    }

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=3001,
        reload=True,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )