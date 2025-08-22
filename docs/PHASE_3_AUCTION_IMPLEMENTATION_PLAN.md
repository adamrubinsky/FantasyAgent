# Phase 3: Sleeper Auction Draft Agent Implementation Plan

**Date Created**: August 21, 2025  
**Target Draft**: August 24, 2025 (Sleeper Auction, League 3)  
**Implementation Date**: August 22, 2025

## Executive Summary

Build a CrewAI-based auction draft agent for Sleeper that provides real-time bid recommendations with <3 second response times. The system will analyze every player nomination, track all team budgets, and follow a Stars & Scrubs strategy for optimal roster construction.

## League 3 Specifications

- **Platform**: Sleeper (NOT Yahoo)
- **Format**: 12-team Auction Draft
- **Budget**: $200 per team
- **Scoring**: Half-PPR (0.5 points per reception)
- **QB Scoring**: 4 PT passing TDs (reduces QB value)
- **Roster**: 1 QB, 2 RB, 2 WR, 1 TE, 1 W/R/T Flex, 1 DEF, 5 Bench, 1 IR
- **NO KICKER POSITION**
- **Strategy**: Stars & Scrubs (70% budget on 3-4 elite players)

## Architecture Overview

### Core Agent System: `/platforms/sleeper/agents/sleeper_auction_crew.py`

Four specialized CrewAI agents working in concert:

1. **Budget Analyst** (claude-3-haiku)
   - Track spending patterns across all 12 teams
   - Calculate market inflation rate
   - Identify budget-constrained teams

2. **Value Calculator** (claude-3-haiku)
   - VBD (Value-Based Drafting) calculations
   - Half-PPR scoring adjustments
   - Position scarcity analysis

3. **Roster Analyzer** (claude-3-haiku)
   - Track roster needs for all teams
   - Identify positional leverage
   - Monitor roster construction progress

4. **Bid Strategist** (claude-3-5-sonnet)
   - Synthesize all analysis
   - Make final BID/PASS decision
   - Set specific bid amounts

### File Structure

```
/platforms/sleeper/agents/
├── sleeper_auction_crew.py      # Main CrewAI implementation (CREATED)
├── auction_value_calculator.py  # VBD calculations (TO CREATE)
└── auction_data_provider.py     # Sleeper API wrapper (TO CREATE)

/core/
├── draft_monitor.py             # Already handles Sleeper auction (EXISTING)
├── official_fantasypros.py     # Rankings provider (EXISTING)
└── auction_cache.py             # Caching layer (TO CREATE)

/templates/
└── unified.html                 # UI with auction widgets (EXISTING)

/unified_server.py               # Main server (UPDATED)
```

## Implementation Steps

### Step 1: Fix and Complete `sleeper_auction_crew.py`

**File**: `/platforms/sleeper/agents/sleeper_auction_crew.py`

Required fixes:
1. ✅ Import corrections (OfficialFantasyProsMCP not FantasyProsClient)
2. Add proper VBD value calculation
3. Implement market inflation tracking
4. Add async/await properly for all methods

Key methods to implement:
- `analyze_nomination()` - Main entry for player bid analysis
- `get_nomination_suggestion()` - Suggest players to nominate
- `analyze_draft_question()` - Handle general Q&A
- `get_proactive_analysis()` - Strategic insights

### Step 2: Create Auction Value Calculator

**File**: `/platforms/sleeper/agents/auction_value_calculator.py`

```python
class AuctionValueCalculator:
    def __init__(self, league_settings):
        self.budget = 200
        self.teams = 12
        self.roster_spots = 16
        self.scoring = "HALF_PPR"
    
    def calculate_vbd_values(self, rankings):
        """Calculate auction values using VBD methodology"""
        # Implementation details...
    
    def adjust_for_inflation(self, base_value, inflation_rate):
        """Adjust values based on market conditions"""
        # Implementation details...
    
    def get_position_scarcity(self, position, remaining_players):
        """Calculate scarcity multiplier for position"""
        # Implementation details...
```

### Step 3: Create Auction Data Provider

**File**: `/platforms/sleeper/agents/auction_data_provider.py`

```python
class SleeperAuctionDataProvider:
    def __init__(self):
        self.base_url = "https://api.sleeper.app/v1"
        self.player_cache = {}
    
    async def get_auction_status(self, draft_id):
        """Get current auction state from Sleeper"""
        # Implementation details...
    
    async def get_player_details(self, player_id):
        """Get player info with caching"""
        # Implementation details...
    
    def calculate_team_needs(self, rosters):
        """Analyze what each team needs"""
        # Implementation details...
```

### Step 4: Update Server Integration

**File**: `/unified_server.py`

Required updates:
1. ✅ Import SleeperAuctionCrew instead of SleeperAuctionAgent
2. ✅ Add `/api/auction-bid` endpoint for player analysis
3. ✅ Add `/api/proactive/{platform}` endpoint
4. Update WebSocket handler for real-time bid updates
5. Ensure draft_monitor properly polls Sleeper auction

### Step 5: Enhance Draft Monitor

**File**: `/core/draft_monitor.py`

Current implementation at line 585 (`_get_sleeper_auction_status`) needs:
1. Better player metadata fetching
2. Current nomination tracking (if available from API)
3. Accurate budget calculations
4. Position mapping for purchased players

### Step 6: Create Caching Layer

**File**: `/core/auction_cache.py`

```python
class AuctionCache:
    def __init__(self, ttl=30):
        self.rankings_cache = {}
        self.values_cache = {}
        self.ttl = ttl
    
    def get_cached_value(self, player_id):
        """Get cached auction value with TTL check"""
        # Implementation details...
    
    def update_market_values(self, recent_sales):
        """Update cache based on actual sales"""
        # Implementation details...
```

## UI Integration Points

### Widgets to Update (already in `unified.html`):

1. **Draft Status Widget** (lines 194-213)
   - Show current player up for bid
   - Display current bid amount
   - Show high bidder
   - YOUR remaining budget

2. **Your Roster Widget** (lines 215-243)
   - List purchased players with prices
   - Group by position
   - Show total spent/remaining

3. **Available Players Widget** (lines 322-376)
   - Top available by value
   - Click to get bid recommendation
   - Show projected values

4. **Proactive Analysis Widget** (lines 378-402)
   - Budget position vs league
   - Strategy phase (stars/value/scrubs)
   - Next nomination suggestion

## API Endpoints

### Required Endpoints (in `unified_server.py`):

1. **POST `/api/auction-bid`** ✅ (Created)
   - Input: `{player, current_bid, platform}`
   - Output: `{action: "BID/PASS", max_bid, reasoning}`

2. **GET `/api/proactive/sleeper-auction`** ✅ (Created)
   - Output: `{title, insights, next_action}`

3. **POST `/api/chat`** (Existing, needs update)
   - Handle auction-specific queries
   - Return formatted recommendations

4. **GET `/api/draft-status`** (Existing)
   - Properly parse auction data from Sleeper

## Testing Plan

### Step 1: Unit Tests
```bash
# Create test file: /tests/test_auction_crew.py
python3 tests/test_auction_crew.py
```

Test scenarios:
- Quick pass on overpriced players
- Bid on undervalued stars
- Nomination strategy changes
- Budget constraint handling

### Step 2: Integration Test
```bash
# Start server
python3 unified_server.py

# Connect to mock auction draft
# Draft ID: Use Sleeper mock auction
```

### Step 3: Performance Tests
- Measure response time for 50 consecutive nominations
- Ensure <3 second response for all
- Test with degraded network

## Performance Optimizations

1. **Two-Tier Decision Process**
   - Tier 1: Rule-based quick pass (<0.5s)
   - Tier 2: Full CrewAI analysis (1-3s)

2. **Parallel Agent Execution**
   - First 3 agents run simultaneously
   - Only Bid Strategist runs sequentially

3. **Smart Caching**
   - 30-second TTL for rankings
   - Update values based on actual sales
   - Pre-compute top 50 player values

4. **Minimal LLM Calls**
   - Use Haiku for speed (3 agents)
   - Sonnet only for final synthesis
   - Skip LLM for obvious passes

## Critical Success Factors

1. **Response Time**: MUST be <3 seconds per nomination
2. **Budget Accuracy**: Track all 12 teams within $1
3. **Strategy Adherence**: Follow Stars & Scrubs properly
4. **Position Awareness**: Know when positions are scarce
5. **Market Dynamics**: Detect and adapt to inflation

## Day 2 Implementation Checklist (August 22)

### Morning (2 hours)
- [ ] Fix all imports in sleeper_auction_crew.py
- [ ] Create auction_value_calculator.py with VBD logic
- [ ] Create auction_data_provider.py for Sleeper API
- [ ] Test basic import and initialization

### Afternoon (3 hours)
- [ ] Implement analyze_nomination() method fully
- [ ] Add get_nomination_suggestion() logic
- [ ] Create auction_cache.py for performance
- [ ] Integration test with unified_server.py

### Evening (2 hours)
- [ ] Connect to Sleeper mock auction draft
- [ ] Test all UI widgets update properly
- [ ] Measure response times
- [ ] Fix any performance issues

### Final Testing (1 hour)
- [ ] Full mock draft simulation
- [ ] Verify Stars & Scrubs strategy works
- [ ] Ensure <3 second responses
- [ ] Document any issues for Day 3

## Known Issues to Address

1. **Sleeper API Limitations**
   - May not provide current nomination in real-time
   - Solution: Poll frequently, cache aggressively

2. **Player Position Mapping**
   - Sleeper uses player_id, need position for roster
   - Solution: Build position lookup from FantasyPros

3. **Team Identification**
   - User provides team name, need to map to ID
   - Solution: Parse team name intelligently

4. **Market Inflation Calculation**
   - Need baseline values to compare
   - Solution: Use FantasyPros + VBD as baseline

## Success Metrics

- ✅ Agent responds in <3 seconds for all nominations
- ✅ Correctly identifies Stars vs Scrubs vs Value players
- ✅ Tracks budgets for all 12 teams accurately
- ✅ Provides clear BID/PASS with specific amounts
- ✅ UI widgets show real-time auction state
- ✅ Successfully tested with mock draft

## Files to Review Before Implementation

1. `/platforms/sleeper/agents/draft_crew.py` - Reference for CrewAI patterns
2. `/core/draft_monitor.py` (line 585+) - Sleeper auction data fetching
3. `/templates/unified.html` - UI widget structure
4. `/docs/ARCHITECTURE.md` - Overall system design

---

**Remember**: This is for SLEEPER auction, not Yahoo. The draft is August 24, so we have August 22-23 to implement and test. Focus on reliability over complexity - a working simple system beats a broken complex one.