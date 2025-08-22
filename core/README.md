# Core System Components

Essential functionality that powers the draft assistant.

## 🔧 Key Modules

### `draft_monitor.py`
Real-time draft tracking for Sleeper leagues
- WebSocket monitoring of draft rooms
- Team detection and roster management
- Proactive analysis triggers

### `sleeper_player_cache.py`
Player ID resolution and caching
- Maps Sleeper player IDs to names
- 7-day cache with automatic refresh
- Handles 10,000+ NFL players

### `rankings_manager.py`
Rankings data management
- Integrates with FantasyPros API
- 30-minute cache for performance
- Supports PPR, Half-PPR, and Standard scoring

### `official_fantasypros.py`
MCP server integration
- Direct connection to FantasyPros data
- Handles authentication and rate limiting