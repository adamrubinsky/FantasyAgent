# Fantasy Football Draft Assistant - Project Structure

## 📁 Root Directory Layout

```
FantasyAgent/
├── 📋 Core Application Files
│   ├── main.py                    # CLI entry point
│   ├── requirements.txt           # Python dependencies
│   └── .env(.example|.local)      # Environment configuration
│
├── 🤖 Agent System
│   └── agents/
│       └── draft_crew.py          # CrewAI multi-agent implementation
│
├── 🔌 API Integrations  
│   └── api/
│       ├── sleeper_client.py      # Sleeper Fantasy API
│       └── fantasypros_client.py  # Legacy FantasyPros client
│
├── 🧠 Core Logic
│   └── core/
│       ├── ai_assistant.py        # AI analysis engine
│       ├── draft_monitor.py       # Real-time draft tracking
│       ├── league_context.py      # League settings management
│       ├── mcp_integration.py     # MCP client wrapper
│       └── rankings_manager.py    # Data aggregation logic
│
├── 🛠 Utilities (NEW - Day 4)
│   └── utils/
│       └── player_mapping.py      # Cross-platform player ID resolution
│
├── 📜 Scripts (NEW - Day 4)
│   └── scripts/
│       └── create_player_mapping.py # Generate unified player mapping
│
├── 🔗 MCP Servers
│   └── mcp_servers/
│       └── fantasypros_mcp.py     # Custom MCP server (fallback)
│
├── 💾 Data Storage
│   └── data/
│       ├── players_cache.json     # Cached player database
│       ├── draft_state.json       # Current draft state
│       └── league_contexts.json   # Saved league settings
│
├── 🔧 Utilities & Scripts
│   └── scripts/
│       ├── check_picks.py         # Draft pick verification
│       └── generate_rankings.py   # Ranking generation utility
│
├── 🧪 Testing
│   └── tests/
│       ├── test_ai.py            # AI system tests
│       └── test_caching.py       # Cache system tests
│
├── 📖 Documentation
│   ├── docs/
│   │   ├── architecture/         # System architecture diagrams
│   │   └── planning/            # Project planning documents
│   ├── ACTION_LOG.md            # Development progress log
│   ├── OVERVIEW.md              # Project overview
│   ├── SETUP.md                 # Setup instructions
│   └── README.md                # Main project README
│
├── 🔌 External Dependencies
│   └── external/
│       └── fantasypros-mcp-server/  # Official FantasyPros MCP server
│
└── 📝 Examples & Demos
    └── examples/
        ├── ai_examples.md       # AI query examples
        └── league_comparison.py # League analysis examples
```

## 🎯 Key Components

### **Multi-Agent System**
- **CrewAI Framework**: 4 specialized agents (Data Collector, Analyst, Strategist, Advisor)
- **Live Data Integration**: MCP protocol for real-time FantasyPros data
- **Context Awareness**: League settings and draft state tracking

### **Data Sources**
- **Primary**: Official FantasyPros MCP server (requires API key)
- **Fallback**: Custom web scraping with comprehensive mock data
- **Draft Data**: Sleeper API for real-time pick monitoring

### **Deployment Architecture**
- **Development**: Local Python + Node.js MCP servers
- **Production**: AWS Bedrock AgentCore integration
- **Caching**: 3-tier strategy (cached → live → mock)

## 🚀 Quick Start

1. **Python Setup**:
   ```bash
   pip install -r requirements.txt
   cp .env.example .env  # Add your API keys
   ```

2. **MCP Server Setup**:
   ```bash
   cd external/fantasypros-mcp-server/
   npm install && npm run build
   ```

3. **Test System**:
   ```bash
   python main.py test
   python tests/test_caching.py
   ```

4. **Run Draft Assistant**:
   ```bash
   python main.py ask "Should I draft Josh Allen?"
   python main.py monitor  # Live draft monitoring
   ```

## 📊 Data Flow

```
Draft Question → CrewAI Agents → MCP Client → FantasyPros API → Analysis → Recommendation
                     ↓              ↓            ↓
                League Context  Live Rankings  Sleeper Draft Data
```

This structure supports both rapid development and professional deployment while maintaining clean separation of concerns.