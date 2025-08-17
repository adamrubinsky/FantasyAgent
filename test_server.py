"""
Simple test server to verify the unified architecture works
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json

# Request models
class PlatformSelection(BaseModel):
    platform: str
    league_id: str = None
    draft_id: str = None

class DraftQuery(BaseModel):
    platform: str
    query: str
    context: dict = None

# Create FastAPI app
app = FastAPI(title="Fantasy Agent Test Server")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active platform
active_platform = None

@app.get("/")
async def root():
    """Serve the unified HTML page"""
    with open("templates/unified.html", "r") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.post("/api/select-platform")
async def select_platform(selection: PlatformSelection):
    """Handle platform selection"""
    global active_platform
    active_platform = selection.platform
    
    return JSONResponse({
        "status": "success",
        "platform": selection.platform,
        "message": f"Connected to {selection.platform} (test mode - no real agents connected)"
    })

@app.post("/api/draft-query")
async def draft_query(query: DraftQuery):
    """Handle draft queries (mock response)"""
    return JSONResponse({
        "status": "success",
        "response": f"Test response for '{query.query}' on {query.platform} platform",
        "platform": query.platform
    })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # Echo back a confirmation
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "platform_select":
                await websocket.send_json({
                    "type": "platform_changed",
                    "platform": data.get("platform")
                })
    except WebSocketDisconnect:
        pass

@app.get("/api/rankings/{platform}")
async def get_rankings(platform: str):
    """Return mock rankings"""
    mock_players = [
        {"player_id": 1, "player_name": "Christian McCaffrey", "player_position_id": "RB", "player_team_id": "SF", "rank_ecr": 1},
        {"player_id": 2, "player_name": "CeeDee Lamb", "player_position_id": "WR", "player_team_id": "DAL", "rank_ecr": 2},
        {"player_id": 3, "player_name": "Tyreek Hill", "player_position_id": "WR", "player_team_id": "MIA", "rank_ecr": 3},
        {"player_id": 4, "player_name": "Justin Jefferson", "player_position_id": "WR", "player_team_id": "MIN", "rank_ecr": 4},
        {"player_id": 5, "player_name": "Ja'Marr Chase", "player_position_id": "WR", "player_team_id": "CIN", "rank_ecr": 5},
    ]
    return JSONResponse(mock_players)

@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "Test server running on port 3001", "active_platform": active_platform}

if __name__ == "__main__":
    print("Starting test server on http://localhost:3001")
    uvicorn.run(app, host="0.0.0.0", port=3001)