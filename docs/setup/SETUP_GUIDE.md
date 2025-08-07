# Fantasy Draft Assistant - Complete AWS Setup Guide

## 🎯 Current Status
- ✅ Bedrock models activated in your AWS account
- ✅ SAM CLI installed
- ✅ IAM setup scripts ready
- ✅ Deployment scripts ready

## 🚀 Complete Setup Process

### Step 1: Create Dedicated IAM User
Run this script as your **root user or admin user**:

```bash
./iam-setup/create_project_user.sh
```

This will create:
- ✅ IAM user: `fantasy-draft-deployer`
- ✅ Comprehensive deployment policy
- ✅ Lambda execution role
- ✅ Access keys (saved to `fantasy-draft-credentials.txt`)

### Step 2: Configure AWS CLI Profile
```bash
# Configure new profile with the generated credentials
aws configure --profile fantasy-draft

# Enter the credentials from fantasy-draft-credentials.txt:
# AWS Access Key ID: [from credentials file]
# AWS Secret Access Key: [from credentials file]
# Default region name: us-east-1
# Default output format: json
```

### Step 3: Test Bedrock Access
```bash
# Set the profile
export AWS_PROFILE=fantasy-draft

# Test Bedrock with new credentials
python3 -c "
import boto3, json
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
response = bedrock.invoke_model(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    body=json.dumps({
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': 50,
        'messages': [{'role': 'user', 'content': 'Say hello from Bedrock!'}]
    })
)
result = json.loads(response['body'].read())
print('✅ Bedrock:', result['content'][0]['text'])
"
```

### Step 4: Deploy to AWS
```bash
# Deploy using the new profile
./deploy_with_profile.sh
```

This will:
- ✅ Package Lambda function with Bedrock integration
- ✅ Deploy CloudFormation stack
- ✅ Create API Gateway endpoints
- ✅ Set up DynamoDB for state storage

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Your AWS Account                          │
├─────────────────────────────────────────────────────────────┤
│  IAM User: fantasy-draft-deployer                          │
│  └── Policies: Bedrock, Lambda, API Gateway, DynamoDB      │
├─────────────────────────────────────────────────────────────┤
│  Lambda Function: fantasy-draft-bedrock-agent              │
│  ├── Runtime: Python 3.11                                 │
│  ├── Memory: 1024 MB                                       │
│  ├── Timeout: 30 seconds                                   │
│  └── Environment: BEDROCK_MODEL_ID, ANTHROPIC_API_KEY      │
├─────────────────────────────────────────────────────────────┤
│  API Gateway: HTTP + WebSocket APIs                        │
│  ├── Endpoints: /, /test, /recommend                       │
│  └── CORS: Enabled for web access                          │
├─────────────────────────────────────────────────────────────┤
│  DynamoDB: fantasy-draft-sessions                          │
│  └── Billing: Pay-per-request                              │
├─────────────────────────────────────────────────────────────┤
│  Amazon Bedrock: Claude Models                             │
│  └── Models: claude-3-5-sonnet-20241022-v2:0              │
└─────────────────────────────────────────────────────────────┘
```

## 🧪 Testing Your Deployment

### Test 1: Basic API Health
```bash
curl https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/Prod
```

### Test 2: Bedrock Integration
```bash
curl -X POST https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/Prod/test
```

### Test 3: Draft Recommendation
```bash
curl -X POST https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/Prod/recommend \
  -H "Content-Type: application/json" \
  -d '{"question": "I'\''m drafting 7th overall in SUPERFLEX. Who should I target?"}'
```

## 💰 Cost Estimation

| Service | Usage | Monthly Cost |
|---------|--------|--------------|
| **Lambda** | 1M requests, 1GB-sec | ~$5 |
| **API Gateway** | 1M requests | ~$3.50 |
| **DynamoDB** | Light usage | ~$1 |
| **Bedrock** | 100K tokens | ~$3 |
| **Total** | | **~$12.50/month** |

## 🔧 Configuration Options

### Environment Variables
```bash
# In Lambda function
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
USE_BEDROCK=true
ANTHROPIC_API_KEY=[fallback]
AWS_ACCOUNT_ID=YOUR_AWS_ACCOUNT_ID
PROJECT_NAME=fantasy-draft
```

### Available Bedrock Models
- `anthropic.claude-3-5-sonnet-20241022-v2:0` (Recommended)
- `anthropic.claude-3-5-haiku-20241022-v2:0` (Faster/Cheaper)
- `anthropic.claude-3-opus-20240229-v1:0` (Most Capable)

## 🚨 Troubleshooting

### Issue: "AccessDenied" on Bedrock
**Solution**: Make sure you've activated Claude models in AWS Console → Bedrock → Model access

### Issue: "User cannot perform iam:CreateRole"
**Solution**: Run the IAM setup script with root/admin user, not regular user

### Issue: SAM deployment fails
**Solution**: Make sure AWS_PROFILE=fantasy-draft is set

### Issue: Lambda timeout
**Solution**: Increase timeout in template.yaml (currently 30s)

## 🎉 Success Indicators

✅ **IAM Setup Complete**: User and roles created  
✅ **Bedrock Access**: Can invoke Claude models  
✅ **Lambda Deployed**: Function responding to requests  
✅ **API Working**: Can get recommendations via HTTP  
✅ **Cost Optimized**: Pay-per-use serverless architecture  

## 📚 Next Steps After Deployment

1. **Web UI**: Deploy frontend to S3 + CloudFront
2. **WebSocket**: Add real-time draft monitoring
3. **Multi-Agent**: Expand to full CrewAI orchestration
4. **Monitoring**: Add CloudWatch dashboards
5. **Scaling**: Add auto-scaling based on usage

---

*This setup gives you a production-ready Fantasy Football Draft Assistant using AWS Well-Architected principles with Bedrock integration!*