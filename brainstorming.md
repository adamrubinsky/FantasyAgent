# Fantasy Football Draft Assistant - Project Brainstorming & Context

## Project Overview

Building an AI-powered fantasy football draft assistant that provides real-time recommendations during live drafts. The system needs to work within the critical 90-second pick window and integrate with multiple fantasy platforms.

**Critical Constraint**: First draft is on Sleeper platform on August 14th, 2025 (approximately 2 weeks from project start on August 5th).

**Important League Setting**: League uses SUPERFLEX rosters (QB values are much higher!)

## Key Requirements

### Business Requirements
1. **Real-time draft monitoring** - Know who's been picked instantly
2. **Intelligent recommendations** - AI-powered suggestions within 90 seconds
3. **Multi-platform support** - Yahoo Fantasy and Sleeper (Sleeper first for MVP)
4. **Historical context** - Use past performance data for better recommendations
5. **Pre-computation** - Start analyzing when 3 picks away from user's turn
6. **Live rankings** - Pull current rankings from FantasyPros (superflex) and Sleeper

### Technical Requirements
- **Response time**: <2 seconds for recommendations when pick arrives
- **Draft duration**: Support 8-hour draft sessions
- **Reliability**: 99.9% uptime during draft windows
- **Platforms**: Yahoo (OAuth required) and Sleeper (public API)
- **Rankings**: Real-time from FantasyPros (must handle superflex)

## Architecture Decisions

### Technology Stack
- **Infrastructure**: AWS Bedrock AgentCore (deploy after local development)
- **Agent Framework**: CrewAI initially (simple), potentially LangGraph later (complex workflows)
- **LLM**: Claude via Anthropic API (user has Claude Max account)
- **Language**: Python 3.10+
- **Database**: OpenSearch for vector embeddings (post-MVP)
- **Development**: VS Code with Claude Code integration

### Development Strategy
1. **Local Development First** (Aug 5-12)
   - Build and test everything locally
   - Rapid iteration without deployment overhead
   - Full debugging capabilities

2. **Structure for AgentCore** (Aug 12-13)
   - Refactor code to AgentCore patterns
   - Still run locally but with proper architecture

3. **Deploy to Production** (After Aug 14 draft)
   - Deploy working system to AgentCore
   - Add monitoring and scaling

## Platform Integration Details

### Sleeper API (Start Here - No Auth!)
- **Base URL**: `https://api.sleeper.app/v1`
- **No authentication required** (public API)
- **Key Endpoints**:
  - `/user/{username}` - Get user info
  - `/user/{user_id}/leagues/nfl/2025` - Get leagues
  - `/league/{league_id}/rosters` - Get all rosters
  - `/players/nfl` - Get all players (5MB payload, cache this!)
  - `/draft/{draft_id}/picks` - Get draft picks

### Yahoo Fantasy API (Phase 2)
- **Requires OAuth 2.0** authentication
- **Must register app** at Yahoo Developer Network
- **Key Capabilities**:
  - Real-time draft monitoring
  - Pick submission
  - Full league/roster data

### FantasyPros Integration (Critical for Rankings)
- **Available via MCP (Model Context Protocol) server**
- **No web scraping needed!**
- **Must support superflex rankings** 
- **Update rankings on draft day**
- Pull latest consensus rankings
- Filter by scoring format (PPR/Half/Standard)
- **Superflex** dramatically changes QB values!

## Agent Architecture

### CrewAI Implementation (MVP)
```python
# Four specialized agents working together:
1. Data Collector Agent - Fetches live draft/player data + rankings
2. Analysis Agent - Evaluates players based on stats/projections  
3. Strategy Agent - Considers league settings and roster construction
4. Recommendation Agent - Synthesizes final pick suggestions
```

### Key Features by Priority

**Must Have (MVP)**:
- See who's been drafted
- Get available players by position
- **Pull live rankings from FantasyPros/Sleeper**
- Basic recommendations (top 5)
- Track user's roster
- 5-second response time
- **Superflex roster support**

**Should Have**:
- Pre-computation (3 picks early)
- Claude integration for analysis
- Player comparison tool
- ADP value indicators
- Tier break notifications
- **Enhanced player data**: ADP, bye weeks, playoff matchups (Weeks 14-16), projected fantasy points
- **Advanced table columns**: Strength of schedule, target share, red zone touches

**Nice to Have** (Post-MVP):
- Web UI
- Voice notifications
- Historical pattern matching
- Advanced analytics

## 9-Day Sprint Plan (Aug 5-14)

### Day 1 (Aug 5): Setup & Sleeper Connection
- Environment setup
- Basic project structure
- Get Sleeper API working
- Cache player data locally

### Day 2 (Aug 6): Draft Monitoring
- Poll draft every 5 seconds
- Track picks and available players
- Basic CLI interface

### Day 3 (Aug 7): Live Rankings Integration
- **Set up FantasyPros MCP server locally**
- **Use MCP tools to pull superflex rankings**
- **Test get_rankings() and get_projections() tools**
- **Cache with 1-hour expiry**
- Merge rankings with Sleeper data
- Create unified ranking system

### Day 4 (Aug 8): Claude Integration
- Add AI analysis
- Natural language queries
- Player comparisons
- Superflex strategy logic

### Weekend (Aug 10-11): Integration & Testing
- Connect all components
- Run full mock drafts
- Performance optimization
- Add pre-computation

### Final Days (Aug 12-13): Polish & Prep
- Test with actual league
- **Refresh rankings on draft morning**
- Create backup plans
- Document commands

## Code Structure

```
fantasy-draft-assistant/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   └── draft_assistant.py  # CrewAI agent
├── api/
│   ├── __init__.py
│   ├── sleeper_client.py   # No auth needed!
│   ├── yahoo_client.py     # OAuth complexity
│   └── mcp_client.py       # For FantasyPros MCP
├── core/
│   ├── __init__.py
│   ├── draft_monitor.py    # Polls for updates
│   ├── recommender.py      # Pick logic
│   ├── rankings_manager.py # Merges multiple sources
│   └── ai_assistant.py     # Claude integration
├── data/
│   ├── players_cache.json  # 5MB from Sleeper
│   └── rankings_cache.json # Live rankings (1hr TTL)
├── tests/
│   └── test_sleeper.py
├── .env                    # API keys
├── requirements.txt
└── main.py                 # Entry point
```

## Critical Path to Success

### Minimum Viable Product for Aug 14
1. **Connect to Sleeper league** ✓
2. **Monitor draft in real-time** ✓  
3. **Show available players** ✓
4. **Pull live superflex rankings** ✓
5. **Give recommendations based on current rankings** ✓
6. **Track user's roster** ✓

Everything else is a bonus!

## Key Technical Patterns

### MCP Integration for FantasyPros
```python
# Using MCP is cleaner than web scraping:
1. Install/run FantasyPros MCP server locally
2. Connect via MCP client
3. Use built-in tools for rankings
4. Supports all scoring formats
5. Aligns with AgentCore architecture
```

### Rankings Management
```python
# Rankings should be:
1. Pulled fresh on draft day
2. Cached with TTL (1 hour)
3. Merged from multiple sources
4. SUPERFLEX-aware (QBs ranked higher!)
```

### Rate Limiting
```python
# Sleeper: 1000 requests per minute
# Yahoo: 60 requests per minute
# FantasyPros MCP: Check server limits
# Implement exponential backoff
```

### Pre-computation Strategy
```python
# When user is 3 picks away:
1. Fetch current available players
2. Update rankings if stale
3. Generate top 20 scenarios
4. Cache recommendations
5. Serve instantly when pick arrives
```

### Error Handling Philosophy
- Graceful degradation over failure
- Always have cached rankings as fallback
- Log everything for debugging

## Authentication & Secrets

### Required API Keys
```bash
ANTHROPIC_API_KEY=your-claude-api-key
YAHOO_CLIENT_ID=from-yahoo-developer
YAHOO_CLIENT_SECRET=from-yahoo-developer
```

### Sleeper Authentication
- None required! Public API
- Just need username and league_id

## Testing Strategy

### Mock Draft Checklist
- [ ] Full draft simulation with real timing
- [ ] Test with different draft positions
- [ ] Verify <2 second response times
- [ ] Test connection drops
- [ ] Verify recommendations make sense
- [ ] **Test superflex QB valuations**

## Deployment Notes (Post-MVP)

### AgentCore Considerations
- Supports any framework (CrewAI ✓)
- Free during preview (until Sept 16)
- Provides Memory, Identity, Gateway services
- 8-hour runtime support for long drafts

### Why Local First?
1. Faster iteration (seconds vs minutes)
2. Better debugging (full stack traces)
3. No deployment failures during development
4. Can always run locally as fallback

## Common Pitfalls to Avoid

1. **Don't overcomplicate** - Simple working > Complex broken
2. **Cache everything** - API calls are precious during draft
3. **Update rankings day-of** - Don't use stale rankings!
4. **Test with real data** - Use your actual league
5. **Have backups** - Export rankings, have manual fallback
6. **Remember superflex** - QBs are worth way more!

## Success Metrics

- Get recommendations in <2 seconds ✓
- Don't timeout on any pick ✓
- Rankings are current (not stale) ✓
- Draft better than last year ✓
- Learn for next iteration ✓

## Post-Draft Roadmap

1. **Week 1**: Add Yahoo OAuth
2. **Week 2**: Deploy to AgentCore
3. **Week 3**: Add vector DB for historical data
4. **Month 2**: Production features (web UI, etc.)

## Resources & Documentation

- [Sleeper API Docs](https://docs.sleeper.app/)
- [Yahoo Fantasy API](https://developer.yahoo.com/fantasysports/)
- [AWS Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)
- [CrewAI Documentation](https://docs.crewai.com/)
- [FantasyPros MCP Server](https://github.com/DynamicEndpoints/fantasy-pros-mcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- Python sleeper wrapper: `sleeper-api-wrapper`
- Python Yahoo wrapper: `yfpy`

## Emergency Fallback

If everything fails, this script with cached rankings still helps:
```python
# Load latest rankings and players
import json
with open('rankings_cache.json') as f:
    rankings = json.load(f)
with open('players.json') as f:
    players = json.load(f)
# Filter drafted, sort by current rankings, show top 5
```

## League-Specific Notes

- **Scoring Format**: [Confirm: PPR/Half/Standard?]
- **Roster Format**: SUPERFLEX (QB/RB/RB/WR/WR/TE/FLEX/SUPERFLEX)
- **This means**: QBs are MUCH more valuable
- **Draft strategy**: Consider QB early, maybe 2 in first 4 rounds

## Contact & Support

- Project GitHub: [your-repo-here]
- Draft Date: August 14, 2025
- Platform Priority: Sleeper first, Yahoo later
- League Type: SUPERFLEX (critical for rankings!)

---

*This document contains all context needed to build the fantasy football draft assistant. Start with the 9-day sprint plan and focus on MVP features for the August 14th draft. Remember: superflex changes everything about QB values!*