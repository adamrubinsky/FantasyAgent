# FantasyAgent Project Audit - August 22, 2025

## Executive Summary
Comprehensive audit of the FantasyAgent project to identify active components, deprecated code, and files for archival before GitHub publication.

## 🟢 ACTIVE & ESSENTIAL (Keep in main project)

### Core Server & UI
- `unified_server.py` - Main production server (Phase 3 active)
- `templates/unified.html` - Active unified UI for all platforms
- `main.py` - Application entry point

### Active Agent Systems

#### Sleeper Platform
- `platforms/sleeper/agents/sleeper_auction_crew_fast.py` - **PRIMARY** auction agent (<3s response)
- `platforms/sleeper/agents/draft_crew.py` - **PRIMARY** snake draft agent (production tested)
- `platforms/sleeper/api/sleeper_client.py` - Active API client

#### Yahoo Platform  
- `platforms/yahoo/agents/yahoo_snake_agent.py` - Ready for testing
- `platforms/yahoo/agents/yahoo_auction_agent.py` - Ready for testing
- `platforms/yahoo/api/yahoo_client.py` - Active API client
- `platforms/yahoo/api/yahoo_oauth_handler.py` - OAuth handling

### Core Functionality
- `core/draft_monitor.py` - Real-time draft monitoring
- `core/sleeper_player_cache.py` - Player ID caching (NEW - Phase 3)
- `core/rankings_manager.py` - Rankings management
- `core/official_fantasypros.py` - FantasyPros integration
- `core/league_context.py` - League settings management

### Essential Documentation
- `README.md` - Main project documentation
- `docs/PHASE_3_SUMMARY.md` - Current phase documentation
- `docs/ACTION_LOG.md` - Active development log
- `docs/ISSUE_LOG.md` - Active issue tracking
- `docs/STARTUP_GUIDE.md` - How to run the system
- `CLAUDE.md` - AI assistant instructions (important!)

### Configuration
- `requirements.txt` - Python dependencies
- `config/` - OAuth and API configurations

## 🟡 ARCHIVE (Move to archive/ folder)

### Old Server Versions
- `archive/old_servers/` - Already archived ✅
  - basic_server.py, dev_server.py, flask_dev_server.py, etc.

### Old Agent Versions
- `platforms/sleeper/agents/draft_crew_optimized.py` - Superseded by draft_crew.py
- `platforms/sleeper/agents/sleeper_auction_agent.py` - Superseded by sleeper_auction_crew_fast.py
- `platforms/sleeper/agents/sleeper_auction_crew.py` - Superseded by sleeper_auction_crew_fast.py
- `platforms/sleeper/agents/optimize_draft_crew.py` - One-time optimization script
- `platforms/sleeper/agents/draft_strategy_optimizer.py` - Development tool

### Duplicate Templates
- `platforms/sleeper/templates/` - Using unified.html instead
- `templates/dev.html` - Development version, superseded
- `templates/index.html` - Old version, superseded

### Old Yahoo Attempts
- `archive/yahoo_oauth_attempts/` - Already archived ✅
- `archive/old_yahoo/` - Already archived ✅

### Development/Test Files
- `tests/stress_test_recommendations.py` - One-time stress test
- `tests/test_real_performance.py` - Performance testing
- `tests/test_results.json` - Test output file

### Outdated Documentation
- `docs/PHASE_2_SUMMARY.md` - Completed phase
- `docs/MEMORY_PHASE2_YAHOO.md` - Phase 2 specific
- `docs/YAHOO_DRAFT_INSTRUCTIONS.md` - Draft completed
- `docs/YAHOO_DRAFT_CONTINUATION.md` - Draft completed
- `docs/archive/` - Already archived docs ✅

## 🔴 DELETE (Remove completely)

### Test Files in Root
- ~~`test_auction_integration.py`~~ - Already deleted ✅
- ~~`test_optimized_auction.py`~~ - Already deleted ✅

### Generated Cache Files
- `data/*.json` (except league_contexts.json) - Regenerated on demand
- `logs/*.log` - Old log files
- `__pycache__/` directories - Python cache
- `.pyc` files - Python bytecode

### Redundant Directories
- `auth/` - Empty directory
- `aws_config/` - Empty directory
- `iam-setup/` - Duplicate of infrastructure/iam
- `static/mock-backend.js` - Not used with real backend

### Bedrock/AWS AgentCore
- `bedrock-agentcore/` - Entire directory (not using AWS deployment)
- `deployment/agentcore/` - AWS AgentCore deployment (not using)
- `deployment/lambda/` - Lambda deployment (not using)
- `infrastructure/` - AWS infrastructure (not using)

## 🔵 NEEDS REVIEW

### MCP Servers
- `mcp_servers/` vs `platforms/shared/mcp_servers/` - Determine which is active
- `external/fantasypros-mcp-server/` - Node.js MCP server, check if needed

### Data Files
- `data/player_id_mapping.json` - May be needed for player mapping
- `data/league_contexts.json` - Active league configurations
- Review which rankings JSON files are actually used

### Platform Organization
- `platforms/shared/` - Appears to duplicate `core/` directory
  - Recommend consolidating to single location

## 📋 RECOMMENDED ACTIONS

### 1. Immediate Cleanup
```bash
# Remove empty directories
rm -rf auth/ aws_config/ iam-setup/

# Remove Bedrock/AWS directories (not using)
rm -rf bedrock-agentcore/ deployment/ infrastructure/

# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Clean logs
rm logs/*.log
```

### 2. Archive Old Agents
```bash
# Create archive directory for old agents
mkdir -p archive/old_agents/sleeper/

# Move old Sleeper agents
mv platforms/sleeper/agents/draft_crew_optimized.py archive/old_agents/sleeper/
mv platforms/sleeper/agents/sleeper_auction_agent.py archive/old_agents/sleeper/
mv platforms/sleeper/agents/sleeper_auction_crew.py archive/old_agents/sleeper/
mv platforms/sleeper/agents/optimize_draft_crew.py archive/old_agents/sleeper/
mv platforms/sleeper/agents/draft_strategy_optimizer.py archive/old_agents/sleeper/
```

### 3. Archive Old Documentation
```bash
# Move completed phase docs
mv docs/PHASE_2_SUMMARY.md docs/archive/
mv docs/MEMORY_PHASE2_YAHOO.md docs/archive/
mv docs/YAHOO_DRAFT_INSTRUCTIONS.md docs/archive/
mv docs/YAHOO_DRAFT_CONTINUATION.md docs/archive/
```

### 4. Consolidate Duplicates
- Decide between `core/` and `platforms/shared/core/`
- Decide between `mcp_servers/` and `platforms/shared/mcp_servers/`
- Remove duplicate template directories

### 5. Final Structure for GitHub
```
FantasyAgent/
├── README.md
├── CLAUDE.md
├── requirements.txt
├── unified_server.py
├── main.py
├── core/              # Core functionality
├── platforms/         # Platform-specific code
│   ├── sleeper/
│   └── yahoo/
├── templates/         # UI templates (unified.html only)
├── config/           # Configuration files
├── docs/             # Active documentation
├── tests/            # Unit and integration tests
├── scripts/          # Utility scripts
└── archive/          # Historical code for reference
```

## 📊 Size Reduction Estimate
- **Current size: 987MB** (mainly bedrock-agentcore samples)
  - bedrock-agentcore/: 889MB (AWS samples - NOT NEEDED)
  - external/: 31MB (node_modules for MCP)
  - archive/: 1MB (already archived code)
  - Rest of project: ~66MB
- **After cleanup: ~20-25MB**
- **Reduction: ~97%** (removing 960MB+)

## ✅ Ready for GitHub Checklist
- [ ] Remove all API keys and secrets from code
- [ ] Clean up cache and log files
- [ ] Archive old code versions
- [ ] Remove AWS/Bedrock directories
- [ ] Consolidate duplicate directories
- [ ] Update README with current status
- [ ] Add .gitignore for cache/logs/secrets
- [ ] Verify all active agents work
- [ ] Document minimum Python version (3.8+)
- [ ] Include setup instructions