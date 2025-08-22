# Sleeper Platform Integration

Production-ready draft assistant for Sleeper fantasy football.

## ✅ Features

### Snake Draft Support
- **4-agent CrewAI system** for comprehensive analysis
- **15-second response time** with detailed recommendations
- **Proactive analysis** at 6, 3, and 0 picks ahead
- Successfully used in multiple live drafts

### Auction Draft Support
- **3-second updates** for fast-paced bidding
- **VBD-based valuations** with market price comparison
- **Budget-aware recommendations** based on roster needs
- **Max bid calculations** to prevent overspending

## 📁 Structure

- `/agents/` - AI agent implementations
  - `draft_crew.py` - Snake draft 4-agent system
  - `sleeper_auction_crew_fast.py` - Optimized auction agent
  - `auction_value_calculator.py` - VBD calculations
- `/api/` - Sleeper API client
- `/server/` - WebSocket and HTTP handlers
- `/templates/` - UI templates (deprecated)