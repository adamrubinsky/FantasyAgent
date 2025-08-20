# FantasyAgent Project Structure

## 📁 Directory Organization - Phase 2 Day 4 (August 18, 2025)

```
FantasyAgent/
├── 🚀 Core Entry Points
│   ├── unified_server.py       # Main unified server for both platforms
│   ├── dev_server.py           # Development server for testing
│   └── main.py                 # CLI entry point
│
├── 📂 platforms/               # Platform-specific implementations
│   ├── sleeper/                # Sleeper platform (PRODUCTION)
│   │   ├── agents/             # CrewAI agents (DO NOT MODIFY)
│   │   │   ├── draft_crew.py           # Main 4-agent draft system (111KB)
│   │   │   ├── draft_crew_optimized.py # Optimized version
│   │   │   └── draft_strategy_optimizer.py
│   │   ├── api/                # Sleeper API clients
│   │   ├── server/             # Platform-specific server code
│   │   └── templates/          # UI templates
│   │
│   ├── yahoo/                  # Yahoo platform (IN DEVELOPMENT)
│   │   ├── agents/             # LangGraph agents (<3s response target)
│   │   │   ├── yahoo_snake_agent.py    # Snake draft agent
│   │   │   ├── yahoo_auction_agent.py  # Auction draft agent
│   │   │   └── draft_graph.py          # Graph structure
│   │   ├── api/                # Yahoo API clients
│   │   ├── server/             # Platform-specific server code
│   │   └── templates/          # UI templates
│   │
│   └── shared/                 # Shared utilities between platforms
│
├── 📂 core/                    # Core shared functionality
│   ├── official_fantasypros.py         # FantasyPros MCP integration
│   ├── rankings_manager.py             # Rankings management with caching
│   ├── player_data_enricher.py         # Player data enrichment
│   ├── draft_monitor.py                # Real-time draft monitoring
│   ├── league_context.py               # League settings management
│   ├── mcp_integration.py              # MCP client integration
│   ├── ai_assistant.py                 # AI assistant base class
│   ├── manual_draft_tracker.py         # Manual draft tracking
│   └── pre_computation.py              # Pre-computed data optimization
│
├── 📂 api/                     # Legacy API clients (being migrated)
│   └── sleeper_client.py      # Original Sleeper client
│
├── 📂 config/                  # Configuration files
│   ├── yahoo/                 # Yahoo OAuth and config
│   │   ├── yahoo_oauth_final.py
│   │   ├── yahoo_exchange_code.py
│   │   ├── yahoo_get_new_oauth.py
│   │   └── yahoo_use_existing_code.py
│   └── settings.json          # General settings
│
├── 📂 tests/                   # All test files
│   ├── yahoo/                 # Yahoo-specific tests
│   │   ├── test_yahoo_api.py
│   │   ├── test_yahoo_integration.py
│   │   ├── test_yahoo_queries.py
│   │   ├── test_yahoo_verified.py
│   │   ├── simulate_yahoo_draft.py
│   │   ├── debug_yahoo_response.py
│   │   └── check_current_draft.py
│   ├── test_live_system.py            # Comprehensive system tests
│   ├── test_ai.py                     # AI agent tests
│   ├── test_rankings.py               # Rankings tests
│   ├── test_quick_data.py             # Data loading tests
│   ├── test_server.py                 # Server tests
│   ├── test_performance_optimization.py
│   ├── test_real_performance.py
│   └── stress_test_recommendations.py # Stress testing
│
├── 📂 data/                    # Data files and mappings
│   ├── unified_player_mapping.json    # 11,389 player ID mappings
│   ├── fantasypros_rankings/          # Cached rankings (30-min TTL)
│   ├── sleeper_data/                  # Cached Sleeper data
│   └── mock_players.json              # Mock data for testing
│
├── 📂 templates/               # UI templates
│   └── index.html             # Main unified UI template
│
├── 📂 static/                 # Static assets
│   └── (CSS, JS files)
│
├── 📂 docs/                   # Documentation
│   ├── API.md                 # API documentation
│   ├── ARCHITECTURE.md        # System architecture
│   ├── DEPLOYMENT_PLAN.md     # Deployment strategy
│   └── setup.md               # Setup instructions
│
├── 📂 mcp_servers/            # MCP server implementations
│   └── fantasypros/           # FantasyPros MCP server
│
├── 📂 archive/                # Archived old code
│   ├── old_agents/            # Old agents folder (original CrewAI)
│   │   └── agents/            # Moved from root
│   ├── old_yahoo/             # Old yahoo_agents folder
│   │   └── yahoo_agents/      # Moved from root
│   └── old_servers/           # Old server implementations
│       ├── web_app.py         # Old Flask web app
│       └── server.py          # Old server implementation
│
├── 📂 private/                # Private credentials (gitignored)
│   └── yahoo_token.json      # Yahoo OAuth token
│
├── 📂 logs/                   # Application logs
│   └── draft_logs/            # Draft-specific logs
│
├── 📂 deployment/             # Deployment configurations
│   ├── lambda/                # Lambda functions
│   └── scripts/               # Deployment scripts
│
├── 📂 infrastructure/         # AWS infrastructure
│   ├── iam/                  # IAM roles and policies
│   └── policies/              # Policy definitions
│
├── 📄 .env.local              # Local environment variables
├── 📄 .env.example            # Environment template
├── 📄 requirements.txt        # Python dependencies
├── 📄 action_log.md           # Development action log
├── 📄 CLAUDE.md               # Claude AI instructions
└── 📄 README.md               # Project readme
```

## 🏗️ System Architecture

### Multi-Platform Support
```
┌─────────────────────────────────────────────────────┐
│                  unified_server.py                   │
│                  (Main Entry Point)                  │
└────────────────┬───────────────┬────────────────────┘
                 │               │
        ┌────────▼──────┐ ┌─────▼──────┐
        │    Sleeper    │ │   Yahoo    │
        │   Platform    │ │  Platform  │
        └───────────────┘ └────────────┘
                 │               │
        ┌────────▼──────┐ ┌─────▼──────┐
        │   CrewAI      │ │ LangGraph  │
        │   Agents      │ │  Agents    │
        │  (15s resp)   │ │ (<3s resp) │
        └───────────────┘ └────────────┘
```

### Data Flow Architecture
```
User Request → Platform Router → Agent System → Data Providers → Response
                                       ↓
                               MCP Integration
                                       ↓
                              FantasyPros API
```

## 🔑 Key Components

### 1. Unified Server (`unified_server.py`)
- Single entry point for both platforms
- Platform detection and routing
- WebSocket support for real-time updates
- Handles both Sleeper and Yahoo drafts

### 2. Platform-Specific Agents

#### Sleeper (Production Ready ✅)
- **Location**: `platforms/sleeper/agents/draft_crew.py`
- **Framework**: CrewAI with 4 specialized agents
- **Response Time**: 15 seconds
- **Status**: Production tested, successful live draft

#### Yahoo (In Development 🔄)
- **Location**: `platforms/yahoo/agents/`
- **Framework**: LangGraph for speed
- **Response Time**: <3 seconds target
- **Status**: Ready for testing

### 3. Core Systems
- **MCP Integration**: FantasyPros data via MCP protocol
- **Player Mapping**: 11,389 unified player IDs across platforms
- **Caching**: 30-minute TTL for rankings data
- **Real-time Monitoring**: Draft state tracking

## 📊 Current Status (Phase 2 Day 4)

### ✅ Completed
- Reorganized file structure for clarity
- Fixed all import paths to use `platforms/` structure
- Archived old/unused code
- Sleeper platform fully working
- Unified player ID mapping system
- UI data integration from APIs

### 🔄 In Progress
- Yahoo live data pulling from mock drafts
- Agent performance optimization
- Unified UI testing with both platforms

### 🎯 Next Steps
1. Verify Yahoo agents are using correct code
2. Fix Yahoo mock draft data integration
3. Test <3s response times for Yahoo
4. Complete integration testing

## 🚀 Quick Start

### Development Server
```bash
# Start unified server (recommended)
python3 unified_server.py

# Or use development server
python3 dev_server.py
```

### Running Tests
```bash
# Test Sleeper system
python3 tests/test_live_system.py

# Test Yahoo snake draft
python3 platforms/yahoo/agents/tests/test_snake_draft.py

# Test Yahoo auction
python3 platforms/yahoo/agents/tests/test_auction_values.py
```

## 📅 Upcoming Drafts
- **August 19**: Yahoo Snake Draft (League 2, Full PPR)
- **August 24**: Yahoo Auction Draft (League 3, Half PPR)

## ⚠️ Important Notes
- **DO NOT MODIFY** `platforms/sleeper/agents/` - production system
- Keep Sleeper and Yahoo systems isolated
- Yahoo requires <3s response for 90-second draft clock
- All new development uses `platforms/` structure
- Use `unified_server.py` for testing both platforms