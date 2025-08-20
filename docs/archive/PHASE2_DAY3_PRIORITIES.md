# Phase 2, Day 3 Priorities - August 17, 2025

## 🎯 Start Here
Welcome to Day 3 of Phase 2! This document will guide you through today's priorities.

### Context Documents to Read First
1. **CLAUDE.md** - Critical guidelines and system requirements
2. **docs/ACTION_LOG.md** - See Day 2 accomplishments and current state
3. **docs/issue_log.md** - Review Issue #9 (Yahoo MemorySaver)
4. **Memory MCP** - Search for "Phase 2 Day 2" and "Unified Architecture"

### Current System State
- ✅ **Sleeper Platform**: Fully functional on unified server (port 3001)
- ✅ **Vue.js UI**: Beautiful interface with platform switcher working
- ✅ **Proactive Panel**: Added to UI but API endpoint not implemented
- ⚠️ **Yahoo Agents**: Mock responses only (MemorySaver import error)

---

## 📋 Priority Tasks for Today

### 1. Fix Yahoo Agents MemorySaver Import 🔴 CRITICAL
**File**: `yahoo_agents/agents/yahoo_snake_agent.py` and `yahoo_auction_agent.py`
**Issue**: `cannot import name 'MemorySaver' from 'langgraph.checkpoint'`
**Action**: 
- Check LangGraph version and update imports
- May need to use `MemorySaver` from different module or update package
- Ensure <3s response time requirement is met

### 2. Implement Proactive Recommendations Endpoint
**File**: `unified_server.py`
**Route**: `/api/proactive-check`
**Requirements**:
- Only for Sleeper platform initially
- Call `check_proactive_recommendations()` from draft_crew
- Return formatted recommendations for UI display
- Include title, content, and optional action

### 3. Add Draft URL Input Field
**File**: `templates/unified.html`
**Location**: Below platform selector
**Features**:
- Input field for Sleeper draft URL
- Parse draft_id and connect to live draft
- Show connection status
- Enable proactive monitoring when connected

### 4. Test Yahoo Snake Agent (League 2)
**League Details**:
- 10-team (not 12!)
- Full PPR (1.0 points)
- 6PT passing TDs (15% QB boost)
- Return yards count
**Testing**:
- Verify scoring adjustments applied
- Check <3s response time
- Test with sample queries

### 5. Test Sleeper Auction Agent (League 3)
**League Details**:
- 12-team
- Half PPR (0.5 points)
- $200 budget
- NO KICKER position
- Stars & Scrubs strategy (70% on 3-4 elite)
**Testing**:
- Verify auction value calculations
- Check budget recommendations
- Test value-based drafting logic

### 6. Performance Optimization (If Time Permits)
- Reduce Sleeper response time from 17s
- Implement better caching strategies
- Consider parallel agent execution
- Add loading states for better UX

---

## 🚀 Quick Commands

### Start the unified server:
```bash
python3 unified_server.py
# Access at http://localhost:3001
```

### Test Sleeper agent:
```bash
curl -X POST "http://localhost:3001/api/select-platform" \
  -H "Content-Type: application/json" \
  -d '{"platform": "sleeper"}'

curl -X POST "http://localhost:3001/api/draft-query" \
  -H "Content-Type: application/json" \
  -d '{"platform": "sleeper", "query": "Who should I draft?", "context": {}}'
```

### Check server health:
```bash
curl "http://localhost:3001/api/health"
```

---

## 📝 Important Notes

### DO NOT MODIFY
- `/agents/` directory (working Sleeper production system)
- `dev_server.py` (original working server)
- Port 3000 (keep original system intact)

### File Locations
- **Unified Server**: `unified_server.py`
- **Unified UI**: `templates/unified.html`
- **Yahoo Agents**: `yahoo_agents/agents/`
- **Alternative Server**: `server.py` (has similar fixes)

### Known Working State
- Sleeper queries work but take ~17 seconds
- Platform switching works perfectly in UI
- WebSocket connections established
- API key properly loaded and passed

### Yahoo Draft Dates
- **League 2 (Snake)**: August 19, 2025 (2 days away!)
- **League 3 (Auction)**: August 24, 2025

---

## 🎓 Success Criteria
1. Yahoo agents load without import errors
2. Both Yahoo agents respond in <3 seconds
3. Proactive recommendations appear for connected drafts
4. Draft URL input connects to live Sleeper drafts
5. All three platforms selectable and functional

---

## 💡 Tips
- Use `python3` not `python` for all commands
- Check Memory MCP for additional context
- Refer to CLAUDE.md for critical guidelines
- Keep Yahoo and Sleeper systems isolated
- Test frequently with the curl commands above

Good luck with Day 3! The Yahoo drafts are coming up soon (Aug 19 and 24), so getting those agents working is the top priority.