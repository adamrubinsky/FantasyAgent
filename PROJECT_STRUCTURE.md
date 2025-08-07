# Fantasy Agent Project Structure

## 📁 Directory Organization

```
FantasyAgent/
├── 📂 agents/                  # CrewAI multi-agent system
│   ├── draft_crew.py           # 4-agent draft analysis system
│   └── __init__.py
│
├── 📂 api/                     # External API integrations
│   ├── sleeper_client.py       # Sleeper Fantasy API client
│   ├── yahoo_client.py         # Yahoo Fantasy API client (future)
│   └── __init__.py
│
├── 📂 core/                    # Core business logic
│   ├── draft_monitor.py        # Real-time draft monitoring
│   ├── official_fantasypros.py # FantasyPros API integration
│   ├── player_data_enricher.py # Enhanced player data
│   └── recommendation_engine.py
│
├── 📂 data/                    # Cached data and rankings
│   ├── players_cache.json      # NFL player database
│   ├── fantasypros_rankings_*.json
│   └── mock_players.json
│
├── 📂 deployment/              # Deployment configurations
│   ├── agentcore/              # Bedrock AgentCore files
│   │   ├── fantasy_draft_agentcore.py
│   │   ├── .bedrock_agentcore.yaml
│   │   └── agentcore_*.py
│   ├── lambda/                 # Lambda backend
│   │   ├── lambda_backend.py
│   │   └── lambda-deployment.zip
│   └── scripts/                # Deployment scripts
│       ├── deploy_*.py
│       └── setup_*.sh
│
├── 📂 docs/                    # Documentation
│   ├── architecture/           # System architecture docs
│   │   ├── DEPLOYMENT_PLAN.md
│   │   └── REAL_AGENTCORE_UNDERSTANDING.md
│   └── setup/                  # Setup guides
│       ├── SETUP_GUIDE.md
│       └── ROOT_USER_SETUP.md
│
├── 📂 infrastructure/          # AWS infrastructure configs
│   ├── iam/                   # IAM roles and policies
│   ├── policies/              # IAM policy JSONs
│   │   ├── CODEBUILD_IAM_POLICY.json
│   │   └── BROADER_IAM_POLICY.json
│   └── codebuild-env.json
│
├── 📂 static/                  # Frontend static assets
│   └── mock-backend.js         # Mock backend for testing
│
├── 📂 templates/               # HTML templates
│   └── index.html              # Main web interface
│
├── 📂 tests/                   # Test files
│   ├── integration/            # Integration tests
│   │   └── test_*.py
│   └── unit/                   # Unit tests
│       └── debug_*.py
│
├── 📂 archive/                 # Archived/deprecated files
│   └── incorrect_bedrock_agents/
│
├── 📂 logs/                    # Application logs
│   └── fantasy-draft-agentcore.log
│
├── 📄 main.py                  # Main CLI entry point
├── 📄 web_app.py              # Flask web application
├── 📄 requirements.txt         # Python dependencies
├── 📄 Dockerfile              # Docker configuration
├── 📄 ACTION_LOG.md           # Development history
├── 📄 OVERVIEW.md             # Project overview
├── 📄 README.md               # Project readme
└── 📄 .env.example            # Environment variables template
```

## 🔑 Key Files

### Core Application
- `main.py` - CLI interface for the draft assistant
- `web_app.py` - Flask web server for browser interface
- `requirements.txt` - All Python package dependencies

### API Clients
- `api/sleeper_client.py` - Async Sleeper API integration
- `core/official_fantasypros.py` - FantasyPros rankings API

### Multi-Agent System
- `agents/draft_crew.py` - CrewAI 4-agent analysis system

### Frontend
- `templates/index.html` - Interactive web UI
- `static/mock-backend.js` - Mock responses for testing

### Deployment
- `deployment/lambda/lambda_backend.py` - AWS Lambda backend
- `deployment/agentcore/fantasy_draft_agentcore.py` - AgentCore implementation

### Documentation
- `ACTION_LOG.md` - Complete development history
- `OVERVIEW.md` - Current project status
- `docs/architecture/DEPLOYMENT_PLAN.md` - Full deployment strategy

## 🌐 Live Endpoints

### Frontend
- **URL**: http://YOUR_S3_BUCKET_NAME.s3-website-us-east-1.amazonaws.com
- **Hosting**: AWS S3 Static Website

### Backend API
- **URL**: https://YOUR_API_GATEWAY_ID.execute-api.us-east-1.amazonaws.com/prod
- **Service**: AWS Lambda + API Gateway

## 🚀 Quick Start

1. **Local Development**
   ```bash
   python main.py test    # Test Sleeper connection
   python web_app.py      # Start local web server
   ```

2. **Deploy Updates**
   ```bash
   # Update frontend
   aws s3 sync templates/ s3://YOUR_S3_BUCKET_NAME/
   aws s3 sync static/ s3://YOUR_S3_BUCKET_NAME/static/
   
   # Update Lambda backend
   cd deployment/lambda
   zip lambda-deployment.zip lambda_backend.py
   aws lambda update-function-code --function-name fantasy-draft-backend --zip-file fileb://lambda-deployment.zip
   ```

## 📊 Current Status (Day 3 - August 7th)

- ✅ Frontend deployed with real URL access
- ✅ Lambda backend API working (mock responses)
- ✅ URL extraction for Sleeper/Yahoo drafts
- 🔄 AgentCore deployment (CodeBuild issues)
- 🎯 Next: Connect CrewAI agents to Lambda backend