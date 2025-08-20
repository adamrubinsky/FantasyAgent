# 🚀 AWS Bedrock AgentCore Deployment Guide

## Overview

This Fantasy Football Draft Assistant is designed to be deployed to AWS Bedrock AgentCore, which provides native MCP (Model Context Protocol) support. AgentCore automatically handles scaling, session isolation, and tool integration.

## Prerequisites

1. **AWS Account** with Bedrock access
2. **AgentCore CLI** installed: `pip install bedrock-agentcore-starter-toolkit`
3. **MCP packages**: `pip install mcp fastmcp` (already in requirements.txt)
4. **FantasyPros API access** (contact partners@fantasypros.com)

## MCP Server Structure

Our MCP server is located at `mcp_servers/fantasypros_mcp.py` and provides these tools:

- `get_rankings` - Consensus rankings with ADP and tiers
- `get_projections` - Player projections and stats
- `get_adp_analysis` - Value pick identification
- `get_tier_breaks` - Position tier analysis
- `get_superflex_strategy` - SUPERFLEX draft advice

## Deployment Steps

### 1. Prepare MCP Server

```bash
# Navigate to MCP server directory
cd mcp_servers/

# Test server locally first
python fantasypros_mcp.py
```

### 2. Configure AgentCore

```bash
# Configure deployment
agentcore configure -e fantasypros_mcp.py --protocol MCP

# This creates the necessary configuration files
```

### 3. Set Environment Variables

Create `.env.production` with your FantasyPros credentials:

```bash
# FantasyPros API
FANTASYPROS_API_KEY=your-api-key-here
FANTASYPROS_SESSION_COOKIE=your-session-cookie

# League Settings
DEFAULT_SCORING_FORMAT=half_ppr
DEFAULT_LEAGUE_TYPE=superflex
```

### 4. Deploy to AgentCore

```bash
# Launch to AWS
agentcore launch

# This will:
# - Build Docker container with your MCP server
# - Deploy to AWS Lambda/ECS
# - Set up API Gateway endpoints
# - Configure authentication via Cognito
```

### 5. Update Local App

Once deployed, update your local `.env.local`:

```bash
# AgentCore endpoints
AGENTCORE_MCP_URL=https://your-agent-endpoint.execute-api.region.amazonaws.com/mcp
AGENTCORE_AUTH_TOKEN=your-bearer-token-here
```

## Local vs Production Mode

### Local Development (Current)
- Uses mock FantasyPros data
- Direct function calls (no HTTP)
- Fast iteration and testing

### Production (AgentCore)
- Real FantasyPros API integration
- HTTP calls to AgentCore-hosted MCP server
- Auto-scaling and session isolation
- Enterprise security and monitoring

## Testing Deployment

```bash
# Test the deployed MCP server
python core/mcp_integration.py

# Should show "Running in PRODUCTION mode"
# If successful, commands will work with real FantasyPros data
```

## AgentCore Benefits

1. **Automatic Scaling** - Handles traffic spikes during draft day
2. **Session Isolation** - Each draft session is isolated
3. **Security** - Enterprise-grade authentication and authorization
4. **Monitoring** - Built-in observability and logging
5. **Cost Optimization** - Pay only for what you use

## FantasyPros API Integration

### Getting API Access

1. Contact FantasyPros partnership team: partners@fantasypros.com
2. Explain your use case: AI-powered fantasy football draft assistant
3. Request access to:
   - Consensus rankings API
   - ADP data API
   - Player projections API
   - Historical data API

### API Endpoints (Production)

Once you have API access, update `fantasypros_mcp.py` to use real endpoints:

```python
# Replace mock data with real API calls
async def get_rankings_from_api(scoring, superflex):
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"https://api.fantasypros.com/rankings/{scoring}"
    if superflex:
        url += "?format=superflex"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.json()
```

## Costs (Preview Pricing)

- **AgentCore Runtime**: Free until Sept 16, 2025
- **After Sept 16**: Standard AWS pricing for Lambda/ECS
- **FantasyPros API**: Custom pricing (contact them)

## Support & Troubleshooting

### Common Issues

1. **MCP Import Errors**: Ensure `mcp` and `fastmcp` are installed
2. **AgentCore CLI Issues**: Update to latest version
3. **API Rate Limits**: Implement exponential backoff
4. **Session Timeout**: AgentCore handles this automatically

### Debug Commands

```bash
# Check AgentCore status
agentcore status

# View logs
agentcore logs

# Test MCP endpoints
curl -X POST $AGENTCORE_MCP_URL/tools/get_rankings \
  -H "Authorization: Bearer $AGENTCORE_AUTH_TOKEN" \
  -d '{"position": "QB", "limit": 5}'
```

## Next Steps

1. **Secure FantasyPros Partnership** - Get real API access
2. **Deploy to AgentCore** - Follow steps above
3. **Test with Real Data** - Validate rankings accuracy
4. **Performance Tuning** - Optimize for draft day load
5. **Monitor & Scale** - Use AgentCore observability

---

*This deployment guide will be updated as AgentCore features evolve and FantasyPros integration is finalized.*