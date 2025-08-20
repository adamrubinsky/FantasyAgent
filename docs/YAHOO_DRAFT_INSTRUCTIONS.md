# Yahoo Draft Instructions - August 19, 2025

## 🚨 CRITICAL: OAuth Token Management

### Token Expiry Issue
- **Yahoo OAuth tokens expire after EXACTLY 1 HOUR**
- You MUST refresh the token before or during the draft
- Token expired at 7:41 PM during testing (created at 6:41 PM)

### How to Refresh Token
```bash
python3 config/yahoo/refresh_yahoo_token.py
```

### Check Token Status
```bash
python3 -c "import json; from datetime import datetime; 
data = json.load(open('private/yahoo_token.json')); 
expires = data.get('expires_at', ''); 
print(f'Token expires at: {expires}');
now = datetime.now();
expires_dt = datetime.fromisoformat(expires);
if now > expires_dt:
    print('❌ TOKEN EXPIRED - REFRESH NOW!')
else:
    mins_left = (expires_dt - now).seconds // 60
    print(f'✅ Token valid for {mins_left} more minutes')"
```

## 📋 Draft Day Checklist

### 30 Minutes Before Draft
1. **Start the server**:
   ```bash
   python3 unified_server.py
   ```

2. **Refresh OAuth token**:
   ```bash
   python3 config/yahoo/refresh_yahoo_token.py
   ```

3. **Open browser**: http://localhost:3001

4. **Connect to draft**:
   - Select "Yahoo Snake Draft" from dropdown
   - Enter draft URL (format: `https://football.fantasysports.yahoo.com/draftclient/f1/9124471/10?auth=`)
   - Enter your draft position: **10**
   - Click "Connect to Draft"

### During Draft
- **Monitor token expiry** - refresh if approaching 1 hour
- **Watch server logs** for "Yahoo token expired" messages
- **Use "Top Available Players" widget** - this one works correctly
- **Ask agent questions** despite UI issues:
  - "Who should I draft?"
  - "Best WR available?"
  - "RB or WR here?"

## 🎯 Your Draft Position
- **Pick #10** (last pick of round 1)
- **Snake draft pattern**:
  - Round 1: Pick #10
  - Round 2: Pick #11 (back-to-back)
  - Round 3: Pick #30
  - Round 4: Pick #31 (back-to-back)
  - Round 5: Pick #50
  - Round 6: Pick #51 (back-to-back)

## ⚠️ Known Issues & Workarounds

### What's Working ✅
- Yahoo API connection (with valid token)
- Draft data fetching (picks, rosters)
- Agent has full context of draft
- Rankings/"Top Available Players" widget
- Agent response time <3 seconds

### What's Not Working ❌
- **Your Roster widget**: Shows empty (but agent knows your picks)
- **Recent Picks widget**: Shows "Unknown Player" (but data exists)
- **Proactive Analysis**: Shows wrong "picks until turn" number
- **Draft Status**: Missing next pick number

### Workarounds
1. **Trust the agent** - it has the correct draft data even if UI doesn't show it
2. **Use Rankings widget** to see who's available
3. **Check server logs** to verify your picks are tracked
4. **Refresh token immediately** if you see any OAuth errors

## 🔧 Emergency Fixes

### If Token Expires During Draft
```bash
# In a new terminal (keep server running)
python3 config/yahoo/refresh_yahoo_token.py

# The server should pick up the new token automatically
# If not, restart the server
```

### If Agent Gives Generic Responses
- Check server logs for "Yahoo token expired"
- Refresh token
- Reconnect to draft in UI

### If Nothing Works
- The agent will still work with FantasyPros rankings
- Use: "Who are the top available WRs?" type questions
- Agent knows Full PPR scoring adjustments

## 📊 League Settings (Full PPR)
- **Scoring**: Full PPR (1 point per reception)
- **QB Scoring**: 6 PT passing TDs (15% QB boost)
- **Return Yards**: 25 yards = 1 point
- **Teams**: 10
- **Draft Type**: Snake

## 🎮 Agent Strategy
The Yahoo agent is configured for:
- **WR Priority** in Full PPR (25% boost)
- **Pass-catching RBs** valued higher
- **Return specialists** get bonus consideration
- **QBs** adjusted for 6PT passing TDs

## 💡 Pro Tips
1. Set a timer for 50 minutes after refreshing token
2. Keep the refresh command ready to copy/paste
3. Have a backup browser tab with FantasyPros rankings
4. The agent works best with specific questions
5. Don't panic if UI looks broken - agent has the data

---

**Remember**: The core agent functionality works even if the display doesn't. Focus on asking good questions and trust the recommendations!