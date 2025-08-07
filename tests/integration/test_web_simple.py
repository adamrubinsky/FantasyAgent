#!/usr/bin/env python3
"""
Simple web server test to diagnose connectivity issues
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def test_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fantasy Draft Assistant - Test</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; padding: 20px; background: #0f172a; color: white;">
        <h1 style="color: #10b981;">🏈 Fantasy Draft Assistant - Connection Test</h1>
        <p>✅ If you can see this page, the web server is working!</p>
        
        <div style="background: #1e293b; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3>System Status:</h3>
            <p>✅ FastAPI Server: <span style="color: #10b981;">RUNNING</span></p>
            <p>✅ HTML Rendering: <span style="color: #10b981;">WORKING</span></p>
            <p>📱 Browser Compatibility: <span style="color: #10b981;">OK</span></p>
        </div>
        
        <div style="background: #1e293b; padding: 15px; border-radius: 8px;">
            <h3>Next Steps:</h3>
            <p>1. If this loads, the basic web server is working</p>
            <p>2. We can then test the full draft interface</p>
            <p>3. WebSocket connections will be tested next</p>
        </div>
        
        <script>
            console.log("✅ JavaScript is working");
            document.body.innerHTML += '<p style="color: #10b981;">✅ JavaScript: WORKING</p>';
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    print("🚀 Starting Simple Test Server...")
    print("📱 Open browser to: http://localhost:8001")
    print("🔍 This will test basic connectivity before the full app")
    
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")