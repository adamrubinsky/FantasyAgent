# FantasyAgent Issue Log

## Resolved Issues

### Issue #1: Team Detection Hardcoded to Slot 7
**Status**: RESOLVED
**Date**: 2025-08-22
**Symptoms**: 
- User in Team 2 slot seeing Team 7 data
- Roster and budget information incorrect

**Root Cause**: 
- Team detection logic hardcoded to slot 7 in draft_monitor.py

**Resolution**:
- Updated logic to prioritize direct slot number input
- Falls back to username matching, then "Team X" parsing
- Updated UI to clarify slot number input accepted

### Issue #2: Import Error for AuctionDataProvider
**Status**: RESOLVED
**Date**: 2025-08-22
**Symptoms**:
- Proactive analysis showing fallback message
- "cannot import name 'AuctionDataProvider'" error in logs

**Root Cause**:
- Class was actually named SleeperAuctionDataProvider

**Resolution**:
- Fixed import statement in draft_monitor.py line 848

### Issue #3: Inflated Max Bid Calculations
**Status**: RESOLVED
**Date**: 2025-08-22
**Symptoms**:
- Max bid $185 for player with $200 budget
- Values not considering actual player rankings

**Root Cause**:
- Formula: budget - roster_spots_left + 1
- Using arbitrary caps instead of real values

**Resolution**:
- Integrated real auction values from rankings
- Added budget-aware adjustments
- Position-specific value caps

### Issue #4: Event Loop Already Running
**Status**: RESOLVED
**Date**: 2025-08-22
**Symptoms**:
- "This event loop is already running" error
- Async functions failing to execute

**Root Cause**:
- Using run_until_complete in already async context

**Resolution**:
- Changed to await for async calls
- Proper async/await chain maintained

### Issue #5: All Players Showing $1 Market Value
**Status**: RESOLVED
**Date**: 2025-08-22
**Symptoms**:
- Every player valued at $1
- VBD calculation returning 0

**Root Cause**:
- FantasyPros rankings had rank=999 for all players
- VBD calculation failing without valid ranks

**Resolution**:
- Use index position as rank when rank=999
- Added rank-based fallback values
- Tiered value system based on player rank

### Issue #6: $0 Max Bid for All Players
**Status**: RESOLVED
**Date**: 2025-08-22
**Symptoms**:
- "Max Bid: $0" for all nominated players
- Market values showing correctly but max bid broken

**Root Cause**:
- auction_values dict not properly initialized
- Fallback logic not triggering

**Resolution**:
- Proper initialization of auction_values dict
- Rank-based fallback when VBD fails
- Position-adjusted default values

### Issue #7: Slow Proactive Analysis Updates
**Status**: RESOLVED
**Date**: 2025-08-22
**Symptoms**:
- Analysis not updating in time for auction bids
- 10-second delay too slow for 30-second nomination timer

**Root Cause**:
- Fixed 10-second polling interval for all draft types

**Resolution**:
- Dynamic polling: 3 seconds for auction, 10 for snake
- Platform-specific configuration in unified.html

### Issue #8: Proactive Analysis 15+ Second Update Lag
**Status**: RESOLVED
**Date**: 2025-08-24
**Symptoms**:
- Nominations showing same player for 15+ seconds after they were sold
- Updates taking much longer than expected 2-3 seconds

**Root Cause**:
- Sleeper API's `nominated_player_id` doesn't update immediately after sale
- API has inherent 5-8 second delay from live draft window

**Resolution**:
- Implemented stale nomination detection (checks if player in picks)
- Added pick count tracking to detect sales
- Shows "Waiting for next nomination..." when between players
- Fixed frontend polling to actually use 2-second intervals
- Remaining 5-8 second delay is Sleeper's API lag (cannot be optimized)

## Known Issues

### Issue #9: Sleeper Auction Values Not From API
**Status**: WORKAROUND IN PLACE
**Notes**: 
- Sleeper has auction values visible in draft window
- Not found in API responses yet
- Using pre-calculated VBD values for all 580 players
- Instant lookups from data/pre_calculated_auction_values.json

### Issue #10: Name Matching Inconsistencies
**Status**: MONITORING
**Notes**:
- Some players with Jr/Sr/III suffixes may not match
- Normalization logic in place but may need refinement
- No user complaints yet but potential issue