# Project Organization - FantasyAgent

## Date: August 19, 2025

## Root Folder Cleanup Performed

### Files Relocated
- **Logs** → `/logs/`
  - dev_fixed.log
  - dev_server.log  
  - dev_updated.log
  - server_debug.log
  - server_output.log
  - server.log
  - simple_server.log
  - unified_server.log
  - web_app.log

- **Documentation** → `/docs/`
  - YAHOO_DRAFT_CONTINUATION.md
  - YAHOO_DRAFT_INSTRUCTIONS.md
  - action_log.md
  - issue_log.md

- **Tests** → `/tests/`
  - test_draft_data.py

- **Archive** → `/archive/`
  - old_servers/dev_server.py
  - yahoo_responses/
    - league_status.xml
    - yahoo_draft_response.xml
    - yahoo_response_1246753.xml

### Files Kept in Root (Appropriate)
- **CLAUDE.md** - Assistant instructions
- **README.md** - Project documentation
- **PROJECT_STRUCTURE.md** - Architecture overview
- **unified_server.py** - Main active server
- **main.py** - Entry point
- **requirements.txt** - Dependencies
- **Dockerfile** - Container config

## Current Project Structure

```
FantasyAgent/
├── platforms/          # Platform-specific implementations
│   ├── sleeper/       # Proven CrewAI system
│   └── yahoo/         # LangGraph experiments
├── core/              # Shared core functionality
├── docs/              # All documentation
├── logs/              # All log files
├── data/              # Cached rankings and state
├── config/            # OAuth and API configs
├── archive/           # Old/deprecated code
├── tests/             # Test suites
├── templates/         # UI templates
└── private/           # Sensitive tokens

## Key Active Files
- **unified_server.py** - Main server supporting all platforms
- **templates/unified.html** - Unified UI for all leagues
- **core/draft_monitor.py** - Real-time draft tracking
- **core/yahoo_token_manager.py** - OAuth auto-refresh

## Phase Status
- Phase 1: ✅ Sleeper Snake (Complete, successful draft)
- Phase 2: ⚠️ Yahoo Snake (Partial - API works, agent needs improvement)  
- Phase 3: 🔜 Sleeper Auction (Next priority)

## Lessons Learned
1. Keep platform implementations isolated
2. CrewAI simpler than LangGraph for complex flows
3. Cache aggressively for rate-limited APIs
4. Test with mock drafts before production
5. Document API quirks immediately