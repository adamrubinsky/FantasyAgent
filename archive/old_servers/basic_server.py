#!/usr/bin/env python3
"""
Basic HTTP Server for Fantasy Draft Assistant
Using Python's built-in HTTP server to avoid dependency issues
"""

import json
import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Global variables
draft_crew = None

def init_agents():
    """Initialize CrewAI agents"""
    global draft_crew
    
    print("🚀 Starting Fantasy Draft Assistant - Basic HTTP Server")
    print("📡 Initializing CrewAI agents...")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        try:
            from agents.draft_crew import FantasyDraftCrew
            draft_crew = FantasyDraftCrew(anthropic_api_key=api_key)
            print("✅ CrewAI agents ready!")
            return True
        except Exception as e:
            print(f"❌ Error loading CrewAI: {e}")
            draft_crew = None
            return False
    else:
        print("⚠️ No ANTHROPIC_API_KEY found - AI features disabled")
        return False

class FantasyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_html()
        elif self.path == '/api/status':
            self.send_status()
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/chat':
            self.handle_chat()
        else:
            self.send_response(404)
            self.end_headers()
    
    def send_html(self):
        html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Fantasy Draft Assistant - Basic Server</title>
    <meta charset="utf-8">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
            padding: 20px; 
            background: #0f172a; 
            color: white; 
            margin: 0;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header {
            background: linear-gradient(90deg, #8b5cf6, #2563eb);
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            text-align: center;
        }
        .chat-area {
            background: #1e293b;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        #messages {
            height: 400px;
            overflow-y: auto;
            margin-bottom: 20px;
            padding: 15px;
            background: #0f172a;
            border-radius: 4px;
            border: 1px solid #475569;
        }
        .message {
            margin-bottom: 15px;
            padding: 12px;
            border-radius: 8px;
            line-height: 1.5;
        }
        .user-message {
            background: #2563eb;
            text-align: right;
        }
        .ai-message {
            background: #059669;
            white-space: pre-wrap;
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
        button:hover { background: #059669; }
        button:disabled {
            background: #6b7280;
            cursor: not-allowed;
        }
        .examples {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 10px;
            margin-top: 20px;
        }
        .example-btn {
            padding: 10px;
            background: #475569;
            border: 1px solid #64748b;
            color: white;
            cursor: pointer;
            border-radius: 4px;
            font-size: 14px;
            transition: background 0.2s;
        }
        .example-btn:hover {
            background: #64748b;
        }
        .status { 
            text-align: center; 
            margin-bottom: 20px;
            padding: 10px;
            background: #1e293b;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏈 Fantasy Draft Assistant</h1>
            <p>Real CrewAI Multi-Agent System | SUPERFLEX League Focus</p>
        </div>
        
        <div class="status" id="status">
            <span id="statusText">Loading...</span>
        </div>
        
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
        
        <div class="examples">
            <button class="example-btn" onclick="askExample('Should I draft Josh Allen in round 1?')">Should I draft Josh Allen in round 1?</button>
            <button class="example-btn" onclick="askExample('Compare Lamar Jackson vs Dak Prescott')">Compare Lamar Jackson vs Dak Prescott</button>
            <button class="example-btn" onclick="askExample('What RBs should I target after QBs?')">What RBs should I target after QBs?</button>
            <button class="example-btn" onclick="askExample('Best SUPERFLEX strategy for 2024?')">Best SUPERFLEX strategy for 2024?</button>
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
                
                const statusEl = document.getElementById('statusText');
                
                if (data.agents_loaded) {
                    statusEl.innerHTML = '✅ AI Agents Ready | Server: localhost:3000';
                    statusEl.style.color = '#10b981';
                } else {
                    statusEl.innerHTML = '❌ AI Agents Failed to Load | Check Console';
                    statusEl.style.color = '#ef4444';
                }
            } catch (error) {
                document.getElementById('statusText').innerHTML = '❌ Server Connection Error';
                document.getElementById('statusText').style.color = '#ef4444';
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
        
        function askExample(question) {
            document.getElementById('questionInput').value = question;
            askQuestion();
        }
        
        function addMessage(type, message) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + type + '-message';
            
            const prefix = type === 'user' ? '👤 You: ' : 
                          type === 'ai' ? '🤖 AI: ' : '🔔 System: ';
            
            messageDiv.textContent = prefix + message;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        // Enter key support
        document.getElementById('questionInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !isProcessing) {
                askQuestion();
            }
        });
        
        // Auto-refresh status every 30 seconds
        setInterval(checkStatus, 30000);
    </script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def send_status(self):
        status_data = {
            "status": "running",
            "agents_loaded": draft_crew is not None,
            "timestamp": "now"
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(status_data).encode('utf-8'))
    
    def handle_chat(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            message = data.get('message', '')
            print(f"💬 Question: {message}")
            
            if not draft_crew:
                response_data = {
                    "success": False,
                    "error": "AI agents not initialized - check ANTHROPIC_API_KEY in .env.local"
                }
            else:
                # Context for SUPERFLEX league
                context = {
                    "league_format": "SUPERFLEX",
                    "scoring": "Half-PPR",
                    "teams": 12,
                    "draft_position": "TBD"
                }
                
                print("🤖 Calling CrewAI agents...")
                
                try:
                    # Run async function
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    response = loop.run_until_complete(
                        draft_crew.analyze_draft_question(message, context)
                    )
                    loop.close()
                    
                    response_data = {
                        "success": True,
                        "response": response,
                        "agent_type": "CrewAI Multi-Agent System"
                    }
                    print("✅ Response generated")
                    
                except Exception as e:
                    print(f"❌ CrewAI error: {e}")
                    response_data = {
                        "success": False,
                        "error": f"AI processing error: {str(e)}"
                    }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            print(f"❌ Chat error: {e}")
            error_response = {
                "success": False,
                "error": str(e)
            }
            
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
    
    def log_message(self, format, *args):
        # Suppress default logging
        return

if __name__ == '__main__':
    # Initialize agents
    agents_ready = init_agents()
    
    if not agents_ready:
        print("⚠️  AI agents failed to load, but server will still start for testing")
    
    # Start server
    server = HTTPServer(('0.0.0.0', 3000), FantasyHandler)
    print(f"🌐 Basic server running at http://localhost:3000")
    print(f"🤖 AI Agents: {'Ready' if agents_ready else 'Failed'}")
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        server.server_close()