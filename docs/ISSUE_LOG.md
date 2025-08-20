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