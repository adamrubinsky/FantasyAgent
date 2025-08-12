#!/usr/bin/env python3
"""
Simplified Development Server for Fantasy Draft Assistant
No complex middleware, just core functionality
"""

import json
import os
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Import our core systems
from agents.draft_crew import FantasyDraftCrew

app = FastAPI(title="Fantasy Draft Assistant - Simple Dev Server")

# Globals
templates_dir = Path(__file__).parent / "templates"
draft_crew = None

@app.on_event("startup")
async def startup_event():
    """Initialize the AI system"""
    global draft_crew
    
    print("🚀 Starting Fantasy Draft Assistant - Simple Dev Server")
    print("📡 Initializing CrewAI agents...")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        draft_crew = FantasyDraftCrew(anthropic_api_key=api_key)
        print("✅ CrewAI agents ready!")
    else:
        print("⚠️ No ANTHROPIC_API_KEY found - AI features disabled")

@app.get("/")
async def home():
    """Serve the development page"""
    html_path = templates_dir / "dev.html"
    if html_path.exists():
        with open(html_path, 'r') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    else:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fantasy Draft Assistant - Dev Server</title>
            <style>
                body { font-family: sans-serif; padding: 20px; background: #1a1a1a; color: white; }
                .container { max-width: 800px; margin: 0 auto; }
                input, button { padding: 10px; margin: 10px 0; }
                input { width: 70%; }
                button { background: #4CAF50; color: white; border: none; cursor: pointer; }
                #response { margin-top: 20px; padding: 15px; background: #333; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏈 Fantasy Draft Assistant - Simple Dev Server</h1>
                <p>Ask me anything about your SUPERFLEX draft!</p>
                
                <input type="text" id="question" placeholder="e.g., Should I draft Josh Allen in round 1?" />
                <button onclick="askQuestion()">Ask AI</button>
                
                <div id="response"></div>
            </div>
            
            <script>
                async function askQuestion() {
                    const question = document.getElementById('question').value;
                    const responseDiv = document.getElementById('response');
                    
                    if (!question) return;
                    
                    responseDiv.innerHTML = '🤔 Thinking...';
                    
                    try {
                        const response = await fetch('/api/chat', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({message: question})
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            responseDiv.innerHTML = '<strong>AI Response:</strong><br><pre>' + data.response + '</pre>';
                        } else {
                            responseDiv.innerHTML = '❌ Error: ' + data.error;
                        }
                    } catch (error) {
                        responseDiv.innerHTML = '❌ Connection error: ' + error.message;
                    }
                }
                
                // Enter key support
                document.getElementById('question').addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') askQuestion();
                });
            </script>
        </body>
        </html>
        """)

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """Real AI chat using CrewAI agents"""
    try:
        data = await request.json()
        message = data.get('message', '')
        
        print(f"💬 Question: {message}")
        
        if not draft_crew:
            return JSONResponse({
                "success": False,
                "error": "AI agents not initialized - check ANTHROPIC_API_KEY"
            })
        
        # Context for SUPERFLEX league
        context = {
            "league_format": "SUPERFLEX",
            "scoring": "Half-PPR",
            "teams": 12,
            "draft_position": "TBD"
        }
        
        # Get real AI response
        print("🤖 Calling CrewAI agents...")
        response = await draft_crew.analyze_draft_question(message, context)
        
        print("✅ Response generated")
        return JSONResponse({
            "success": True,
            "response": response,
            "agent_type": "CrewAI Multi-Agent System"
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.get("/api/status")
async def status():
    """Check server status"""
    return JSONResponse({
        "status": "running",
        "agents_loaded": draft_crew is not None,
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    print("🚀 Starting Simple Dev Server on http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=3000)