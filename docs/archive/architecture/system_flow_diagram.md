# Fantasy Draft Assistant - System Architecture Flow

## 🏗️ High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FANTASY DRAFT ASSISTANT                           │
│                              Web Interface                                 │
│                           http://localhost:3000                           │
└─────────────────────┬───────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Backend                                  │
│                         (dev_server.py)                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │   API Routes    │  │  Session Mgmt   │  │      Real-time Polling      │ │
│  │ /api/ask        │  │   Context &     │  │    Draft Status Every      │ │
│  │ /api/draft-     │  │   User State    │  │        5 seconds            │ │
│  │     status      │  │                 │  │                             │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CREWAI MULTI-AGENT SYSTEM                           │
│                         (agents/draft_crew.py)                             │
│                                                                             │
│  ┌────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────┐│
│  │ Draft Monitor  │ │ Data Collector  │ │ Analysis Agent  │ │ Strategy    ││
│  │                │ │                 │ │                 │ │ Agent       ││
│  │ • Track picks  │ │ • Fetch live    │ │ • Player stats  │ │ • Position  ││
│  │ • User turn    │ │   data from     │ │ • Rankings      │ │   needs     ││
│  │ • Proactive    │ │   APIs          │ │ • Comparisons   │ │ • Roster    ││
│  │   triggers     │ │ • Available     │ │ • Value assess  │ │   balance   ││
│  │                │ │   players       │ │                 │ │ • Bye weeks ││
│  └────────┬───────┘ └─────┬───────────┘ └─────┬───────────┘ └─────┬───────┘│
│           │               │                   │                   │        │
│           └───────────────┼───────────────────┼───────────────────┘        │
│                           │                   │                            │
│                           ▼                   ▼                            │
│           ┌─────────────────────────────────────────────────────────────┐   │
│           │              RECOMMENDATION AGENT                          │   │
│           │                                                             │   │
│           │ • Synthesizes all analysis                                  │   │
│           │ • Applies position-based rules                              │   │
│           │ • Considers SUPERFLEX strategy                              │   │
│           │ • Avoids QB over-indexing                                   │   │
│           │ • Provides 3 ranked recommendations                        │   │
│           └─────────────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────────────────────┘
                      │
                      ▼
```

## 📊 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DATA SOURCES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────┐  │
│  │   Sleeper API    │    │  FantasyPros     │    │   Player Mapping     │  │
│  │                  │    │      API         │    │      System          │  │
│  │ • Draft picks    │    │ • SUPERFLEX      │    │ • 11,389 players     │  │
│  │ • Available      │    │   rankings       │    │ • Cross-platform     │  │
│  │   players        │    │ • Player stats   │    │   ID mapping         │  │
│  │ • User roster    │    │ • Projections    │    │ • Sleeper ↔          │  │
│  │ • League info    │    │ • ADP data       │    │   FantasyPros        │  │
│  │                  │    │                  │    │   matching           │  │
│  └──────┬───────────┘    └──────┬───────────┘    └──────┬───────────────┘  │
│         │                       │                       │                  │
└─────────┼───────────────────────┼───────────────────────┼──────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA PROCESSING LAYER                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    UNIFIED DATA AGGREGATION                          │  │
│  │                                                                      │  │
│  │  1. FETCH LIVE DRAFT DATA                                            │  │
│  │     ├─ Get current draft picks from Sleeper                         │  │
│  │     ├─ Identify user's roster using picked_by field                 │  │
│  │     └─ Calculate user's next pick and timing                        │  │
│  │                                                                      │  │
│  │  2. PROCESS AVAILABLE PLAYERS                                        │  │
│  │     ├─ Get all undrafted players                                     │  │
│  │     ├─ Cross-reference with FantasyPros rankings                    │  │
│  │     ├─ Apply unified player ID mapping                               │  │
│  │     └─ Filter out drafted players using robust matching             │  │
│  │                                                                      │  │
│  │  3. ANALYZE ROSTER COMPOSITION                                       │  │
│  │     ├─ Count positions: QB, RB, WR, TE                              │  │
│  │     ├─ Analyze bye week distribution                                 │  │
│  │     ├─ Identify position priorities/avoid list                      │  │
│  │     └─ Generate strategic guidance for AI                           │  │
│  │                                                                      │  │
│  │  4. CONTEXTUALIZE FOR AI AGENTS                                     │  │
│  │     ├─ Format draft context with user roster                        │  │
│  │     ├─ Include position priorities and avoid rules                  │  │
│  │     ├─ Add bye week considerations                                   │  │
│  │     └─ Prepare available player rankings                            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI RECOMMENDATION ENGINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      ENHANCED LOGIC RULES                           │  │
│  │                                                                      │  │
│  │  📋 POSITION-BASED DECISION MATRIX:                                 │  │
│  │     ┌─ QB Count = 0: "QB (critical for SUPERFLEX)"                  │  │
│  │     ├─ QB Count = 1: "2nd QB (important for SUPERFLEX)"             │  │
│  │     ├─ QB Count = 2: "3rd QB (optional depth)"                      │  │
│  │     └─ QB Count ≥ 3: "AVOID: QB (focus other positions)"            │  │
│  │                                                                      │  │
│  │  🏃 RB PRIORITY LOGIC:                                               │  │
│  │     ├─ RB Count < 2: "RB (need starters - high priority)"           │  │
│  │     ├─ RB Count < 4: "RB (depth/handcuffs - medium priority)"       │  │
│  │     └─ RB Count < 6: "RB (additional depth)"                        │  │
│  │                                                                      │  │
│  │  🎯 WR PRIORITY LOGIC:                                               │  │
│  │     ├─ WR Count < 3: "WR (need starters - high priority)"           │  │
│  │     ├─ WR Count < 5: "WR (depth - medium priority)"                 │  │
│  │     └─ WR Count < 7: "WR (additional depth)"                        │  │
│  │                                                                      │  │
│  │  📅 BYE WEEK ANALYSIS:                                               │  │
│  │     ├─ Identify weeks with 3+ players                               │  │
│  │     ├─ Flag problematic bye week stacking                           │  │
│  │     └─ Recommend avoiding same-bye players                          │  │
│  │                                                                      │  │
│  │  🏆 SUPERFLEX BALANCE:                                               │  │
│  │     ├─ Use FantasyPros SUPERFLEX rankings (not Sleeper)             │  │
│  │     ├─ Balance QB value with positional needs                       │  │
│  │     └─ Don't over-index on QBs when sufficient depth exists         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    AI AGENT EXECUTION FLOW                          │  │
│  │                                                                      │  │
│  │  Step 1: DATA COLLECTOR                                             │  │
│  │     └─ Compiles all context and available players                   │  │
│  │                                                                      │  │
│  │  Step 2: ANALYSIS AGENT                                             │  │
│  │     └─ Evaluates player values, stats, and rankings                 │  │
│  │                                                                      │  │
│  │  Step 3: STRATEGY AGENT                                             │  │
│  │     └─ Applies position logic and roster construction rules         │  │
│  │                                                                      │  │
│  │  Step 4: RECOMMENDATION AGENT                                       │  │
│  │     ├─ Synthesizes analysis with position priorities                │  │
│  │     ├─ Applies avoid/prioritize rules from Position Summary         │  │
│  │     ├─ Considers bye week distribution                              │  │
│  │     ├─ Formats 3 ranked recommendations with reasoning              │  │
│  │     └─ Provides backup options and strategic context               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            OUTPUT FORMAT                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🥇 **Primary Pick**: Player Name (Position) - Reasoning                   │
│     • Why this player fits current roster needs                            │
│     • FantasyPros ranking and value assessment                             │
│     • Strategic fit for SUPERFLEX format                                   │
│                                                                             │
│  🥈 **Backup Option**: Player Name (Position) - Reasoning                  │
│     • Alternative if primary pick is drafted                               │
│     • Position priority and roster balance                                 │
│                                                                             │
│  🥉 **Third Choice**: Player Name (Position) - Reasoning                   │
│     • Additional fallback option                                           │
│     • Strategic considerations and value                                    │
│                                                                             │
│  📋 **Additional Context**:                                                │
│     • Current roster composition summary                                   │
│     • Position priorities for next few picks                               │
│     • Bye week considerations if relevant                                  │
│     • Trade value and season-long strategy notes                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Real-Time Operation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DRAFT MONITORING CYCLE                             │
│                            (Every 5 seconds)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. 📡 FETCH CURRENT DRAFT STATE                                           │
│     ├─ Query Sleeper API for latest picks                                  │
│     ├─ Check if new picks have been made                                   │
│     ├─ Update draft pick counter and available players                     │
│     └─ Calculate picks until user's turn                                   │
│                                                                             │
│  2. 👤 UPDATE USER CONTEXT                                                 │
│     ├─ Map user roster using picked_by field + user ID                    │
│     ├─ Count positions in user's current roster                           │
│     ├─ Analyze bye week distribution                                       │
│     └─ Generate position priority/avoid guidance                          │
│                                                                             │
│  3. 🤖 PROACTIVE RECOMMENDATIONS                                           │
│     ├─ Trigger at 6 picks before user's turn                             │
│     ├─ Trigger at 3 picks before user's turn                             │
│     ├─ Pre-compute recommendations for faster response                     │
│     └─ Cache results for immediate delivery when user's turn arrives      │
│                                                                             │
│  4. 🎯 CONTEXTUAL AI ANALYSIS                                              │
│     ├─ Apply enhanced position-based logic                                │
│     ├─ Use current FantasyPros SUPERFLEX rankings                         │
│     ├─ Consider user's specific roster needs                              │
│     ├─ Factor in bye week distribution                                    │
│     └─ Balance SUPERFLEX value with positional requirements               │
│                                                                             │
│  5. 📤 DELIVER RECOMMENDATIONS                                             │
│     ├─ Format 3 prioritized player recommendations                        │
│     ├─ Provide clear reasoning for each choice                            │
│     ├─ Include backup options and strategic context                       │
│     └─ Update web interface with real-time data                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🛠️ Key Technical Components

### Data Layer
- **Sleeper API Client**: Real-time draft monitoring, player database access
- **FantasyPros Integration**: Live SUPERFLEX rankings and projections  
- **Player Mapping System**: 11,389 player cross-platform ID resolution
- **Caching Layer**: Smart caching with TTL for API efficiency

### AI Processing Layer
- **CrewAI Framework**: Multi-agent orchestration and task delegation
- **Context Management**: Session state, user preferences, draft history
- **Decision Engine**: Enhanced logic rules for position-based recommendations
- **Real-time Analysis**: Live data processing with <2 second response times

### Application Layer  
- **FastAPI Backend**: RESTful API endpoints, WebSocket support
- **Web Interface**: Responsive UI with real-time updates
- **Proactive System**: Pre-computation triggers 3-6 picks ahead
- **Error Handling**: Graceful degradation and fallback mechanisms

## 📊 Data Storage & Caching Strategy

```
/data/
├── player_id_mapping.json     # 11,389 players cross-platform IDs
├── players_cache.json         # Sleeper player database (24hr TTL)
├── rankings_cache.json        # FantasyPros rankings (1hr TTL)
└── draft_state.json          # Current session state and context
```

## 🚀 Performance Characteristics

- **API Response Time**: <500ms for Sleeper calls
- **AI Recommendation Time**: <2 seconds end-to-end
- **Draft Monitoring Frequency**: 5-second polling cycle
- **Proactive Trigger Points**: 6 picks and 3 picks before user turn
- **Cache Hit Rate**: >90% for repeated player lookups
- **Memory Footprint**: <500MB for full operation

---

*This architecture enables real-time fantasy football draft assistance with intelligent, context-aware recommendations while maintaining high performance and reliability during critical draft windows.*