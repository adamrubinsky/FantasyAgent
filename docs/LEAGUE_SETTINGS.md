# Fantasy Football League Settings - 2025 Season

## Overview
User has 3 fantasy football leagues with different platforms, scoring, and draft formats.

---

## League 1: Sleeper SUPERFLEX (PRIMARY)
**Draft Date**: August 14, 2025 (3 days away)  
**Platform**: Sleeper  
**Draft Type**: Snake Draft  
**League ID**: 1221322229137031168  
**Team**: Roster Slot 5  

### Roster Positions
- QB × 1
- RB × 2  
- WR × 3
- TE × 1
- FLEX × 2 (RB/WR/TE)
- SUPERFLEX × 1 (QB/RB/WR/TE)
- K × 1
- DST × 1
- Bench × 6

### Scoring
- **Format**: Half-PPR (0.5 points per reception)
- **Passing**: 0.04 per yard (25 yards = 1 point), 4 PT passing TD
- **Rushing**: 0.1 per yard (10 yards = 1 point), 6 PT rushing TD
- **Receiving**: 0.1 per yard, 0.5 PPR, 6 PT receiving TD
- **Special**: SUPERFLEX means QBs have extreme value

### Key Strategy
- **Must have 2 QBs by Round 4**
- Top 4 QBs (Allen/Hurts/Lamar/Mahomes) are first round picks
- Never draft K/DST before Round 15
- 3 keepers allowed (late-round value targets)

---

## League 2: Yahoo Snake Draft (FULL PPR)
**Draft Date**: August 19, 2025 (8 days away)  
**Platform**: Yahoo Fantasy  
**Draft Type**: Snake Draft  
**League URL**: https://football.fantasysports.yahoo.com/f1/475629/5  
**League ID**: 475629  
**Team ID**: 5  

### Roster Positions
- QB × 1
- RB × 2
- WR × 2
- TE × 1
- W/R Flex × 1
- K × 1
- DEF × 1
- Bench × 7

### Scoring (FULL PPR)
- **Format**: FULL PPR (1 point per reception)
- **Passing**: 25 yards/point, 6 PT passing TDs, -2 INT
- **Rushing**: 10 yards/point, 6 PT rushing TDs
- **Receiving**: 10 yards/point, 1 PPR, 6 PT receiving TDs
- **Bonuses**: 
  - Passing: +3 at 300y, +2 at 350y, +1 at 400y
  - Rushing: +3 at 90y, +2 at 130y, +1 at 170y
  - Receiving: +3 at 100y, +2 at 140y, +1 at 180y
- **Return Scoring**: 25 yards/point, 6 PT return TDs
- **Kickers**: 3 pts (0-39y), 4 pts (40-49y), 5 pts (50+)
- **Defense**: Standard with points allowed scoring

### Key Strategy
- WR-heavy due to FULL PPR
- QB less valuable (only 1 starter, no SUPERFLEX)
- Target pass-catching RBs
- Return specialists have added value

---

## League 3: Yahoo Auction (HALF PPR)
**Draft Date**: August 24, 2025 (13 days away)  
**Platform**: Yahoo Fantasy  
**Draft Type**: AUCTION ($200 budget)  
**League URL**: https://football.fantasysports.yahoo.com/f1/682492/2  
**League ID**: 682492  
**Team ID**: 2  

### Roster Positions
- QB × 1
- WR × 2
- RB × 2
- TE × 1
- W/R/T Flex × 1
- DEF × 1
- Bench × 5
- IR × 1
- **NO KICKER**

### Scoring (HALF PPR)
- **Format**: Half-PPR (0.5 points per reception)
- **Passing**: 25 yards/point, 4 PT passing TDs, -2 INT
- **Rushing**: 10 yards/point, 6 PT rushing TDs
- **Receiving**: 10 yards/point, 0.5 PPR, 6 PT receiving TDs
- **Bonuses**:
  - Passing: +2 at 300y, +1 at 400y
  - Rushing: +1 at 100y, +2 at 150y, +2 at 200y
  - Receiving: +1 at 125y, +1 at 150y, +2 at 200y
- **Defense**: Standard + 0.5 for tackles for loss
- **No Kicker Position**

### Auction Strategy
- **Budget**: $200 total
- **Stars & Scrubs**: Spend 70-80% on 3-4 studs
- **Max per player**: ~$70 (35% of budget)
- **Save $10-15** for end-game bidding wars
- **Nominate expensive players** you don't want early
- **Track other teams' budgets** carefully

---

## Key Differences Between Leagues

### QB Value Ranking
1. **Sleeper SUPERFLEX**: QBs are EXTREME value (2-3 needed)
2. **Yahoo Snake (PPR)**: QBs moderate value (6 PT passing TD helps)
3. **Yahoo Auction (Half-PPR)**: QBs lowest value (4 PT passing TD)

### WR vs RB Priority
1. **Yahoo Snake**: WR priority (FULL PPR)
2. **Sleeper/Yahoo Auction**: Balanced (Half-PPR)

### Unique Considerations
- **Sleeper**: SUPERFLEX spot changes everything
- **Yahoo Snake**: Return yards scoring (target return specialists)
- **Yahoo Auction**: No kicker, extra flex spot

---

## Draft Priority Order
1. **August 14**: Sleeper SUPERFLEX (current system ready)
2. **August 19**: Yahoo Snake (need to add Yahoo monitoring)
3. **August 24**: Yahoo Auction (need auction-specific logic)

---

## Technical Requirements

### For Yahoo Integration
- ✅ OAuth App Created
- ✅ Client ID/Secret Stored
- ✅ League IDs Identified
- ⚠️ Need: OAuth token exchange
- ⚠️ Need: Draft monitoring endpoint
- ⚠️ Need: Different agent logic per league

### API Access Status
- **Sleeper**: ✅ Working (public API)
- **Yahoo**: ⚠️ OAuth configured, need token exchange
- **FantasyPros**: ✅ Working (API key active)

---

*Last Updated: August 11, 2025 (Day 7)*