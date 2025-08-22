# Data Files

Rankings data and player mappings for the draft assistant.

## 📊 Files

### Player Mappings
- `unified_player_mapping.json` - 11,389 players mapped across platforms
- `sleeper_players.json` - Sleeper player database cache

### Rankings Data
- `fantasypros_rankings_NFL_ALL_PPR_300.json` - Full PPR top 300
- `fantasypros_rankings_NFL_ALL_HALF_300.json` - Half PPR top 300
- `fantasypros_rankings_NFL_ALL_HALF_500.json` - Half PPR top 500
- `fantasypros_rankings_NFL_OP_HALF_500.json` - SUPERFLEX rankings

## 🔄 Updates
Rankings are cached with 30-minute TTL and auto-refresh from FantasyPros API when available.