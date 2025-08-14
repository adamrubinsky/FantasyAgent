# Claude Assistant Instructions for FantasyAgent

## Project Overview
You are working on FantasyAgent, a comprehensive fantasy football draft assistant system that supports multiple platforms (Sleeper, Yahoo) with AI-powered recommendations. The project uses two different AI frameworks:
- **CrewAI** for Sleeper (production system, DO NOT MODIFY)
- **LangGraph** for Yahoo (new system with <3s response times)

## Critical Guidelines

### 1. System Isolation
- **NEVER** modify files in `/agents/` directory (working Sleeper/CrewAI system)
- **Yahoo agents** are completely isolated in `/yahoo_agents/` directory
- Keep these systems separate to avoid breaking production Sleeper functionality

### 2. Performance Requirements
- Yahoo agents MUST respond in <3 seconds
- Use LangGraph's parallel execution capabilities
- Cache frequently accessed data (30-minute TTL for rankings)
- Use Haiku for speed, Sonnet only for final synthesis

### 3. League-Specific Configurations

#### League 2 (Yahoo Snake - August 19)
- **Scoring**: Full PPR (1 point per reception)
- **QB Scoring**: 6 PT passing TDs (15% QB boost)
- **Special**: Return yards (25 yards/point)
- **Strategy**: Prioritize WRs (25% boost) and pass-catching RBs
- **Key players**: Return specialists get 10% bonus

#### League 3 (Yahoo Auction - August 24)
- **Budget**: $200
- **Scoring**: Half PPR (0.5 points per reception)
- **QB Scoring**: 4 PT passing TDs (cap QBs at $22)
- **Strategy**: Stars & Scrubs (70% on 3-4 elite players)
- **NO KICKER** position

### 4. Testing Requirements
When asked to test:
1. Run comprehensive test suites first
2. Test League 2: `python3 yahoo_agents/tests/test_snake_draft.py`
3. Test League 3: `python3 yahoo_agents/tests/test_auction_values.py`
4. Verify <3s response times
5. Check league-specific adjustments are applied

### 5. Data Sources
- **Primary**: FantasyPros MCP server (check if running)
- **Rankings**: Use `get_rankings` with appropriate scoring format
- **Auction Values**: Use custom VBD calculator (MCP doesn't provide)
- **Cache**: 30-minute TTL to reduce API calls

### 6. Python Environment
- **Required**: Python 3.8+ (LangGraph minimum)
- **Commands**: Always use `python3` and `pip3`
- **Virtual Env**: Avoid venv, use system Python or user installs
- **Installation**: Use `--user` flag for pip3 installs

### 7. File Organization
```
FantasyAgent/
├── agents/          # Sleeper CrewAI (DO NOT TOUCH)
├── yahoo_agents/    # Yahoo LangGraph agents
│   ├── agents/      # Draft agents
│   ├── clients/     # API clients
│   ├── data_providers/  # Data sources
│   └── tests/       # Test suites
```

### 8. Common Issues & Solutions

**Import Warnings**: VS Code Pylance warnings can be ignored if code runs
**Python Version**: Must be 3.8+, check with `python3 --version`
**MCP Issues**: Ensure FantasyPros MCP is configured in Claude settings
**Slow First Call**: Normal due to cold start, subsequent calls faster

### 9. Development Workflow
1. Always test changes with comprehensive test suites
2. Monitor response times (must be <3s)
3. Verify league-specific adjustments
4. Document any new features in `/docs/`
5. Keep Yahoo and Sleeper systems isolated

### 10. Upcoming Drafts
- **August 19**: League 2 (Yahoo Snake, Full PPR)
- **August 24**: League 3 (Yahoo Auction, Half PPR)
- Both require <3s response times for 90-second draft clock

## Key Technologies

### LangGraph Components
- **StateGraph**: Manages draft state and workflow
- **RunnableParallel**: Concurrent analysis execution
- **Conditional Routing**: Skip steps for simple decisions
- **Memory Saver**: Checkpoint system for state

### Performance Optimizations
- Parallel analysis of multiple factors
- Quick rule-based checks before LLM calls
- Smart model selection (Haiku vs Sonnet)
- Caching of rankings and calculated values

## Testing Checklist
- [ ] All tests pass
- [ ] Response time <3s
- [ ] League adjustments correct
- [ ] No interference with Sleeper system
- [ ] Rankings cache working
- [ ] Auction values calculating properly

## Important Notes
- Production Sleeper draft was successful (August 12)
- Yahoo agents ready but need live testing
- Streaming responses planned for future
- Mock draft testing pending ("another day" per user)