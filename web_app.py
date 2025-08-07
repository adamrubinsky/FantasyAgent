#!/usr/bin/env python3
"""
Fantasy Football Draft Assistant - Web UI
Real-time browser-based interface with chat and automatic alerts
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Import our core systems
from api.sleeper_client import SleeperClient
from core.draft_monitor import DraftMonitor
from core.mcp_integration import MCPClient
from agents.draft_crew import FantasyDraftCrew
from core.league_context import league_manager

app = FastAPI(title="Fantasy Draft Assistant", description="AI-powered draft recommendations")

# Create static files and templates directories
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.draft_monitor: Optional[DraftMonitor] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ Client connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"❌ Client disconnected. Total connections: {len(self.active_connections)}")
        
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except:
            self.disconnect(websocket)
            
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def start_draft_monitoring(self, draft_id: str = None):
        """Start monitoring draft and send real-time updates"""
        if self.monitoring_task and not self.monitoring_task.done():
            return  # Already monitoring
            
        username = os.getenv('SLEEPER_USERNAME')
        league_id = os.getenv('SLEEPER_LEAGUE_ID') 
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not username:
            await self.broadcast({
                "type": "error",
                "message": "SLEEPER_USERNAME not configured"
            })
            return
            
        self.monitoring_task = asyncio.create_task(
            self._monitor_draft_loop(username, league_id, api_key, draft_id)
        )
        
    async def _monitor_draft_loop(self, username: str, league_id: str, api_key: str, draft_id: str = None):
        """Main draft monitoring loop"""
        try:
            async with DraftMonitor(username, league_id, api_key, draft_id) as monitor:
                self.draft_monitor = monitor
                print(f"🔄 Initializing draft monitor for {username} in league {league_id}")
                
                if not await monitor.initialize_draft():
                    await self.broadcast({
                        "type": "error", 
                        "message": "Failed to initialize draft monitoring"
                    })
                    return
                
                print(f"✅ Draft monitor initialized - Draft ID: {monitor.draft_id}, User Roster: {monitor.user_roster_id}")
                
                # Get initial picks to show existing picks and user roster
                picks = await monitor.client.get_draft_picks(monitor.draft_id)
                print(f"📋 Found {len(picks)} existing picks in draft")
                
                await self.broadcast({
                    "type": "draft_started",
                    "message": f"🏈 Monitoring draft {monitor.draft_id}",
                    "draft_id": monitor.draft_id,
                    "user_roster_id": monitor.user_roster_id
                })
                
                # Send initial roster state
                print(f"📊 Sending initial roster update...")
                await self.send_user_roster_update(monitor, picks)
                
                # Send all existing picks
                print(f"📋 Found {len(picks)} total picks in draft")
                if picks:
                    try:
                        players = await monitor.client.get_all_players()
                        print(f"👥 Loaded {len(players)} players from database")
                        
                        # Send last 10 picks to show recent activity
                        recent_picks = picks[-10:] if len(picks) >= 10 else picks
                        print(f"📋 Sending {len(recent_picks)} recent picks...")
                        
                        for pick in recent_picks:
                            player_name = "Unknown Player"
                            player_team = ""
                            player_position = ""
                            
                            if pick.get('player_id') and pick['player_id'] in players:
                                player = players[pick['player_id']]
                                player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
                                player_team = player.get('team', '')
                                player_position = "/".join(player.get('fantasy_positions', []))
                            else:
                                print(f"⚠️ Player not found for pick {pick.get('pick_no', '?')}: {pick.get('player_id', 'no ID')}")
                        
                            await self.broadcast({
                                "type": "new_pick",
                                "pick_number": pick.get('pick_no', 0),
                                "player_name": player_name,
                                "team": player_team,
                                "position": player_position,
                                "picked_by": f"Team {pick.get('roster_id', 'Unknown')}",
                                "is_user_pick": pick.get('roster_id') == monitor.user_roster_id
                            })
                            
                    except Exception as e:
                        print(f"❌ Error loading existing picks: {e}")
                        await self.broadcast({
                            "type": "error",
                            "message": f"Could not load existing picks: {str(e)}"
                        })
                else:
                    print("📋 No existing picks found - this appears to be a new draft")
                
                last_pick_count = len(picks)  # Set to current count, not 0
                last_alert_pick = None
                
                print(f"🔄 Starting monitoring loop with {last_pick_count} existing picks")
                
                while True:
                    try:
                        # Get current draft state
                        picks = await monitor.client.get_draft_picks(monitor.draft_id)
                        current_pick_count = len(picks)
                        current_pick_number = current_pick_count + 1
                        
                        # Check for new picks
                        if current_pick_count > last_pick_count:
                            # New pick made!
                            print(f"🔄 New picks detected: {current_pick_count} vs {last_pick_count}")
                            new_picks = picks[last_pick_count:]
                            for pick in new_picks:
                                player_name = "Unknown Player"
                                player_team = ""
                                player_position = ""
                                
                                if pick.get('player_id'):
                                    players = await monitor.client.get_all_players()
                                    if pick['player_id'] in players:
                                        player = players[pick['player_id']]
                                        player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
                                        player_team = player.get('team', '')
                                        player_position = "/".join(player.get('fantasy_positions', []))
                                
                                pick_data = {
                                    "type": "new_pick",
                                    "pick_number": pick.get('pick_no', len(picks)),
                                    "player_name": player_name,
                                    "team": player_team,
                                    "position": player_position,
                                    "picked_by": f"Team {pick.get('roster_id', 'Unknown')}",
                                    "is_user_pick": pick.get('roster_id') == monitor.user_roster_id
                                }
                                
                                print(f"📋 Broadcasting new pick: {player_name} to {pick_data['picked_by']}")
                                await self.broadcast(pick_data)
                            
                            last_pick_count = current_pick_count
                            
                            # Send updated user roster
                            await self.send_user_roster_update(monitor, picks)
                        
                        # Check if user's turn is approaching (3 picks away)
                        picks_until_user_turn = monitor._get_picks_until_user_turn(current_pick_number)
                        
                        if (picks_until_user_turn is not None and 
                            picks_until_user_turn <= 3 and 
                            picks_until_user_turn >= 0 and
                            current_pick_number != last_alert_pick):
                            
                            # Time for automatic recommendation!
                            await self.send_automatic_recommendation(
                                monitor, current_pick_number, picks_until_user_turn, api_key
                            )
                            last_alert_pick = current_pick_number
                        
                        # Send draft status update
                        await self.broadcast({
                            "type": "draft_status",
                            "current_pick": current_pick_number,
                            "total_picks": monitor.total_picks,
                            "picks_until_user": picks_until_user_turn,
                            "user_turn": picks_until_user_turn == 0
                        })
                        
                        # Wait before next poll
                        await asyncio.sleep(5)
                        
                    except Exception as e:
                        print(f"Error in monitoring loop: {e}")
                        await asyncio.sleep(10)  # Wait longer on error
                        
        except Exception as e:
            await self.broadcast({
                "type": "error",
                "message": f"Draft monitoring failed: {str(e)}"
            })
    
    async def send_user_roster_update(self, monitor: DraftMonitor, picks: List[Dict]):
        """Send updated user roster information"""
        try:
            # Filter picks for user's team
            user_picks = [pick for pick in picks if pick.get('roster_id') == monitor.user_roster_id]
            print(f"👤 Found {len(user_picks)} picks for user's team (roster_id: {monitor.user_roster_id})")
            
            players = await monitor.client.get_all_players()
            roster_players = []
            
            for pick in user_picks:
                if pick.get('player_id') and pick['player_id'] in players:
                    player = players[pick['player_id']]
                    player_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
                    
                    roster_players.append({
                        "pick_number": pick.get('pick_no', 0),
                        "player_name": player_name,
                        "team": player.get('team', ''),
                        "positions": player.get('fantasy_positions', []),
                        "primary_position": player.get('fantasy_positions', ['FLEX'])[0]
                    })
            
            # Define typical roster slots for Superflex league
            roster_slots = [
                {"position": "QB", "filled": False, "player": None},
                {"position": "RB", "filled": False, "player": None},
                {"position": "RB", "filled": False, "player": None},
                {"position": "WR", "filled": False, "player": None},
                {"position": "WR", "filled": False, "player": None},
                {"position": "TE", "filled": False, "player": None},
                {"position": "FLEX", "filled": False, "player": None},
                {"position": "SUPERFLEX", "filled": False, "player": None},
                {"position": "DST", "filled": False, "player": None},
                {"position": "K", "filled": False, "player": None},
                {"position": "BENCH", "filled": False, "player": None},
                {"position": "BENCH", "filled": False, "player": None},
                {"position": "BENCH", "filled": False, "player": None},
                {"position": "BENCH", "filled": False, "player": None},
                {"position": "BENCH", "filled": False, "player": None},
                {"position": "BENCH", "filled": False, "player": None}
            ]
            
            # Fill roster slots with drafted players
            for player in roster_players:
                primary_pos = player['primary_position']
                
                # Find first available slot for this position
                for slot in roster_slots:
                    if not slot['filled']:
                        if (slot['position'] == primary_pos or 
                            slot['position'] == 'FLEX' and primary_pos in ['RB', 'WR', 'TE'] or
                            slot['position'] == 'SUPERFLEX' and primary_pos == 'QB' or
                            slot['position'] == 'BENCH'):
                            slot['filled'] = True
                            slot['player'] = player
                            break
            
            roster_update_data = {
                "type": "user_roster_update",
                "roster_slots": roster_slots,
                "total_picks": len(user_picks),
                "remaining_slots": len([s for s in roster_slots if not s['filled']])
            }
            print(f"📤 Broadcasting roster update with {len(roster_slots)} slots")
            await self.broadcast(roster_update_data)
            
        except Exception as e:
            print(f"Error updating user roster: {e}")
    
    async def send_automatic_recommendation(self, monitor: DraftMonitor, current_pick: int, picks_away: int, api_key: str):
        """Send automatic AI recommendation when user's turn approaches"""
        try:
            if picks_away == 0:
                urgency = "🚨 YOUR TURN NOW!"
                message_type = "urgent_recommendation"
            elif picks_away == 1:
                urgency = "⏰ You're up next!"
                message_type = "upcoming_recommendation" 
            elif picks_away <= 3:
                urgency = f"📍 {picks_away} picks until your turn"
                message_type = "early_recommendation"
            
            # Get AI recommendation
            if api_key:
                crew = FantasyDraftCrew(anthropic_api_key=api_key)
                
                # Get available players (basic data only for performance)
                all_available = await monitor.client.get_available_players(
                    monitor.draft_id, enhanced=False
                )
                available_players = all_available[:20]  # Top 20 available
                
                player_names = [p['name'] for p in available_players[:10]]
                
                # Get AI recommendation with context
                context = {
                    "available_players": player_names,
                    "picks_until_user_turn": picks_away,
                    "user_turn": picks_away == 0
                }
                recommendation = await crew.get_draft_recommendation(
                    current_pick=current_pick,
                    context=context
                )
                
                await self.broadcast({
                    "type": message_type,
                    "urgency": urgency,
                    "message": f"{urgency}\n\n🤖 AI Recommendation:\n{recommendation}",
                    "picks_away": picks_away,
                    "current_pick": current_pick,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # Fallback without AI
                top_players = available_players[:3]
                player_list = "\n".join([f"• {p['name']} ({p['positions'][0]}) - Rank {p['rank']}" 
                                       for p in top_players])
                
                await self.broadcast({
                    "type": message_type,
                    "urgency": urgency, 
                    "message": f"{urgency}\n\n📊 Top Available Players:\n{player_list}",
                    "picks_away": picks_away,
                    "current_pick": current_pick,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            print(f"Error generating automatic recommendation: {e}")

# Global connection manager
manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request):
    """Main draft assistant interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket)
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "start_monitoring":
                draft_id = message.get("draft_id")
                await manager.start_draft_monitoring(draft_id)
                
            elif message["type"] == "chat_message":
                # Handle chat message - get AI response
                await handle_chat_message(message, websocket)
                
            elif message["type"] == "get_available_players":
                await send_available_players(message, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def handle_chat_message(message: dict, websocket: WebSocket):
    """Handle chat messages and get AI responses"""
    user_message = message.get("message", "")
    print(f"🗣️ Received chat message: {user_message}")
    
    try:
        # Echo user message
        await manager.send_personal_message({
            "type": "chat_message",
            "sender": "user",
            "message": user_message,
            "timestamp": datetime.now().isoformat()
        }, websocket)
        
        # Get AI response
        api_key = os.getenv('ANTHROPIC_API_KEY')
        print(f"🔑 API key available: {bool(api_key)}")
        
        if api_key:
            try:
                print("🤖 Creating CrewAI instance...")
                
                # Try simple response first to test
                # Send thinking indicator for non-simple messages
                if user_message.lower() not in ['hello', 'hi', 'test']:
                    await manager.send_personal_message({
                        "type": "chat_message",
                        "sender": "ai", 
                        "message": "🤔 Analyzing your question...",
                        "timestamp": datetime.now().isoformat(),
                        "thinking": True
                    }, websocket)
                
                if user_message.lower() in ['hello', 'hi', 'test']:
                    response = "🤖 Hello! I'm your Fantasy Draft Assistant. I can help you with draft questions, player comparisons, and recommendations. Try asking 'Who should I draft?' or 'Compare Josh Allen vs Lamar Jackson'."
                    print("✅ Using simple greeting response")
                else:
                    # Use FAST single agent instead of slow CrewAI
                    from core.ai_assistant import FantasyAIAssistant
                    
                    # Get quick context
                    context_info = ""
                    if manager.draft_monitor:
                        try:
                            picks = await manager.draft_monitor.client.get_draft_picks(manager.draft_monitor.draft_id)
                            current_pick = len(picks) + 1
                            
                            # Get top 5 available players (basic data only for speed)
                            available = await manager.draft_monitor.client.get_available_players(
                                manager.draft_monitor.draft_id, enhanced=False
                            )
                            top_available = [p['name'] for p in available[:5]]
                            
                            context_info = f"""
Current Draft: Pick #{current_pick}, SUPERFLEX Half-PPR
Top Available: {', '.join(top_available)}

Question: {user_message}

Provide a concise, actionable answer (2-3 sentences max)."""
                        except:
                            context_info = f"SUPERFLEX Half-PPR League Question: {user_message}"
                    
                    # Use fast single AI assistant
                    ai_assistant = FantasyAIAssistant(anthropic_api_key=api_key)
                    response = await ai_assistant.get_recommendation(context_info)
                    print(f"✅ Got fast AI response: {response[:100]}...")
                
                await manager.send_personal_message({
                    "type": "chat_message", 
                    "sender": "ai",
                    "message": response,
                    "timestamp": datetime.now().isoformat()
                }, websocket)
                
            except Exception as ai_error:
                print(f"❌ AI processing error: {ai_error}")
                import traceback
                traceback.print_exc()
                
                # Provide a helpful fallback response
                fallback_responses = {
                    'who should i draft': "I'd recommend looking at the available players list and considering your roster needs. QBs are very valuable in Superflex leagues!",
                    'compare': "To compare players, I need more specific information. Try asking about specific players like 'Compare Josh Allen vs Lamar Jackson'.",
                    'available': "Check the Available Players section on the left - I can help you analyze any of those players!",
                    'help': "I can help with draft recommendations, player comparisons, and strategy advice. Try asking specific questions about players or draft strategy!"
                }
                
                # Simple keyword matching for fallback
                response = "🤖 I'm having technical difficulties with my AI processing. "
                for key, fallback in fallback_responses.items():
                    if key in user_message.lower():
                        response += fallback
                        break
                else:
                    response += "Please try asking a simpler question, or check the available players list to get recommendations."
                
                await manager.send_personal_message({
                    "type": "chat_message",
                    "sender": "ai", 
                    "message": response,
                    "timestamp": datetime.now().isoformat()
                }, websocket)
        else:
            print("⚠️ No API key configured")
            await manager.send_personal_message({
                "type": "chat_message",
                "sender": "ai", 
                "message": "🤖 AI assistant unavailable (no ANTHROPIC_API_KEY configured in .env.local)",
                "timestamp": datetime.now().isoformat()
            }, websocket)
            
    except Exception as e:
        print(f"❌ Chat message error: {e}")
        await manager.send_personal_message({
            "type": "chat_message",
            "sender": "ai",
            "message": f"❌ Error processing your message: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, websocket)

async def send_available_players(message: dict, websocket: WebSocket):
    """Send available players list"""
    try:
        if not manager.draft_monitor:
            await manager.send_personal_message({
                "type": "error",
                "message": "Draft monitoring not active"
            }, websocket)
            return
            
        position = message.get("position")
        limit = message.get("limit", 20)
        
        # Use enhanced data only when specifically requested via chat
        # For real-time updates, use basic data for performance  
        enhanced = message.get("enhanced", False)
        available_players = await manager.draft_monitor.client.get_available_players(
            manager.draft_monitor.draft_id, 
            position=position,
            enhanced=enhanced
        )
        
        await manager.send_personal_message({
            "type": "available_players",
            "players": available_players[:limit],
            "position": position,
            "total": len(available_players)
        }, websocket)
        
    except Exception as e:
        await manager.send_personal_message({
            "type": "error",
            "message": f"Error getting available players: {str(e)}"
        }, websocket)

if __name__ == "__main__":
    print("🚀 Starting Fantasy Draft Assistant Web UI")
    print("📱 Open your browser to: http://localhost:8000")
    print("💬 Chat interface with automatic draft alerts enabled!")
    
    uvicorn.run(
        "web_app:app",
        host="0.0.0.0", 
        port=8000,
        reload=True,
        log_level="info"
    )