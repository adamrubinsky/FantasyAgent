# Fantasy Draft Assistant - Full Stack Deployment Plan

## 🎯 User Request: "I want to be able to put in a real URL to access it"

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                    │
├─────────────────────────────────────────────────────────────┤
│  🌐 Frontend (Web UI)                                      │
│  ├─ AWS S3 + CloudFront (Static Site)                     │
│  ├─ Custom Domain: drafts.adamrubinsky.com                │
│  └─ Real URL access from anywhere                         │
├─────────────────────────────────────────────────────────────┤
│  🤖 Backend (AgentCore Runtime)                            │
│  ├─ Bedrock AgentCore (Multi-Agent System)                │
│  ├─ API Gateway for HTTP access                           │
│  └─ WebSocket support for real-time updates               │
├─────────────────────────────────────────────────────────────┤
│  🔗 Integrations                                           │
│  ├─ Sleeper API (Draft monitoring)                        │
│  ├─ FantasyPros API (Live rankings)                       │
│  └─ CrewAI Multi-Agent orchestration                      │
└─────────────────────────────────────────────────────────────┘
```

## Phase 1: AgentCore Backend Deployment (Current Focus)

### 1.1 Configure AgentCore Runtime
```bash
# Configure AgentCore with your AWS role
agentcore configure --entrypoint fantasy_draft_agentcore.py \
  --execution-role-arn arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/fantasy-draft-agentcore-role

# Deploy to AgentCore Runtime  
agentcore launch
```

### 1.2 Expected Results
- AgentCore runtime endpoint (AWS managed)
- Multi-agent system running in cloud
- 8-hour session support for draft duration
- Built-in observability and monitoring

## Phase 2: Frontend Deployment Options

### Option A: AWS S3 + CloudFront (Recommended)
**Benefits**: Fast, scalable, cost-effective, CDN distribution
**Timeline**: 30 minutes setup

```bash
# 1. Create S3 bucket for static website
aws s3 mb s3://fantasy-draft-assistant-web

# 2. Configure static website hosting
aws s3 website s3://fantasy-draft-assistant-web \
  --index-document index.html

# 3. Upload web files
aws s3 sync templates/ s3://fantasy-draft-assistant-web/
aws s3 sync static/ s3://fantasy-draft-assistant-web/static/

# 4. Create CloudFront distribution (optional - for custom domain)
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
```

**Result**: https://fantasy-draft-assistant-web.s3-website-us-east-1.amazonaws.com

### Option B: AWS Amplify (Easiest)
**Benefits**: Git integration, automatic deployments, custom domains
**Timeline**: 15 minutes setup

```bash
# Connect GitHub repo to Amplify
aws amplify create-app --name fantasy-draft-assistant \
  --repository https://github.com/adamrubinsky/FantasyAgent

# Configure build settings for static site
aws amplify create-branch --app-id <app-id> --branch-name main
```

**Result**: https://main.abcd123.amplifyapp.com (plus custom domain option)

### Option C: AWS App Runner (Full Stack)
**Benefits**: Handles both frontend and backend, automatic scaling
**Timeline**: 20 minutes setup

```bash
# Deploy web_app.py as full stack application
aws apprunner create-service --service-name fantasy-draft-assistant \
  --source-configuration '{"ImageRepository": {"ImageConfiguration": {"Port": "8000"}}}'
```

**Result**: https://xyz123.us-east-1.awsapprunner.com

## Phase 3: Integration Configuration

### 3.1 Update Frontend API Endpoints
```javascript
// In static/app.js - Update API endpoints
const API_BASE_URL = 'https://your-agentcore-endpoint.amazonaws.com';
const WS_URL = 'wss://your-agentcore-endpoint.amazonaws.com/ws';
```

### 3.2 CORS Configuration
```python
# In AgentCore agent - Add CORS headers
@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "https://your-frontend-domain.com"
    return response
```

## Phase 4: Custom Domain Setup (Optional)

### 4.1 Route 53 Configuration
```bash
# Create hosted zone (if not exists)
aws route53 create-hosted-zone --name adamrubinsky.com --caller-reference fantasy-$(date +%s)

# Create CNAME record for subdomain
aws route53 change-resource-record-sets --hosted-zone-id Z123456789 \
  --change-batch file://route53-changes.json
```

### 4.2 SSL Certificate
```bash
# Request ACM certificate
aws acm request-certificate --domain-name drafts.adamrubinsky.com \
  --validation-method DNS
```

## Recommended Deployment Strategy

### 🚀 Quick Start (Today)
1. **Deploy AgentCore Backend** - Get multi-agent system running in AWS
2. **AWS Amplify Frontend** - Quickest way to get real URL access
3. **Test with Sleeper Mock Draft** - Validate full integration

### 📈 Production Ready (Next Week)  
1. **Custom domain setup** - drafts.adamrubinsky.com
2. **CloudFront optimization** - Global CDN for fast access
3. **Monitoring and alerts** - AgentCore observability + CloudWatch

## Commands to Execute (Next Steps)

```bash
# 1. Configure AgentCore
agentcore configure --entrypoint fantasy_draft_agentcore.py \
  -er arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/fantasy-draft-agentcore-role

# 2. Deploy to AgentCore Runtime
agentcore launch

# 3. Deploy frontend to Amplify
aws amplify create-app --name fantasy-draft-assistant \
  --repository https://github.com/adamrubinsky/FantasyAgent

# 4. Test full integration
curl https://your-agentcore-endpoint/test
curl https://your-amplify-url.amplifyapp.com
```

## Expected Timeline
- **AgentCore Backend**: 15 minutes (once configured correctly)  
- **Frontend Deployment**: 15 minutes (Amplify) or 30 minutes (S3+CloudFront)
- **Integration Testing**: 30 minutes
- **Custom Domain** (optional): 1 hour

## Benefits of This Approach
- ✅ **Real URL access** from anywhere
- ✅ **Proper AgentCore deployment** (not fake Bedrock Agents)
- ✅ **Mobile responsive** for draft day access
- ✅ **WebSocket real-time updates** during draft
- ✅ **Well-Architected** following AWS best practices
- ✅ **Production ready** for August 14th draft

Would you like to start with AgentCore deployment or frontend deployment first?