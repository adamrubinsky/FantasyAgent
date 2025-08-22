# FantasyAgent Issue Log

## Phase 2 Day 4 - August 18, 2025

### Issue #1: CrewAI Agent Recommending Already Drafted Players
**Status**: Partially Resolved / Won't Fix for Completed Drafts

**Description**: 
Agent was recommending Joe Burrow despite user already having him on roster. Agent also recommended Josh Allen and Lamar Jackson as available in Round 18.

**Investigation**:
1. Context was being passed but with wrong data structure
2. draft_monitor.py wasn't returning draft picks to unified_server
3. Sleeper API returns `null` for completed/archived draft picks

**Root Cause**:
- Draft ID `1025303554033897472` returns null from Sleeper API
- Likely an archived or private completed draft
- Server finds roster (17 players) but can't get full draft data
- Without draft history, agent thinks all players are available

**Attempted Fixes**:
1. ✅ Added context passing in unified_server.py (lines 215-217)
2. ✅ Modified draft_monitor.py to return draftPicks and availablePlayers
3. ❌ Cannot fix API returning null for completed drafts

**Resolution**:
User decided this doesn't need fixing as it only affects completed/archived drafts. Live drafts should work correctly.

### Issue #2: Import Path Inconsistencies
**Status**: Resolved

**Description**:
After reorganization, import paths were using old structure

**Fix**:
Updated all server files to use `platforms.sleeper.agents.draft_crew` instead of `agents.draft_crew`

**Files Fixed**:
- unified_server.py
- dev_server.py  
- server.py
- web_app.py
- main.py

### Issue #3: Undefined 'client' Variable in draft_monitor.py
**Status**: Resolved

**Description**:
draft_monitor.py tried to use undefined 'client' variable when fetching available players

**Fix**:
Removed the problematic code and simplified to return empty available_players for completed drafts

## Phase 3 Day 2 - August 22, 2025

### Issue #4: Sleeper Auction UI Widgets Not Loading Data
**Status**: Resolved ✅

**Description**:
During mock auction draft testing, multiple UI widgets showed placeholder or incorrect data:
- Draft Status: "#" instead of pick numbers
- Remaining Budget: $200 instead of actual $37
- Your Roster: "Empty" despite having 3 players
- Proactive Analysis: Generic messages
- Recent Picks: Player IDs instead of names
- Available Players: Not updating

**Root Causes**:
1. Platform check logic preventing auction code execution
2. No player ID to name resolution system
3. Missing field mappings for auction data
4. No drafted player tracking

**Fixes Applied**:
1. ✅ Fixed platform check in draft_monitor.py line 752
2. ✅ Created SleeperPlayerCache system with 7-day TTL
3. ✅ Added proper field mappings in unified_server.py
4. ✅ Implemented max bid calculations with position caps

### Issue #5: Agent Recommending Drafted Players
**Status**: Resolved ✅

**Description**:
Chat agent was recommending players already drafted (Chase, Lamb, Jefferson) and suggesting players above budget ($15 when only $10 available)

**Root Causes**:
1. No drafted player filtering in agent
2. Name suffix mismatches (Jr., Sr., III)
3. No budget awareness in recommendations

**Fixes Applied**:
1. ✅ Added name normalization for suffixes
2. ✅ Implemented budget-aware player filtering
3. ✅ Added drafted player list to agent context
4. ✅ Enhanced prompts with budget constraints

### Issue #6: Late Draft Strategy Issues
**Status**: Resolved ✅

**Description**:
Agent suggesting expensive "decoy" nominations when most teams only have $1-3 left in endgame (after pick 135)

**Root Cause**:
No awareness of draft phase and other teams' budget constraints

**Fix Applied**:
✅ Added late-draft intelligence:
- After pick 135/192, assumes all teams budget-constrained
- Recommends nominating players you actually want at $1-2
- No more expensive decoy strategy in endgame

### Performance Summary
- Widget updates: <1 second (real-time)
- Player name lookups: Instant (cached)
- Agent response time: <3 seconds maintained
- All widgets functional and updating properly