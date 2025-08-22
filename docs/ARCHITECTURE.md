# FantasyAgent System Architecture

## Overview

FantasyAgent is a multi-platform fantasy football draft assistant that provides real-time AI-powered recommendations during live drafts. The system supports both Sleeper and Yahoo platforms with platform-specific optimizations.

## Core Architecture Principles

### 1. Platform Isolation
- Each platform (Sleeper/Yahoo) has its own isolated implementation
- No cross-dependencies between platforms
- Shared core utilities only for common functionality

### 2. Performance Targets
- **Sleeper**: 15-second response time (achieved)
- **Yahoo**: <3-second response time (target for 90-second draft clock)

### 3. AI Framework Selection
- **Sleeper**: CrewAI for comprehensive multi-agent analysis
- **Yahoo**: LangGraph for high-performance state machines

## System Components

### Entry Points

```
unified_server.py
├── Platform Detection
├── WebSocket Management
├── Request Routing
└── Response Handling
```

### Platform Architecture

#### Sleeper Platform
```
platforms/sleeper/
├── agents/
│   ├── draft_crew.py                    # Snake draft CrewAI 4-agent system
│   │   ├── Value Analyst
│   │   ├── Position Strategist
│   │   ├── Risk Assessor
│   │   └── Final Recommender
│   ├── sleeper_auction_crew_fast.py     # Auction draft (<4s response)
│   │   ├── Market Analyst (Haiku)
│   │   ├── Value Expert (Haiku)
│   │   ├── Roster Builder (Haiku)
│   │   └── Auction Strategist (Sonnet 4)
│   ├── auction_cache.py                 # 3-tier caching system
│   ├── auction_value_calculator.py      # VBD methodology
│   └── auction_data_provider.py         # Data sourcing hierarchy
├── api/
│   └── sleeper_client.py                # Real-time draft monitoring
└── templates/
    └── sleeper_ui.html                   # Platform-specific UI
```

#### Yahoo Platform
```
platforms/yahoo/
├── agents/
│   ├── yahoo_snake_agent.py  # Snake draft logic
│   ├── yahoo_auction_agent.py # Auction valuations
│   └── draft_graph.py         # LangGraph state machine
├── api/
│   └── yahoo_client.py        # OAuth & API integration
└── templates/
    └── yahoo_ui.html          # Platform-specific UI
```

### Core Systems

```
core/
├── official_fantasypros.py    # MCP server integration
├── rankings_manager.py        # 30-minute cache TTL
├── player_data_enricher.py    # Player metadata
├── draft_monitor.py           # Real-time state tracking
└── league_context.py          # League settings management
```

## Data Flow

### 1. Request Flow
```
User Input → WebSocket → unified_server.py → Platform Router
    ↓
Platform Handler → Agent System → Data Providers
    ↓
MCP Server → FantasyPros API → Cache Layer
    ↓
Agent Analysis → Response Generation → WebSocket → UI
```

### 2. Real-time Draft Monitoring (Sleeper)
```
Sleeper API ← 5-second polling ← draft_monitor.py
    ↓
Draft State Update → Agent Trigger → Proactive Analysis
    ↓
WebSocket Broadcast → UI Update
```

### 3. Caching Strategy
```
Request → Cache Check (30-min TTL)
    ↓ (miss)
FantasyPros API → Cache Store → Response
    ↓ (hit)
Cached Data → Response
```

## Agent Systems

### CrewAI (Sleeper)

```python
class FantasyDraftCrew:
    agents = [
        ValueAnalyst(),      # Identifies value picks
        PositionStrategist(), # Manages roster balance
        RiskAssessor(),      # Evaluates risks
        FinalRecommender()   # Synthesizes recommendations
    ]
    
    def analyze_draft_question(self, query, context):
        # Sequential agent processing
        # Each agent contributes specialized analysis
        # Final synthesis by recommender
        return recommendations
```

### LangGraph (Yahoo)

```python
class YahooSnakeAgent:
    graph = StateGraph()
    
    # Parallel execution for speed
    graph.add_parallel([
        "analyze_value",
        "check_position_needs",
        "evaluate_adp"
    ])
    
    # Conditional routing
    if simple_decision:
        return quick_response  # <1s
    else:
        return full_analysis   # <3s
```

## Performance Optimizations

### 1. Model Selection
- **Haiku**: Quick analysis, position checks (<1s)
- **Sonnet**: Final synthesis, complex comparisons (<3s)

### 2. Parallel Processing

#### LangGraph (Yahoo)
```python
# LangGraph parallel execution
from langchain.runnables import RunnableParallel

parallel_analysis = RunnableParallel({
    "value": value_chain,
    "position": position_chain,
    "adp": adp_chain
})
```

#### CrewAI (Sleeper Auction)
```python
# Parallel crews using kickoff_async()
results = await asyncio.gather(
    market_crew.kickoff_async(),
    value_crew.kickoff_async(),
    roster_crew.kickoff_async(),
    return_exceptions=True
)
```

### 3. Caching Layers
- **Rankings**: 30-minute TTL
- **Player Data**: Session-based
- **Draft State**: Real-time, no cache

#### Sleeper Auction 3-Tier System
- **L1 Cache** (0ms): Pre-computed obvious decisions
- **L2 Quick Rules** (0-3ms): Heuristics without LLM
- **L3 Full Analysis** (~4s): Parallel CrewAI agents

### 4. Proactive Analysis
- Triggered at 6, 3, and 0 picks ahead
- Pre-computed recommendations
- 5-second response at user's turn

## Data Management

### Unified Player Mapping
```json
{
  "player_id": "unified_12345",
  "sleeper_id": "4984",
  "fantasypros_id": "17298",
  "yahoo_id": "33456",
  "espn_id": "15847",
  "name": "Josh Allen",
  "position": "QB",
  "team": "BUF"
}
```
- 11,389 players mapped across platforms
- Resolves ID mismatches
- Enables cross-platform filtering

### League Context
```python
class LeagueContext:
    platform: str           # "sleeper" | "yahoo"
    scoring: str           # "PPR" | "HALF_PPR" | "STANDARD"
    roster_format: dict    # Position requirements
    draft_type: str        # "snake" | "auction"
    special_positions: list # ["SUPERFLEX", "OP"]
```

## WebSocket Communication

### Message Types
```javascript
// Client → Server
{
  "type": "draft_question",
  "platform": "sleeper",
  "query": "Who should I draft?",
  "context": {...}
}

// Server → Client
{
  "type": "recommendation",
  "players": [...],
  "reasoning": "...",
  "alternatives": [...]
}

// Server → Client (Proactive)
{
  "type": "proactive_alert",
  "picks_until_turn": 3,
  "recommendations": [...]
}
```

## Error Handling

### Timeout Strategy
```python
try:
    result = await asyncio.wait_for(
        agent.analyze(query),
        timeout=30.0  # Sleeper
    )
except asyncio.TimeoutError:
    return fallback_response()
```

### Fallback Mechanisms
1. Quick rule-based recommendations
2. Cached previous analysis
3. Simple ranking-based suggestions

## Security Considerations

### OAuth (Yahoo)
- Tokens stored in `private/yahoo_token.json`
- Auto-refresh before expiration
- Secure credential handling

### API Keys
- Environment variables only
- Never committed to repository
- `.env.local` for development

## Deployment Architecture

### Local Development
```
unified_server.py
├── FastAPI application
├── WebSocket server
├── Static file serving
└── Hot reload enabled
```

### Production (Future)
```
AWS Architecture:
├── API Gateway → Lambda
├── S3 → Static hosting
├── DynamoDB → State storage
├── CloudWatch → Monitoring
└── Bedrock → AgentCore
```

## Testing Strategy

### Unit Tests
- Agent logic validation
- API integration tests
- Cache behavior tests

### Integration Tests
```bash
tests/
├── test_live_system.py      # End-to-end Sleeper
├── yahoo/
│   ├── test_snake_draft.py  # Yahoo snake logic
│   └── test_auction.py      # Auction valuations
└── stress_test.py           # Performance testing
```

### Performance Benchmarks

#### Achieved Response Times
| Platform | Draft Type | Target | Achieved |
|----------|------------|--------|----------|
| Sleeper | Snake | 15s | 15s ✅ |
| Sleeper | Auction | <3s | 0-4s ✅ |
| Yahoo | Snake | <3s | <3s (testing) |

#### Sleeper Auction Optimization Results
- **Initial**: 22 seconds (sequential CrewAI)
- **Optimized**: <4 seconds (parallel async)
- **Cache hits**: 0ms response
- **Quick rules**: 0-3ms response

## Future Enhancements

### Phase 3
- Streaming responses for instant feedback
- Advanced caching with Redis
- Multi-draft concurrent support
- Historical pattern analysis

### Phase 4
- Voice notifications
- Mobile app integration
- Trade analyzer
- Season-long assistant

---

*Last Updated: Phase 3 Day 2 - August 22, 2025*