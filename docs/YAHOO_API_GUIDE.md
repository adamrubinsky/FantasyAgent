# Yahoo Fantasy Sports API Guide

## Overview
This guide contains essential information for working with the Yahoo Fantasy Sports API, specifically for NFL fantasy football draft monitoring and management.

## Authentication
- **Type**: OAuth 2.0 (3-legged flow for user data)
- **Requirements**: Consumer key/secret from Yahoo Developer Network
- **Token Storage**: `private/yahoo_token.json`
- **Token Refresh**: Required when access token expires

## API Base URLs
```
Base: https://fantasysports.yahooapis.com/fantasy/v2/
```

## Key Resource Patterns

### Game Keys
- **Game Code**: `nfl` (consistent across seasons)
- **Game ID**: Season-specific (e.g., `449` for 2025)
- **Usage**: `nfl.l.{league_id}` or `449.l.{league_id}`

### League Resources
```
/fantasy/v2/league/nfl.l.{league_id}
/fantasy/v2/league/nfl.l.{league_id}/settings
/fantasy/v2/league/nfl.l.{league_id}/standings
/fantasy/v2/league/nfl.l.{league_id}/draftresults
/fantasy/v2/league/nfl.l.{league_id}/transactions
```

### Team Resources
```
/fantasy/v2/team/nfl.l.{league_id}.t.{team_id}
/fantasy/v2/team/nfl.l.{league_id}.t.{team_id}/roster
/fantasy/v2/team/nfl.l.{league_id}.t.{team_id}/draftresults
```

### Player Resources
```
/fantasy/v2/player/nfl.p.{player_id}
/fantasy/v2/player/{player_key}
/fantasy/v2/player/{player_key}/stats
```

## Draft-Specific Endpoints

### Draft Results
**Endpoint**: `/fantasy/v2/league/nfl.l.{league_id}/draftresults`

**Response Structure**:
```xml
<draft_result>
  <pick>11</pick>
  <round>1</round>
  <team_key>nfl.l.123456.t.1</team_key>
  <player_key>nfl.p.7254</player_key>
  <!-- Note: Player name NOT included, must fetch separately -->
</draft_result>
```

### Getting Player Names
Player names are NOT included in draft results. You must:
1. Extract player_key from draft results
2. Make separate API call to get player details:
   ```
   GET /fantasy/v2/player/{player_key}
   ```
3. Parse response for player name

**Player Response Structure**:
```xml
<player>
  <player_key>nfl.p.7254</player_key>
  <player_id>7254</player_id>
  <name>
    <full>Christian McCaffrey</full>
    <first>Christian</first>
    <last>McCaffrey</last>
  </name>
  <display_position>RB</display_position>
  <editorial_team_abbr>SF</editorial_team_abbr>
</player>
```

## XML Parsing Patterns

### Draft Results Patterns
```python
# Extract from draft_result blocks
picks_pattern = r'<draft_result>(.*?)</draft_result>'

# Within each draft_result:
pick_pattern = r'<pick>(\d+)</pick>'
round_pattern = r'<round>(\d+)</round>'
team_pattern = r'<team_key>.*\.t\.(\d+)</team_key>'
player_key_pattern = r'<player_key>(.*?)</player_key>'
```

### Player Name Patterns
```python
# Different name formats in responses
name_patterns = [
    r'<name>\s*<full>(.*?)</full>',      # Full name in nested tag
    r'<player_name>(.*?)</player_name>',  # Direct player_name tag
    r'<name>(.*?)</name>',                # Simple name tag
]

# Position and team
position_pattern = r'<display_position>(.*?)</display_position>'
team_pattern = r'<editorial_team_abbr>(.*?)</editorial_team_abbr>'
```

## Implementation Strategy for Draft Monitoring

### 1. Initial Connection
- Extract league_id from any Yahoo fantasy URL
- Store draft_slot for user identification

### 2. Fetching Draft Data
```python
# Step 1: Get draft results
draft_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/nfl.l.{league_id}/draftresults"

# Step 2: Parse player keys from results
player_keys = extract_player_keys(xml_response)

# Step 3: Batch fetch player details (if possible)
# Or fetch individually as needed
for player_key in player_keys:
    player_url = f"https://fantasysports.yahooapis.com/fantasy/v2/player/{player_key}"
    # Fetch and parse player name
```

### 3. Optimizations
- **Cache player names**: Once fetched, store player_key -> name mapping
- **Batch requests**: Use multi-resource requests when possible
- **Rate limiting**: Yahoo has undocumented rate limits, add delays if needed

## Common Issues & Solutions

### Issue: Empty Draft Results
**Cause**: Draft hasn't started or API returns incomplete data
**Solution**: Check league settings for draft date/time, use mock data for testing

### Issue: Player Names Missing
**Cause**: Draft results only contain player keys
**Solution**: Implement player detail fetching as described above

### Issue: OAuth Token Expiration
**Cause**: Access tokens expire after 1 hour
**Solution**: Implement token refresh using refresh_token

### Issue: XML Parsing Complexity
**Cause**: Nested XML with varying structures
**Solution**: Use multiple parsing patterns and fallbacks

## Testing URLs

### Mock Draft URL Examples
```
https://football.fantasysports.yahoo.com/draftclient/f1/1246753/8
https://football.fantasysports.yahoo.com/f1/123456/draft
```

### League URL Patterns
```
Standard: https://football.fantasysports.yahoo.com/f1/{league_id}
Team: https://football.fantasysports.yahoo.com/f1/{league_id}/{team_id}
Draft Results: https://football.fantasysports.yahoo.com/f1/{league_id}/draftresults
```

## Rate Limits
- Undocumented but observed: ~1-2 requests per second sustained
- Implement exponential backoff on 429 errors
- Cache frequently accessed data (30-minute TTL recommended)

## Next Steps for Implementation

1. **Immediate**: Implement player key to name resolution
2. **Priority**: Cache player mappings to reduce API calls
3. **Enhancement**: Batch player fetching if multiple keys needed
4. **Testing**: Use mock draft data until live draft (August 19)

## Resources
- [Yahoo Developer Network](https://developer.yahoo.com/fantasysports/guide/)
- [Yahoo Fantasy API Documentation](https://yahoofantasysportsapidocs.readthedocs.io/)
- OAuth Setup: `yahoo_agents/oauth/yahoo_oauth.py`
- Token Storage: `private/yahoo_token.json`