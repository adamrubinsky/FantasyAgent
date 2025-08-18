# Yahoo Snake Draft Implementation Plan
## Date: August 18, 2025
## Draft Date: August 19, 2025 (Tomorrow!)

## Current State Analysis

### What We Have:
1. **Yahoo OAuth Credentials** (in `.env.local`)
   - Client ID, Secret, App ID all configured
   - Redirect URI: `https://localhost:3000/auth/yahoo/callback`
   - Previous OAuth attempts in `yahoo_oauth_final.py`

2. **UI Widgets** (in `templates/unified.html`)
   - Draft Status widget
   - My Roster/Picks widget  
   - Available Players widget
   - Chat (agent responses)
   - Proactive Analysis widget
   - Recent Picks widget

3. **Backend Infrastructure**
   - `draft_monitor.py` - Currently returns MOCK data for Yahoo
   - `yahoo_snake_agent.py` - LangGraph agent with <3s response times
   - Rankings API working (FantasyPros MCP)

### What's NOT Working:
1. **Real Yahoo API Integration** - Still using mock data
2. **Widget Data Flow** - Widgets not populating with real data
3. **OAuth Token Flow** - Not implemented in server
4. **Roster Tracking** - Not syncing with actual draft picks
5. **Available Players** - Not filtering out drafted players

## Implementation Plan

### Phase 1: Yahoo OAuth Integration (Priority 1)
**Goal**: Get real-time draft data from Yahoo API

#### Option A: Direct Yahoo API (Preferred if OAuth works)
```python
# yahoo_agents/clients/yahoo_oauth_handler.py
class YahooOAuthHandler:
    def __init__(self):
        self.client_id = os.getenv('YAHOO_CLIENT_ID')
        self.client_secret = os.getenv('YAHOO_CLIENT_SECRET')
        self.token_file = 'private/yahoo_token.json'
    
    async def get_access_token(self):
        # Check for existing token
        # Refresh if expired
        # Return valid token
    
    async def make_api_request(self, endpoint):
        # Add OAuth headers
        # Make request to Yahoo API
```

#### Option B: Web Scraping Fallback
```python
# yahoo_agents/clients/yahoo_scraper.py
class YahooScraper:
    async def get_draft_status(self, draft_url):
        # Use Playwright/Selenium to scrape draft room
        # Parse HTML for current pick, rosters, etc.
```

#### Option C: Manual Input Bridge
- User inputs current pick number
- Agent tracks picks manually
- Still provides recommendations

### Phase 2: Draft Monitor Integration (Priority 2)
**Goal**: Replace mock data with real Yahoo API calls

```python
# core/draft_monitor.py modifications
async def _get_yahoo_snake_status(self, draft_id: str) -> Dict[str, Any]:
    """Get real Yahoo draft status"""
    
    # Try OAuth API first
    try:
        oauth_handler = YahooOAuthHandler()
        token = await oauth_handler.get_access_token()
        
        # Yahoo Draft API endpoints
        draft_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{draft_id}/draftresults"
        teams_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{draft_id}/teams"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get draft results
        draft_data = await fetch_with_auth(draft_url, headers)
        
        # Parse current pick, rosters, etc.
        return parse_yahoo_draft_data(draft_data)
        
    except OAuthError:
        # Fall back to scraping
        return await self._scrape_yahoo_draft(draft_id)
```

### Phase 3: Widget Data Flow (Priority 3)
**Goal**: Connect all widgets to real data sources

#### 3.1 Draft Status Widget
```javascript
// Frontend: Poll for status every 5 seconds
async pollDraftStatus() {
    const response = await fetch('/api/draft-status', {
        method: 'POST',
        body: JSON.stringify({
            platform: 'yahoo-snake',
            url: this.draftUrl
        })
    });
    const data = await response.json();
    
    // Update UI
    this.currentPick = data.draftStatus.currentPick;
    this.currentRound = data.draftStatus.round;
    this.isMyTurn = data.draftStatus.myTurn;
}
```

#### 3.2 My Roster Widget
```python
# Backend: Track user's picks
async def get_user_roster(self, platform: str, draft_id: str) -> List[Dict]:
    """Get user's current roster"""
    
    if platform == "yahoo-snake":
        # Get from Yahoo API or tracked picks
        draft_status = await self._get_yahoo_snake_status(draft_id)
        user_slot = self.connected_drafts[platform]["draft_slot"]
        
        # Filter picks by user's team
        my_picks = [
            pick for pick in draft_status["all_picks"] 
            if pick["team_slot"] == user_slot
        ]
        
        return format_roster(my_picks)
```

#### 3.3 Available Players Widget
```python
# Backend: Filter drafted players from rankings
async def get_available_players(self, platform: str) -> List[Dict]:
    """Get top available players"""
    
    # Get all rankings
    rankings = await self.get_rankings(platform)
    
    # Get drafted players
    draft_status = await self.get_draft_status(platform)
    drafted_ids = [pick["player_id"] for pick in draft_status["all_picks"]]
    
    # Filter out drafted
    available = [
        player for player in rankings 
        if player["id"] not in drafted_ids
    ]
    
    return available[:50]  # Top 50 available
```

#### 3.4 Proactive Analysis Widget
```python
# Backend: Smart recommendations based on context
async def get_proactive_recommendation(self, platform: str, draft_status: Dict) -> Dict:
    """Generate context-aware recommendations"""
    
    if draft_status["myTurn"]:
        # It's user's turn - urgent recommendation
        context = {
            "current_pick": draft_status["currentPick"],
            "my_roster": await self.get_user_roster(platform, draft_id),
            "available": await self.get_available_players(platform)[:10]
        }
        
        # Get agent recommendation
        agent = state.get_yahoo_snake_agent()
        rec = await agent.get_quick_recommendation(context)
        
        return {
            "title": "🎯 YOUR PICK!",
            "content": rec["top_pick"],
            "alternatives": rec["alternatives"][:2],
            "urgency": "high"
        }
```

### Phase 4: Data Synchronization (Priority 4)
**Goal**: Keep all data in sync

1. **Polling Strategy**:
   - Draft status: Every 5 seconds
   - Available players: Every 10 seconds
   - Proactive analysis: Every 5 seconds when near user's turn

2. **Caching**:
   - Rankings: 30 minutes
   - Player data: 10 minutes
   - Draft picks: Real-time, no cache

3. **State Management**:
   ```python
   class DraftState:
       def __init__(self):
           self.current_pick = 0
           self.all_picks = []
           self.my_roster = []
           self.available_players = []
           self.last_update = None
   ```

## Implementation Steps

### Today (August 18):

1. **Test Yahoo OAuth** (1 hour)
   - Try `yahoo_oauth_final.py` again
   - If fails, implement scraping fallback

2. **Implement Real Draft Monitor** (2 hours)
   - Replace mock data in `_get_yahoo_snake_status()`
   - Add OAuth handler or scraper
   - Test with mock draft

3. **Connect Widgets** (2 hours)
   - Add `/api/roster` endpoint
   - Add `/api/available-players` endpoint
   - Update frontend polling

4. **Test Full Flow** (1 hour)
   - Join Yahoo mock draft
   - Verify all widgets update
   - Check response times

### Tomorrow Morning (August 19 - Draft Day):

1. **Final Testing** (30 min)
   - Test OAuth token refresh
   - Verify all endpoints
   - Check performance

2. **Backup Plans**:
   - Manual input UI ready
   - Scraping script tested
   - Mobile app as fallback

## API Endpoints Needed

### New Endpoints:
```python
@app.get("/api/roster/{platform}")
async def get_roster(platform: str):
    """Get user's current roster"""
    
@app.get("/api/available/{platform}")  
async def get_available(platform: str):
    """Get top available players"""
    
@app.post("/api/manual-pick")
async def record_manual_pick(pick: ManualPick):
    """Manually record a pick if API fails"""
```

### Modified Endpoints:
```python
@app.post("/api/draft-status")
# Add real Yahoo API calls

@app.post("/api/connect-draft")  
# Add OAuth token initialization
```

## Testing Checklist

- [ ] Yahoo OAuth token obtained
- [ ] Mock draft connection works
- [ ] Draft status updates in real-time
- [ ] My Roster populates correctly
- [ ] Available Players filters drafted
- [ ] Proactive Analysis shows relevant tips
- [ ] Response time <3 seconds
- [ ] All error cases handled

## Fallback Options

1. **If OAuth Fails**:
   - Use web scraping with Playwright
   - Manual input mode
   - Export/import draft board

2. **If API is Slow**:
   - Cache more aggressively
   - Pre-fetch likely scenarios
   - Reduce polling frequency

3. **If Everything Fails**:
   - Standalone recommendations mode
   - User inputs current situation
   - Agent provides advice

## Success Metrics

- OAuth connection established ✅
- Real-time draft data flowing ✅
- All widgets showing correct data ✅
- Response time <3 seconds ✅
- No errors during 16-round draft ✅

## Notes

- Yahoo API rate limit: 20,000 requests/hour (plenty)
- Draft typically takes 90 minutes
- Need ~960 API calls (1 per 5 seconds)
- Well within limits

## Next Steps After Implementation

1. Record actual draft for analysis
2. Compare recommendations vs actual results
3. Optimize for League 3 auction (Aug 24)
4. Add trade analyzer for season