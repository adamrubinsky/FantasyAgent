# Fantasy Football Draft Assistant - Project Overview

## 📋 Project Summary
This is an AI-powered fantasy football draft assistant built to provide real-time recommendations during live drafts. The system is designed to work within the critical 90-second pick window and integrates with multiple fantasy platforms.

**Target Date**: August 14th, 2025 (Sleeper draft)  
**League Type**: SUPERFLEX (QBs are much more valuable!)  
**Development Approach**: Local development first, then AWS AgentCore deployment

---

## 🏗️ Project Structure & File Explanations

### Root Directory Files

#### `main.py` - Main Entry Point & CLI Interface
- **Purpose**: Primary command-line interface for interacting with the draft assistant
- **Key Functions**:
  - `test()` - Tests connection to Sleeper API with your actual league data
  - `league()` - Displays your league information in a formatted table
  - `available()` - Shows available players, filterable by position
- **Dependencies**: Click for CLI, Rich for pretty terminal output
- **Usage**: `python3 main.py test` or `python3 main.py available -p QB -l 10`

#### `requirements.txt` - Python Dependencies
- **Purpose**: Lists all Python packages needed for the project
- **Key Dependencies**:
  - `crewai` - AI agent framework for multi-agent collaboration
  - `aiohttp` - Async HTTP client for API calls
  - `anthropic` - Claude AI integration
  - `click` + `rich` - CLI interface and pretty output
  - `pandas` - Data manipulation (future use)

#### `.env` & `.env.example` - Environment Configuration
- **Purpose**: Stores API keys and configuration settings
- **Contents**:
  - Your Sleeper username and league ID
  - Anthropic API key (for Claude integration)
  - Future Yahoo API credentials
  - Debug and logging settings
- **Security**: `.env` is gitignored, `.env.example` shows format

#### `.gitignore` - Git Exclusions
- **Purpose**: Prevents sensitive files from being committed to GitHub
- **Excludes**: API keys, cache files, Python bytecode, IDE settings

---

## 📁 Directory Structure

### `/api/` - External API Clients
Contains all code for communicating with external fantasy football services.

#### `sleeper_client.py` - Sleeper API Integration
- **Purpose**: Complete interface to Sleeper Fantasy Football API
- **Key Classes**:
  - `SleeperClient` - Main client class with async context manager
- **Key Methods**:
  - `get_user()` - Fetches user info by username
  - `get_league_info()` - Gets league settings and metadata
  - `get_draft_picks()` - Retrieves all picks made in draft so far
  - `get_all_players()` - Downloads full NFL player database (~5MB, cached)
  - `get_available_players()` - Filters out drafted players, sorts by rank
- **Special Features**:
  - Automatic caching of player data (refreshes daily)
  - SSL handling for macOS development
  - Comprehensive error handling and logging
  - Position filtering (crucial for SUPERFLEX)
- **No Authentication Required**: Sleeper API is completely public

### `/agents/` - AI Agent Components
Will contain CrewAI agents for draft analysis (Day 4+ implementation).

**Planned Agents**:
- **Data Collector Agent** - Fetches live data from APIs
- **Analysis Agent** - Evaluates player stats and projections  
- **Strategy Agent** - Considers league settings and roster construction
- **Recommendation Agent** - Synthesizes final pick suggestions

### `/core/` - Core Business Logic
Will contain the main draft monitoring and recommendation services.

**Planned Components**:
- **Draft Monitor** - Polls for real-time updates every 3-5 seconds
- **Recommendation Engine** - Combines AI analysis with rankings
- **Pre-computation Engine** - Starts analysis 3 picks before your turn

### `/data/` - Data Storage & Caching
Stores cached API responses and draft state.

**Files Created**:
- `players_cache.json` - Full NFL player database (11,388 players)
- `rankings_cache.json` - FantasyPros rankings (future)
- `draft_state.json` - Current draft state (future)

### `/tests/` - Unit Tests
Will contain pytest unit tests for all components (Day 2+ implementation).

---

## 🔄 Data Flow Architecture

```
1. Draft Monitoring Loop (every 3-5 seconds):
   Sleeper API → Draft Picks → Available Players → Cache Update

2. Recommendation Generation (when 3 picks away):
   Available Players → AI Agents → Rankings Data → Recommendations

3. User Interaction:
   CLI Commands → Sleeper Client → Formatted Display
```

---

## 🚀 Development Timeline & Progress

### ✅ Day 1 (Aug 5) - COMPLETED
**Goal**: Basic setup and Sleeper API connection

**Completed Actions**:
1. **Project Structure Created** - All directories and base files
2. **Dependencies Installed** - Python packages via pip
3. **Sleeper API Client Built** - Complete async client with caching
4. **Environment Setup** - `.env` file with your actual league credentials
5. **SSL Issues Resolved** - Fixed macOS certificate verification problems
6. **Connection Tested** - Successfully connected to your actual league
7. **CLI Interface Working** - Commands for testing, league info, available players

**Key Discoveries**:
- Your league: "Founding Father Keeper League" (12 teams)
- League type: Half PPR, SUPERFLEX (QBs rank 2-4!)
- Draft ID: 1221322229137031168
- Draft status: pre_draft (not started yet)
- Current picks: 16 made (likely keeper selections)
- Player database: 11,388 NFL players cached locally

### 🔄 Next Steps (Day 2+)
1. **Draft Monitoring** - Real-time pick tracking
2. **Rankings Integration** - FantasyPros via MCP
3. **AI Agent Setup** - CrewAI multi-agent system
4. **Claude Integration** - Natural language analysis
5. **Pre-computation** - Analysis before your turn
6. **Performance Optimization** - <2 second response times

---

## 🛠️ Technical Implementation Details

### Async Programming Pattern
All API calls use Python's `asyncio` for non-blocking operations:
```python
async with SleeperClient() as client:
    league = await client.get_league_info()
    players = await client.get_available_players(draft_id, position="QB")
```

### Caching Strategy
- **Player Data**: Cached for 24 hours (rarely changes during season)
- **Draft Picks**: Real-time (checked every 3-5 seconds)
- **Rankings**: 1-hour cache (updates throughout draft day)

### Error Handling Philosophy
- **Graceful Degradation**: Always provide something useful even if APIs fail
- **Comprehensive Logging**: All errors logged for debugging
- **Fallback Data**: Cached rankings as backup during API outages

### SUPERFLEX Awareness
Throughout the codebase, special handling for SUPERFLEX leagues:
- QB rankings are weighted higher
- Position scarcity calculations account for 2 QB slots
- Strategy recommendations emphasize early QB drafting

---

## 🔧 Key Commands for Daily Use

### Testing & Setup
```bash
python3 main.py test          # Test all API connections
python3 main.py league        # Show your league details
```

### Draft Day Commands
```bash
python3 main.py available               # All available players
python3 main.py available -p QB -l 10   # Top 10 QBs (SUPERFLEX!)
python3 main.py available -p RB -l 15   # Top 15 RBs
python3 main.py available -p WR -l 20   # Top 20 WRs
```

### Future Commands (Coming Soon)
```bash
python3 main.py monitor       # Start draft monitoring
python3 main.py recommend     # Get AI recommendations
python3 main.py compare       # Compare players
```

---

## 📈 Performance Targets

- **API Response Time**: <500ms for Sleeper calls
- **Recommendation Generation**: <2 seconds when your turn arrives
- **Draft Monitoring**: 3-5 second polling interval
- **Memory Usage**: <500MB for full player database
- **Cache Hit Rate**: >90% for repeated player lookups

---

## 🚨 Critical Success Factors

1. **August 14th Deadline** - Must be functional for actual draft
2. **SUPERFLEX Awareness** - QB values are dramatically different
3. **Real-time Performance** - 90-second pick window is unforgiving
4. **Reliability** - Cannot fail during live draft
5. **Usability** - Must be simple enough to use under pressure

---

## 🔮 Future Enhancements (Post-MVP)

1. **Yahoo Integration** - OAuth and live draft monitoring
2. **Web Interface** - Browser-based UI for easier interaction
3. **Voice Notifications** - Audio alerts for your turn
4. **Historical Analysis** - Pattern matching from past seasons
5. **Trade Analyzer** - AI-powered trade recommendations
6. **Mobile Support** - Draft from your phone

---

This overview will be updated daily as we progress through the development timeline.