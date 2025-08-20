# Yahoo Fantasy Agents

Optimized agents for Yahoo Fantasy Football drafts using LangGraph for <3s response times.

## Directory Structure

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

### League 2: Yahoo Snake Draft (Aug 19)
- **Scoring**: Full PPR (1 point per reception)
- **QB Scoring**: 6 PT passing TDs
- **Special**: Return yards scoring (25 yards/point)
- **Strategy**: WR-heavy, target pass-catching RBs
- **Key adjustments**:
  - WRs get 25% value boost
  - QBs get 15% boost (vs 4PT TD leagues)
  - Return specialists get 10% bonus

### League 3: Yahoo Auction (Aug 24)
- **Budget**: $200
- **Scoring**: Half PPR (0.5 points per reception)
- **QB Scoring**: 4 PT passing TDs
- **Special**: No kicker position
- **Strategy**: Stars & Scrubs
- **Key adjustments**:
  - QBs capped at $22 (4PT TD devaluation)
  - Pass-catching RBs get 5-10% premium
  - Elite players worth up to $80 (40% budget rule)

## Usage

### Snake Draft Agent (League 2)
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

### Auction Agent (League 3)
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

## Key Features

1. **LangGraph Parallel Execution**: <3s response times
2. **League-Specific Scoring**: Proper adjustments for PPR, QB scoring
3. **FantasyPros MCP Integration**: Live rankings data
4. **Advanced Auction Values**: VBD methodology with PAR calculations
5. **Return Specialist Tracking**: Bonus for players with return yards

## Testing

Run comprehensive tests:
```bash
# Test League 2 (Snake Draft)
python tests/test_snake_draft.py

# Test League 3 (Auction Values)
python tests/test_auction_values.py

# Integration tests
python tests/test_yahoo_agents.py
```

## Dependencies

- Python 3.8+ (LangGraph requires 3.8 minimum)
- LangGraph 0.6.5+
- langchain-anthropic
- yahoo-oauth (for Yahoo API)
- yfpy (Yahoo Fantasy Python library)

## Environment Variables

Required in `.env.local`:
```
ANTHROPIC_API_KEY=your-key
YAHOO_CLIENT_ID=your-yahoo-client-id
YAHOO_CLIENT_SECRET=your-yahoo-client-secret
YAHOO_LEAGUE_ID_SNAKE=475629
YAHOO_LEAGUE_ID_AUCTION=682492
FANTASYPROS_API_KEY=your-fp-key
```

## Performance

- **Target**: <3s response time
- **Achieved**: 1-2s for cached scenarios, 2-3s for fresh analysis
- **Optimization**: Parallel analysis, smart caching, minimal LLM calls