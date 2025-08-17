# 🚀 FantasyAgent Startup Guide - Adam's Quick Reference

## Starting the System (From Terminal)

### 1. Navigate to Project Directory
```bash
cd /Users/adamrubinsky/VSCode/FantasyAgent
```

### 2. Activate Virtual Environment (if you have one)
```bash
# If using venv
source venv/bin/activate

# If using conda
conda activate fantasyagent
```

### 3. Start the Development Server
```bash
python3 dev_server.py
```

**Expected Output:**
```
🚀 Starting Fantasy Draft Assistant - Development Server
📡 Port: 3000 (avoiding conflicts with other services)
🔄 Cache busting: ENABLED
🤖 Real AI agents: ENABLED
🌐 URL: http://localhost:3000

🚀 Starting Fantasy Draft Assistant - DEV MODE
📡 Initializing AI agents...
🔄 Pre-initializing AI agents (this may take 30-60 seconds)...
✅ Agents already initialized
✅ AI agents ready!
```

### 4. Access the Web Interface
Open browser to: **http://localhost:3000**

### 5. Connect to Your Draft
1. Get your Sleeper draft URL (e.g., https://sleeper.com/draft/nfl/1261075629885894656)
2. Paste it into the "Draft URL" field
3. Enter your roster slot number (e.g., 5)
4. Click "Connect to Draft"

---

## 🛑 Stopping the Server

### Normal Shutdown
Press `Ctrl+C` in the terminal where the server is running

### If That Doesn't Work
```bash
# Find the process
ps aux | grep "python3 dev_server.py"

# Kill the process (replace PID with the actual process ID)
kill -9 PID

# Or kill all Python processes (use carefully!)
pkill -f "python3 dev_server.py"
```

---

## 🔧 Troubleshooting Common Issues

### Issue: Port 3000 Already in Use (MOST COMMON!)

**Quick Fix - One Line Command:**
```bash
# This kills anything on port 3000 and restarts the server
lsof -ti:3000 | xargs kill -9; sleep 2; python3 dev_server.py
```
# All in one restart
  pkill -f "dev_server.py"; sleep 1; cd /Users/adamrubinsky/VSCode/FantasyAgent &&
  /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 dev_server.py
**Alternative One-Liner:**
```bash
# Kill all python processes and restart
pkill -f python3; pkill -f dev_server; sleep 2; python3 dev_server.py
```

**Manual Method:**
```bash
# Find what's using port 3000
lsof -i :3000

# Kill the process (replace PID with actual number)
kill -9 <PID>

# Then restart
python3 dev_server.py
```

### Issue: Server Crashes or Hangs
```bash
# Force kill all related processes
pkill -f dev_server
pkill -f python3

# Clear any cache files
rm -rf __pycache__
rm -rf agents/__pycache__
rm -rf core/__pycache__

# Restart
python3 dev_server.py
```

### Issue: "Module not found" Errors
```bash
# Reinstall dependencies
pip3 install -r requirements.txt

# If specific module missing
pip3 install crewai anthropic fastapi uvicorn aiohttp
```

### Issue: API Key Errors
```bash
# Check your .env.local file
cat .env.local

# Should contain:
# ANTHROPIC_API_KEY=sk-ant-api03-...
# SLEEPER_USERNAME=your-username
# FANTASYPROS_API_KEY=your-key (optional)

# If missing, copy from example
cp .env.example .env.local
# Then edit with your actual keys
nano .env.local
```

### Issue: Draft Not Connecting
1. Verify draft URL is correct format
2. Check roster slot number (1-12, not 0-indexed)
3. Try disconnecting and reconnecting:
   - Refresh browser (Cmd+R)
   - Re-enter draft URL
   - Click Connect again

### Issue: Slow AI Responses
**Normal response times:**
- Proactive at your pick: 5 seconds
- Chat recommendations: 15-30 seconds

**If slower:**
```bash
# Restart the server to clear memory
Ctrl+C
python3 dev_server.py

# Check system resources
top
# Look for high CPU/memory usage
```

### Issue: Proactive Analysis Not Showing
1. Wait 5-10 seconds after connecting
2. Check browser console for errors (Cmd+Option+I)
3. Verify you're at/near your pick
4. Refresh page and reconnect

---

## 📊 Monitoring Server Health

### Check Server Status
```bash
# In a new terminal tab
curl http://localhost:3000/api/dev-status
```

### Watch Server Logs
The terminal running dev_server.py shows real-time logs:
- `🎯` Draft events
- `📊` State updates  
- `✅` Successful operations
- `❌` Errors

### Check Python Version
```bash
python3 --version
# Should be 3.10 or higher
```

---

## 🔄 Quick Restart Sequence

If something seems wrong, follow this sequence:

```bash
# 1. Stop server
Ctrl+C

# 2. Clear any stuck processes
pkill -f dev_server

# 3. Clear cache
rm -rf __pycache__

# 4. Restart
python3 dev_server.py

# 5. Reconnect in browser
# Refresh page, re-enter draft URL
```

---

## 💡 Pro Tips

1. **Keep a second terminal tab open** for troubleshooting commands
2. **Save your draft URL** in a text file for quick access
3. **Note your roster slot** before the draft starts
4. **Test connection** 30 minutes before actual draft
5. **Have backup plan**: Keep FantasyPros rankings open in another tab

---

## 📱 Running in Background (Advanced)

If you want the server to keep running even after closing terminal:

```bash
# Start with nohup
nohup python3 dev_server.py > fantasyagent.log 2>&1 &

# Check it's running
ps aux | grep dev_server

# View logs
tail -f fantasyagent.log

# Stop background process
pkill -f dev_server
```

---

## 🆘 Emergency Commands

```bash
# ONE-LINE NUCLEAR OPTION (kills port 3000 and restarts)
lsof -ti:3000 | xargs kill -9; sleep 2; python3 dev_server.py

# Alternative nuclear option - kill everything and restart
pkill -f python
pkill -f dev_server
cd /Users/adamrubinsky/VSCode/FantasyAgent
python3 dev_server.py

# Check what's running on port 3000
lsof -i :3000

# Free up memory
# Close other applications, especially Chrome tabs

# Test basic Python
python3 -c "print('Python works')"

# Test imports
python3 -c "import crewai; print('CrewAI works')"
python3 -c "import anthropic; print('Anthropic works')"
```

---

## 📞 Getting Help

If all else fails:
1. Screenshot the error
2. Copy the last 20 lines of terminal output
3. Note what you were doing when it broke
4. Check ACTION_LOG.md for similar issues
5. Restart everything and try once more

Remember: The server auto-reloads when you edit files, so you don't need to restart for code changes!

---

**Last Updated**: August 12, 2025 (Day 8 Evening)
**Status**: Production Ready - Agent performing as intended!