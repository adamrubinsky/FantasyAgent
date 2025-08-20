# Yahoo Agent Issues Log
**Phase 2 Day 5 - August 19, 2025**

## Issue #1: OAuth Token Expiry ✅ RESOLVED
**Time**: 6:00 PM
**Problem**: Yahoo OAuth tokens expire after exactly 1 hour
**Impact**: API calls fail with 401 errors
**Solution**: 
- Created `YahooTokenManager` with auto-refresh
- 5-minute buffer before expiry
- Integrated in `draft_monitor.py`
```python
from core.yahoo_token_manager import token_manager
access_token = token_manager.get_valid_token()
```
**Status**: FIXED - Auto-refresh working

---

## Issue #2: UI Widget Field Mismatches ⚠️ PARTIAL
**Time**: 6:15 PM
**Problem**: Widgets showing empty/incorrect data
**Impact**: Draft Status, Your Roster, Recent Picks not displaying
**Solution**:
- Added field transformations in `unified_server.py`
- Created `calculate_next_pick()` helper
- Mapped `roster` → `userRoster` for UI
**Status**: PARTIAL - Some widgets still not showing data

---

## Issue #3: Generic Fallback Responses ✅ RESOLVED
**Time**: 6:30 PM
**Problem**: Agent returning "Ja'Marr Chase" for all queries
**Impact**: Useless recommendations
**Root Cause**: Not using full rankings (only top 100)
**Solution**:
- Use all 500 players from FantasyPros
- Improved query parsing
- Return errors instead of generic fallbacks
**Status**: FIXED - Better responses now

---

## Issue #4: Player Comparison Failures ✅ RESOLVED
**Time**: 6:35 PM
**Problem**: "Ashton Jeanty or RJ Harvey?" returned generic response
**Impact**: Can't compare specific players
**Root Cause**: Rookies not in top 100 subset
**Solution**:
- Search all 500 rankings
- Better name matching algorithm
- Handle partial name matches
**Status**: FIXED - Comparisons working

---

## Issue #5: Yahoo API Rate Limiting (999) 🔴 ACTIVE
**Time**: 6:45 PM
**Problem**: Yahoo blocking IP with error 999
**Impact**: No draft data, can't fetch player names
**Root Cause**: Too many API calls (>720/hour)
**Solutions Implemented**:
1. 30-second cache for draft data
2. Reduced polling 5s → 30s
3. Batch player lookups (max 10)
4. Exponential backoff on fetches
5. FantasyPros fallback
**Status**: BLOCKED - Waiting for timeout (1-24 hours)

---

## Issue #6: Roster Type Mismatch ✅ RESOLVED
**Time**: 6:48 PM
**Problem**: "'list' object has no attribute 'get'"
**Impact**: Agent crashes when processing roster
**Root Cause**: Expected dict, got list
**Solution**: Handle both types in agent
**Status**: FIXED - Type handling added

---

## Issue #7: Draft Context Not Reaching Agent ⚠️ UNCLEAR
**Time**: 6:40 PM
**Problem**: Agent not using draft context (roster, pick #)
**Impact**: Generic advice instead of contextual
**Possible Causes**:
- Yahoo API blocked (no draft data)
- Context not passed correctly
- Agent not processing context
**Status**: UNCLEAR - May be due to API block

---

## Issue #8: Proactive Analysis Not Working ❌ NOT FIXED
**Time**: Throughout testing
**Problem**: Proactive widget shows wrong data
**Impact**: No automatic recommendations
**Status**: NOT FIXED - Low priority

---

## Performance Issues

### Response Times
- Target: <3 seconds
- Actual with cache: 1-2 seconds ✅
- Cold start: 3-4 seconds ⚠️
- With API block: 2-3 seconds ✅

### API Call Volume
- Before: ~720 calls/hour (BLOCKED)
- After: ~120 calls/hour (SAFE)
- Optimal: <100 calls/hour

---

## Lessons Learned

1. **Yahoo is aggressive about rate limiting**
   - No warning before 999 block
   - Blocks last 1-24 hours
   - Must cache aggressively

2. **FantasyPros is reliable fallback**
   - Always available
   - Good rankings data
   - Can work without Yahoo

3. **UI polling must be conservative**
   - 30 seconds minimum
   - Cache everything possible
   - Batch API calls

4. **Type safety matters**
   - Always check list vs dict
   - Handle both formats
   - Add type hints

5. **Query parsing is critical**
   - Users ask in many ways
   - Must detect intent
   - Specific > Generic

---

## Action Items for Next Time

1. **Before Draft**:
   - Start server 1 hour early
   - Test API access
   - Warm up caches
   - Verify token fresh

2. **During Draft**:
   - Monitor rate limits
   - Use 30+ second polling
   - Have FantasyPros ready
   - Track manually if needed

3. **Code Improvements**:
   - Add retry logic
   - Better error messages
   - More caching layers
   - Smarter batching