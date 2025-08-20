# Yahoo Fantasy Agents Documentation

## Overview
The Yahoo Fantasy agents provide AI-powered draft assistance for Yahoo Fantasy Football leagues using LangGraph for optimized performance (<3s response times). The system supports both Snake and Auction draft formats with league-specific scoring adjustments.

## Architecture

### Technology Stack
- **Framework**: LangGraph (chosen over CrewAI for 2-3x speed improvement)
- **LLM**: Claude (Haiku for speed, Sonnet for synthesis)
- **Data Source**: FantasyPros MCP Server
- **Performance**: 1-2s (cached), 2-3s (fresh analysis)

### Directory Structure
```
yahoo_agents/
├── agents/                 # Draft agents
│   ├── yahoo_snake_agent.py      # League 2: Full PPR Snake Draft
│   ├── yahoo_auction_agent.py    # League 3: Half PPR Auction Draft
│   └── draft_graph.py            # Base LangGraph implementation
│
├── clients/               # API clients
│   └── yahoo_client.py          # Yahoo Fantasy API client (OAuth)
│
├── data_providers/        # Data and calculations
│   ├── fantasypros_mcp_client.py   # FantasyPros MCP integration
│   ├── fantasypros_integration.py  # Direct FantasyPros API (backup)
│   └── auction_values.py           # VBD auction value calculator
│
├── tests/                 # Test suites
│   ├── test_snake_draft.py        # League 2 draft scenarios
│   ├── test_auction_values.py     # League 3 auction values
│   └── test_yahoo_agents.py       # Integration tests
│
└── utils/                 # Utilities (future)
```

## League Configurations

### League 2: Yahoo Snake Draft (August 19, 2024)
**Format**: Snake Draft  
**Scoring**: Full PPR (1 point per reception)  
**Special Rules**:
- 6 PT passing TDs (QBs more valuable)
- Return yards scoring (25 yards/point, 6 PT return TDs)
- Bonus points: 300+ passing, 90+ rushing, 100+ receiving

**Strategy Adjustments**:
- WRs get 25% value boost (Full PPR premium)
- QBs get 15% boost (6PT TDs vs standard 4PT)
- Return specialists get 10% bonus (Tyreek Hill, Deebo Samuel, etc.)
- Pass-catching RBs prioritized over pure rushers

**Roster Requirements**:
- 1 QB, 2 RB, 2 WR, 1 TE, 1 W/R Flex, 1 K, 1 DEF, 7 Bench

### League 3: Sleeper Auction Draft (August 24, 2024)
**Format**: Auction Draft  
**Budget**: $200  
**Scoring**: Half PPR (0.5 points per reception)  
**Special Rules**:
- 4 PT passing TDs (QBs less valuable)
- NO KICKER position
- Stars & Scrubs strategy recommended

**Strategy Adjustments**:
- QBs capped at $22 (4PT TD devaluation)
- Pass-catching RBs get 5-10% premium
- Elite players worth up to $80 (40% budget rule)
- Budget phases: STARS ($140), VALUE ($50), SCRUBS ($10)

**Roster Requirements**:
- 1 QB, 2 RB, 2 WR, 1 TE, 1 W/R/T Flex, 1 DEF, 5 Bench, 1 IR

## Agent Implementation Details

### Snake Draft Agent (League 2)

#### Key Components
1. **Quick Position Check**: Rule-based instant recommendations for obvious needs
2. **Parallel PPR Analysis**: Concurrent evaluation of:
   - WR value in Full PPR
   - RB pass-catching ability
   - Return specialist bonuses
   - Position scarcity

3. **Synthesis Engine**: Combines analyses for final recommendations

#### Usage Example
```python
from yahoo_agents.agents import YahooSnakeDraftAgent

agent = YahooSnakeDraftAgent()
context = {
    "round": 3,
    "pick_number": 29,
    "user_roster": {"QB": [], "RB": ["CMC"], "WR": ["Hill"]},
    "available_players": [...]  # From Yahoo API or MCP
}

result = await agent.get_recommendation(context)
# Returns top 3 recommendations with Full PPR adjustments
```

### Auction Draft Agent (League 3)

#### Key Components
1. **Budget Constraints Check**: Determines strategy phase (STARS/VALUE/SCRUBS)
2. **Parallel Market Analysis**:
   - Market inflation detection
   - Position run tracking
   - Opponent budget monitoring
   - Value target identification

3. **Bid Decision Engine**: Real-time bidding recommendations
4. **Nomination Strategy**: Suggests players to nominate based on phase

#### Usage Example
```python
from yahoo_agents.agents import YahooAuctionAgent

agent = YahooAuctionAgent()
context = {
    "remaining_budget": 145,
    "player_up": {"name": "Justin Jefferson", "position": "WR", "rank": 3},
    "current_bid": 48,
    "user_roster": {"RB": ["Jonathan Taylor"]},
    "slots_remaining": 14
}

result = await agent.get_bid_recommendation(context)
# Returns bid decision with max value
```

## Data Integration

### FantasyPros MCP Integration
The agents use the FantasyPros MCP server for:
- Live expert consensus rankings
- Player projections
- Scoring format adjustments (PPR/Half/Standard)

**Note**: MCP does not provide auction values, so we built a custom calculator.

### Auction Value Calculator (VBD Methodology)
The custom auction value calculator implements:
- **Value-Based Drafting (VBD)**: Calculates player value above replacement
- **Points Above Replacement (PAR)**: Projected points minus replacement level
- **Dollar Conversion**: Normalizes PAR to $200 budget across 12 teams
- **Position Adjustments**: Accounts for roster requirements and scarcity

## Performance Optimization

### LangGraph Advantages
- **Parallel Execution**: Multiple analyses run concurrently
- **Smart Routing**: Skip unnecessary steps for simple decisions
- **Model Selection**: Haiku for speed, Sonnet only for final synthesis
- **Caching**: 30-minute cache for rankings data

### Response Time Targets
- **Simple picks**: 50ms (rule-based)
- **Cached analysis**: 1-2 seconds
- **Fresh analysis**: 2-3 seconds
- **Never exceeds**: 3 seconds (90-second draft clock safe)

## Testing

### Test Coverage
- **Snake Draft**: 7 scenarios across different rounds
- **Auction Values**: 40 scenarios with various budgets/players
- **Integration**: End-to-end agent testing

### Running Tests
```bash
# Test League 2 (Snake Draft)
python3 yahoo_agents/tests/test_snake_draft.py

# Test League 3 (Auction Values)
python3 yahoo_agents/tests/test_auction_values.py

# Integration tests
python3 yahoo_agents/tests/test_yahoo_agents.py
```

## Deployment Considerations

### Environment Variables
Required in `.env.local`:
```
ANTHROPIC_API_KEY=your-key
YAHOO_CLIENT_ID=your-yahoo-client-id
YAHOO_CLIENT_SECRET=your-yahoo-client-secret
YAHOO_LEAGUE_ID_SNAKE=your-snake-league-id
YAHOO_LEAGUE_ID_AUCTION=your-auction-league-id
FANTASYPROS_API_KEY=your-fp-key
```

### Python Requirements
- Python 3.8+ (LangGraph minimum requirement)
- Key dependencies:
  - langgraph>=0.6.5
  - langchain-anthropic
  - yahoo-oauth
  - yfpy

## Future Enhancements

### Planned Features
- [ ] Streaming response support for real-time updates
- [ ] Live Yahoo draft monitoring via OAuth
- [ ] Mock draft testing integration
- [ ] Dynasty league support
- [ ] Keeper value calculations

### Potential Optimizations
- [ ] Edge caching for frequently accessed data
- [ ] WebSocket connections for instant updates
- [ ] Pre-computation 3 picks ahead
- [ ] Historical performance integration

## Troubleshooting

### Common Issues

1. **Import Warnings in VS Code**
   - Pylance may show warnings for langgraph imports
   - Code runs fine despite IDE warnings
   - Solution: Configure VS Code Python interpreter

2. **Python Version Errors**
   - LangGraph requires Python 3.8+
   - Use `python3` and `pip3` commands explicitly
   - Check version: `python3 --version`

3. **MCP Connection Issues**
   - Ensure FantasyPros MCP server is running
   - Check MCP configuration in Claude settings
   - Fallback to direct API if MCP unavailable

4. **Slow Response Times**
   - First call may be slower (cold start)
   - Ensure rankings cache is working
   - Check network connectivity to APIs

## Support

For issues or questions:
1. Check test files for usage examples
2. Review error logs in console output
3. Verify environment variables are set
4. Ensure all dependencies are installed

## Development Notes

### Key Design Decisions

1. **LangGraph over CrewAI**: Chosen for 2-3x speed improvement critical for draft scenarios
2. **Isolated Directory**: `/yahoo_agents/` kept separate to avoid interfering with working Sleeper system
3. **League-Specific Agents**: Separate implementations for different scoring formats
4. **VBD Calculator**: Built custom solution when MCP lacked auction values
5. **Parallel Analysis**: Leverages LangGraph's concurrent execution capabilities

### Lessons Learned
- Pre-computation and caching are essential for <3s response times
- League-specific adjustments significantly impact player valuations
- Auction strategies require different logic than snake drafts
- Return specialist bonuses can be tie-breakers in close rankings