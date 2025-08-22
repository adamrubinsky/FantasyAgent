# Yahoo Platform Integration

In-development support for Yahoo Fantasy Football.

## 🔄 Status

### Snake Draft
- **Framework complete** with LangGraph state machine
- **<3 second response time** achieved in testing
- **Full PPR adjustments** implemented
- Awaiting live draft testing

### Auction Draft
- Planned for future release
- Will use similar VBD methodology as Sleeper

## 📁 Structure

- `/agents/` - LangGraph agent implementations
- `/api/` - Yahoo OAuth and API client
- `/data_providers/` - Rankings and data management
- `/server/` - Request handlers (placeholder)
- `/templates/` - UI templates (placeholder)