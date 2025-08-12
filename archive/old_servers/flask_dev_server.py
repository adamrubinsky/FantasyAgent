#!/usr/bin/env python3
"""
Flask Development Server for Fantasy Draft Assistant
Using Flask to avoid FastAPI/Python 3.13 compatibility issues
"""

import json
import os
import asyncio
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

app = Flask(__name__)

# Global variables
draft_crew = None

def init_agents():
    """Initialize CrewAI agents"""
    global draft_crew
    
    print("🚀 Starting Fantasy Draft Assistant - Flask Dev Server")
    print("📡 Initializing CrewAI agents...")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        try:
            from agents.draft_crew import FantasyDraftCrew
            draft_crew = FantasyDraftCrew(anthropic_api_key=api_key)
            print("✅ CrewAI agents ready!")
        except Exception as e:
            print(f"❌ Error loading CrewAI: {e}")
            draft_crew = None
    else:
        print("⚠️ No ANTHROPIC_API_KEY found - AI features disabled")

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Fantasy Draft Assistant - Flask Dev Server</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
            padding: 20px; 
            background: #0f172a; 
            color: white; 
            margin: 0;
        }
        .container { 
            max-width: 1000px; 
            margin: 0 auto; 
        }
        .header {
            background: linear-gradient(90deg, #8b5cf6, #2563eb);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            text-align: center;
        }
        .chat-container {
            display: flex;
            gap: 20px;
            height: 70vh;
        }
        .chat-area {
            flex: 1;
            background: #1e293b;
            border-radius: 8px;
            padding: 20px;
            display: flex;
            flex-direction: column;
        }
        .status-area {
            width: 300px;
            background: #1e293b;
            border-radius: 8px;
            padding: 20px;
        }
        #messages {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 20px;
            padding: 10px;
            background: #0f172a;
            border-radius: 4px;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 8px;
        }
        .user-message {
            background: #2563eb;
            text-align: right;
        }
        .ai-message {
            background: #059669;
        }
        .system-message {
            background: #7c2d12;
            font-style: italic;
        }
        .input-area {
            display: flex;
            gap: 10px;
        }
        input[type="text"] { 
            flex: 1;
            padding: 12px; 
            border: 1px solid #475569;
            background: #334155;
            color: white;
            border-radius: 4px;
            font-size: 16px;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #2563eb;
        }
        button { 
            padding: 12px 20px; 
            background: #10b981; 
            color: white; 
            border: none; 
            cursor: pointer;
            border-radius: 4px;
            font-weight: 600;
        }
        button:hover {
            background: #059669;
        }
        button:disabled {
            background: #6b7280;
            cursor: not-allowed;
        }
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        .status-ok { background: #10b981; }
        .status-error { background: #ef4444; }
        .examples {
            margin-top: 20px;
        }
        .example-btn {
            display: block;
            width: 100%;
            margin-bottom: 8px;
            padding: 8px;
            background: #475569;
            border: 1px solid #64748b;
            color: white;
            text-align: left;
            cursor: pointer;
            border-radius: 4px;
            font-size: 14px;
        }
        .example-btn:hover {
            background: #64748b;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏈 Fantasy Draft Assistant - DEV MODE</h1>
            <p>Real CrewAI Multi-Agent System | SUPERFLEX League Focus</p>
        </div>
        
        <div class="chat-container">
            <div class="chat-area">
                <div id="messages">
                    <div class="message system-message">
                        🤖 Welcome! I'm your Fantasy Draft Assistant powered by a 4-agent CrewAI system.<br>
                        Ask me specific questions about your SUPERFLEX draft and I'll give you real analysis.
                    </div>
                </div>
                
                <div class="input-area">
                    <input type="text" id="questionInput" placeholder="Ask about players, strategy, or comparisons..." />
                    <button id="askButton" onclick="askQuestion()">Ask AI</button>
                </div>
            </div>
            
            <div class="status-area">
                <h3>🔧 System Status</h3>
                <p><span id="agentStatus" class="status-indicator status-error"></span>AI Agents: <span id="agentText">Loading...</span></p>
                <p><span class="status-indicator status-ok"></span>Server: Online</p>
                <p><span class="status-indicator status-ok"></span>Port: 3000</p>
                
                <div class="examples">
                    <h4>💡 Try These Questions:</h4>
                    <button class="example-btn" onclick="askExample(this)">Should I draft Josh Allen in round 1?</button>
                    <button class="example-btn" onclick="askExample(this)">Compare Lamar Jackson vs Dak Prescott</button>
                    <button class="example-btn" onclick="askExample(this)">What RBs should I target after QBs?</button>
                    <button class="example-btn" onclick="askExample(this)">Best SUPERFLEX strategy for 2024?</button>
                    <button class="example-btn" onclick="askExample(this)">Who has the best value in rounds 3-5?</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let isProcessing = false;
        
        // Check status on load
        checkStatus();
        
        async function checkStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                const statusEl = document.getElementById('agentStatus');
                const textEl = document.getElementById('agentText');
                
                if (data.agents_loaded) {
                    statusEl.className = 'status-indicator status-ok';
                    textEl.textContent = 'Ready';
                } else {
                    statusEl.className = 'status-indicator status-error';
                    textEl.textContent = 'Error';
                }
            } catch (error) {
                document.getElementById('agentText').textContent = 'Error';
            }
        }
        
        async function askQuestion() {
            const input = document.getElementById('questionInput');
            const question = input.value.trim();
            
            if (!question || isProcessing) return;
            
            isProcessing = true;
            const button = document.getElementById('askButton');
            button.disabled = true;
            button.textContent = 'Thinking...';
            
            // Add user message
            addMessage('user', question);
            input.value = '';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: question})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addMessage('ai', data.response);
                } else {
                    addMessage('system', '❌ Error: ' + data.error);
                }
            } catch (error) {
                addMessage('system', '❌ Connection error: ' + error.message);
            } finally {
                isProcessing = false;
                button.disabled = false;
                button.textContent = 'Ask AI';
            }
        }
        
        function askExample(button) {
            const question = button.textContent;
            document.getElementById('questionInput').value = question;
            askQuestion();
        }
        
        function addMessage(type, message) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + type + '-message';
            
            const prefix = type === 'user' ? '👤 You: ' : 
                          type === 'ai' ? '🤖 AI: ' : '🔔 System: ';
            
            messageDiv.innerHTML = prefix + message.replace(/\\n/g, '<br>');
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        // Enter key support
        document.getElementById('questionInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !isProcessing) {
                askQuestion();
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    """Serve the main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    """Real AI chat using CrewAI agents"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        print(f"💬 Question: {message}")
        
        if not draft_crew:
            return jsonify({
                "success": False,
                "error": "AI agents not initialized - check ANTHROPIC_API_KEY in .env.local"
            })
        
        # Context for SUPERFLEX league
        context = {
            "league_format": "SUPERFLEX",
            "scoring": "Half-PPR", 
            "teams": 12,
            "draft_position": "TBD"
        }
        
        # Get real AI response - need to run async function
        print("🤖 Calling CrewAI agents...")
        
        async def get_response():
            return await draft_crew.analyze_draft_question(message, context)
        
        # Run async function in new event loop
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(get_response())
            loop.close()
        except Exception as e:
            print(f"❌ CrewAI error: {e}")
            response = f"CrewAI system had an error: {str(e)}\n\nFor SUPERFLEX leagues, remember:\n- QBs are premium (Josh Allen, Lamar Jackson worth early picks)\n- Target 2-3 QBs by round 7\n- Positional scarcity matters more than standard leagues"
        
        print("✅ Response generated")
        return jsonify({
            "success": True,
            "response": response,
            "agent_type": "CrewAI Multi-Agent System"
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/status')
def status():
    """Check server status"""
    return jsonify({
        "status": "running",
        "agents_loaded": draft_crew is not None,
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    init_agents()
    print("🌐 Starting Flask server at http://localhost:3000")
    app.run(host='0.0.0.0', port=3000, debug=True)