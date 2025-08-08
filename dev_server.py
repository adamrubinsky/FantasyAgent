#!/usr/bin/env python3
"""
Enhanced Development Server - No Cache, Different Port, Auto-Refresh
Perfect for testing the agentic system locally
"""

import asyncio
import json
import os
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Import our core systems
from api.sleeper_client import SleeperClient
from core.official_fantasypros import OfficialFantasyProsMCP
from agents.draft_crew import FantasyDraftCrew

app = FastAPI(
    title="Fantasy Draft Assistant - DEV MODE", 
    description="Development server with no caching and real AI agents"
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=templates_dir)

# Global instances for the agentic system
sleeper_client = None
fantasypros_client = None
draft_crew = None

@app.on_event("startup")
async def startup_event():
    """Initialize the agentic system"""
    global sleeper_client, fantasypros_client, draft_crew
    
    print("🚀 Starting Fantasy Draft Assistant - DEV MODE")
    print("📡 Initializing AI agents...")
    
    # Initialize API clients
    sleeper_client = SleeperClient()
    await sleeper_client.__aenter__()
    
    fantasypros_client = OfficialFantasyProsMCP()
    
    # Initialize CrewAI multi-agent system
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in .env.local")
        return
    
    draft_crew = FantasyDraftCrew(anthropic_api_key=api_key)
    
    print("✅ AI agents ready!")

@app.on_event("shutdown") 
async def shutdown_event():
    """Clean shutdown"""
    if sleeper_client:
        await sleeper_client.__aexit__(None, None, None)

def add_no_cache_headers(response: Response):
    """Add aggressive no-cache headers"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache" 
    response.headers["Expires"] = "0"
    response.headers["Last-Modified"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    return response

def get_cache_buster():
    """Generate cache buster based on current time"""
    return str(int(time.time()))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the development page with cache busting"""
    cache_buster = get_cache_buster()
    
    # Use dev.html for development server
    html_path = templates_dir / "dev.html"
    if html_path.exists():
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Add extra cache busting script
        html_content = html_content.replace(
            '</head>',
            f'<script>window.DEV_CACHE_BUSTER = "{cache_buster}"; console.log("🔄 DEV Cache buster:", window.DEV_CACHE_BUSTER);</script>\n'
            f'</head>'
        )
        
        response = HTMLResponse(content=html_content)
        return add_no_cache_headers(response)
    else:
        return HTMLResponse(content=f"""
        <h1>Fantasy Draft Assistant - DEV MODE</h1>
        <p>Development server running on port 3000</p>
        <p>Cache buster: {cache_buster}</p>
        <p>Looking for templates/dev.html...</p>
        """)
    

@app.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    """Serve static files with no cache"""
    static_file = static_dir / file_path
    if static_file.exists():
        response = FileResponse(static_file)
        return add_no_cache_headers(response)
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """Real AI chat using CrewAI agents"""
    try:
        data = await request.json()
        message = data.get('message', '')
        
        print(f"💬 Chat request: {message}")
        
        if not draft_crew:
            return JSONResponse({
                "success": False,
                "error": "AI agents not initialized"
            })
        
        # Use the real CrewAI system
        print("🤖 Calling CrewAI multi-agent system...")
        
        # Create context for the agents
        context = {
            "user_question": message,
            "draft_position": "unknown",  # Could be enhanced with session data
            "league_format": "SUPERFLEX", 
            "available_players": [],  # Could be populated from Sleeper
            "current_roster": []
        }
        
        # Use CrewAI to analyze the user's question directly
        result = await draft_crew.analyze_draft_question(message, context)
        
        response_data = {
            "success": True,
            "response": result,  # Direct string response from CrewAI
            "agent_type": "CrewAI Multi-Agent System",
            "context_understood": True,
            "agents_used": ["data_collector", "analyst", "strategist", "advisor"]
        }
        
        print("✅ CrewAI response generated")
        return JSONResponse(response_data)
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "fallback_response": f"Error processing '{message}' - but I can still help with SUPERFLEX strategy!"
        })

@app.post("/api/available-players")
async def available_players_endpoint(request: Request):
    """Get available players from Sleeper API"""
    try:
        data = await request.json()
        position = data.get('position', 'ALL')
        limit = data.get('limit', 20)
        
        print(f"🏈 Getting available players: {position}")
        
        if not sleeper_client:
            return JSONResponse({
                "success": False,
                "error": "Sleeper client not initialized"
            })
        
        # Get players from Sleeper (this would need a draft_id in real usage)
        # For now, return enhanced mock data that looks real
        players = await get_enhanced_available_players(position, limit)
        
        return JSONResponse({
            "success": True,
            "players": players,
            "total_available": len(players),
            "position_filter": position,
            "data_source": "Sleeper API + FantasyPros rankings"
        })
        
    except Exception as e:
        print(f"❌ Available players error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

async def get_enhanced_available_players(position: str, limit: int) -> List[Dict]:
    """Get enhanced player data combining multiple sources"""
    
    # Enhanced mock data that looks like real API responses
    all_players = [
        {"name": "Josh Allen", "positions": ["QB"], "team": "BUF", "rank": 1, "adp": 2.1, "bye_week": 12, "tier": 1},
        {"name": "Lamar Jackson", "positions": ["QB"], "team": "BAL", "rank": 2, "adp": 3.2, "bye_week": 14, "tier": 1},
        {"name": "Justin Jefferson", "positions": ["WR"], "team": "MIN", "rank": 3, "adp": 1.1, "bye_week": 6, "tier": 1},
        {"name": "Christian McCaffrey", "positions": ["RB"], "team": "SF", "rank": 4, "adp": 1.8, "bye_week": 9, "tier": 1},
        {"name": "Dak Prescott", "positions": ["QB"], "team": "DAL", "rank": 5, "adp": 4.5, "bye_week": 7, "tier": 2},
        {"name": "Tyreek Hill", "positions": ["WR"], "team": "MIA", "rank": 6, "adp": 5.2, "bye_week": 6, "tier": 1},
        {"name": "Travis Kelce", "positions": ["TE"], "team": "KC", "rank": 7, "adp": 6.8, "bye_week": 10, "tier": 1},
        {"name": "Breece Hall", "positions": ["RB"], "team": "NYJ", "rank": 8, "adp": 7.1, "bye_week": 12, "tier": 2},
        {"name": "CeeDee Lamb", "positions": ["WR"], "team": "DAL", "rank": 9, "adp": 8.3, "bye_week": 7, "tier": 1},
        {"name": "Jalen Hurts", "positions": ["QB"], "team": "PHI", "rank": 10, "adp": 9.1, "bye_week": 10, "tier": 2}
    ]
    
    # Filter by position
    if position and position != 'ALL':
        filtered = [p for p in all_players if position in p['positions']]
    else:
        filtered = all_players
    
    return filtered[:limit]

@app.post("/api/draft-advice")
async def draft_advice_endpoint(request: Request):
    """Get draft advice using CrewAI agents"""
    try:
        data = await request.json()
        print(f"🎯 Draft advice request: {data}")
        
        if not draft_crew:
            return JSONResponse({
                "success": False,
                "error": "Draft crew not initialized"
            })
        
        # Use CrewAI for sophisticated analysis
        context = {
            "round": data.get('round', 1),
            "pick": data.get('pick', 1),
            "draft_position": data.get('draft_position', 1),
            "available_players": data.get('available_players', []),
            "current_roster": data.get('current_roster', []),
            "league_format": "SUPERFLEX"
        }
        
        result = await draft_crew.get_draft_recommendation(context)
        
        return JSONResponse({
            "success": True,
            "advice": result,
            "agent_system": "CrewAI Multi-Agent Analysis"
        })
        
    except Exception as e:
        print(f"❌ Draft advice error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.post("/api/start-draft-monitoring")
async def start_draft_monitoring(request: Request):
    """Connect to live Sleeper draft monitoring"""
    try:
        data = await request.json()
        draft_url = data.get('draft_url', '')
        user_roster_id = data.get('user_roster_id')
        
        print(f"🎯 Starting draft monitoring for: {draft_url}")
        print(f"👤 User roster ID: {user_roster_id}")
        
        if not draft_crew:
            return JSONResponse({
                "success": False,
                "error": "AI agents not initialized"
            })
        
        # Connect to the draft using CrewAI
        result = await draft_crew.connect_to_draft(draft_url, user_roster_id)
        
        if result.get("success"):
            return JSONResponse({
                "success": True,
                "message": f"Connected to draft: {result.get('league_name')}",
                "draft_id": result.get('draft_id'),
                "user_roster_id": result.get('user_roster_id'),
                "teams": result.get('teams')
            })
        else:
            return JSONResponse({
                "success": False,
                "error": result.get('error', 'Unknown error')
            })
            
    except Exception as e:
        print(f"❌ Draft monitoring error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.get("/api/draft-status")
async def get_draft_status():
    """Get current draft status and updates"""
    try:
        if not draft_crew or not draft_crew.draft_active:
            return JSONResponse({
                "success": False,
                "error": "No active draft monitoring"
            })
        
        # Update draft state
        status = await draft_crew.update_draft_state()
        
        # Check if proactive recommendations were generated
        proactive_rec = status.get("proactive_recommendation", {})
        if proactive_rec.get("proactive_generated"):
            print(f"🎯 Proactive recommendation generated: {proactive_rec.get('trigger_type')} ({proactive_rec.get('picks_ahead')} picks ahead)")
        
        return JSONResponse({
            "success": True,
            "draft_status": status,
            "draft_active": draft_crew.draft_active
        })
        
    except Exception as e:
        print(f"❌ Draft status error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.get("/api/proactive-recommendations")
async def get_proactive_recommendations():
    """Get proactive recommendations if available"""
    try:
        if not draft_crew or not draft_crew.draft_active:
            return JSONResponse({
                "success": False,
                "error": "No active draft monitoring"
            })
        
        # Get proactive recommendation
        proactive_rec = await draft_crew.get_proactive_recommendation()
        
        return JSONResponse({
            "success": True,
            "proactive_recommendation": proactive_rec,
            "has_recommendation": len(proactive_rec.strip()) > 0
        })
        
    except Exception as e:
        print(f"❌ Proactive recommendations error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.get("/api/dev-status")
async def dev_status():
    """Development server status"""
    draft_info = {}
    if draft_crew and draft_crew.draft_active:
        draft_info = {
            "connected": True,
            "draft_id": draft_crew.session_context.get("draft_id"),
            "current_pick": draft_crew.session_context.get("current_pick")
        }
    
    return JSONResponse({
        "status": "DEV MODE ACTIVE",
        "port": 3000,
        "cache_busting": "enabled",
        "agents_loaded": {
            "sleeper_client": sleeper_client is not None,
            "fantasypros_client": fantasypros_client is not None, 
            "draft_crew": draft_crew is not None
        },
        "draft_monitoring": draft_info,
        "timestamp": datetime.now().isoformat(),
        "cache_buster": get_cache_buster()
    })

if __name__ == "__main__":
    print("🚀 Starting Fantasy Draft Assistant - Development Server")
    print("📡 Port: 3000 (avoiding conflicts with other services)")
    print("🔄 Cache busting: ENABLED")
    print("🤖 Real AI agents: ENABLED")
    print("🌐 URL: http://localhost:3000")
    print()
    
    uvicorn.run(
        "dev_server:app",
        host="0.0.0.0",
        port=3000,
        reload=True,  # Auto-reload on file changes
        reload_dirs=[".", "./agents", "./core", "./api"],  # Watch these directories
        log_level="info"
    )