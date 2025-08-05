# External Dependencies

This directory contains external MCP servers and third-party integrations.

## FantasyPros MCP Server

**Location**: `fantasypros-mcp-server/`
**Source**: https://github.com/DynamicEndpoints/fantasy-pros-mcp  
**Purpose**: Official FantasyPros API integration for live rankings data

### Setup Instructions:

1. **Get FantasyPros API Key**:
   - Email FantasyPros directly for API access
   - Professional sports data requires paid/approved access

2. **Configure Environment**:
   ```bash
   cd external/fantasypros-mcp-server/
   echo "FANTASYPROS_API_KEY=your_api_key_here" > .env
   ```

3. **Install & Build**:
   ```bash
   npm install
   npm run build
   ```

4. **Test Connection**:
   ```bash
   npm run inspector
   ```

### Available Tools:
- `get_rankings(sport, position, scoring)` - NFL rankings with STD/PPR/HALF scoring
- `get_players(sport, playerId)` - Player information
- `get_projections(sport, season, week, position)` - Weekly projections  
- `get_sport_news(sport, limit, category)` - Injury/transaction news

### Integration Status:
- ✅ **Downloaded and built**
- ⏳ **Waiting for API key** (user emailed FantasyPros)
- 🎯 **Ready for integration** once key received