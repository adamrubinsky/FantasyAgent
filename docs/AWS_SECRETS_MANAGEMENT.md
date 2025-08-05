# 🔐 AWS Secrets Management for Bedrock AgentCore Deployment

## Overview

When deploying to AWS Bedrock AgentCore, we'll follow AWS Well-Architected security principles to manage API keys and secrets.

## Local Development (Current)

```bash
# .env.local (gitignored, for local development only)
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
SLEEPER_USERNAME=adamrubinsky
SLEEPER_LEAGUE_ID=1221322229124431872
```

## Production Deployment (AgentCore)

### Option 1: AWS Secrets Manager (Recommended)

```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name "fantasyfootball/anthropic/api-key" \
  --description "Claude API key for Fantasy Football Assistant" \
  --secret-string "sk-ant-api03-your-actual-key-here"

aws secretsmanager create-secret \
  --name "fantasyfootball/sleeper/credentials" \
  --description "Sleeper API credentials" \
  --secret-string '{"username":"adamrubinsky","league_id":"1221322229124431872"}'
```

### Option 2: AWS Systems Manager Parameter Store

```bash
# Store as SecureString parameters
aws ssm put-parameter \
  --name "/fantasyfootball/anthropic/api-key" \
  --value "sk-ant-api03-your-actual-key-here" \
  --type "SecureString"

aws ssm put-parameter \
  --name "/fantasyfootball/sleeper/username" \
  --value "adamrubinsky" \
  --type "String"
```

## AgentCore Integration

### Environment Variables (AgentCore Deployment)

```yaml
# agentcore-config.yml
environment:
  - name: ANTHROPIC_API_KEY
    valueFrom:
      secretRef:
        name: fantasyfootball-secrets
        key: anthropic-api-key
  - name: SLEEPER_USERNAME
    valueFrom:
      secretRef:
        name: fantasyfootball-secrets  
        key: sleeper-username
```

### Code Changes for Production

```python
# core/ai_assistant.py (production version)
import boto3
from botocore.exceptions import ClientError

class FantasyAIAssistant:
    def __init__(self, anthropic_api_key: str = None):
        # Try environment first (AgentCore injection)
        self.api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        
        # Fallback to AWS Secrets Manager if running in AWS
        if not self.api_key and self._is_aws_environment():
            self.api_key = self._get_secret('fantasyfootball/anthropic/api-key')
    
    def _is_aws_environment(self) -> bool:
        """Check if running in AWS environment"""
        return os.getenv('AWS_EXECUTION_ENV') is not None
    
    def _get_secret(self, secret_name: str) -> str:
        """Retrieve secret from AWS Secrets Manager"""
        try:
            session = boto3.session.Session()
            client = session.client('secretsmanager')
            response = client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
        except ClientError as e:
            print(f"Error retrieving secret {secret_name}: {e}")
            return None
```

## Security Best Practices

### 1. IAM Roles & Policies

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:fantasyfootball/*"
      ]
    }
  ]
}
```

### 2. Encryption at Rest

- Secrets Manager: KMS encryption by default
- Parameter Store: SecureString with KMS encryption
- AgentCore: Built-in encryption for environment variables

### 3. Rotation Strategy

```bash
# Set up automatic rotation for API keys
aws secretsmanager update-secret \
  --secret-id "fantasyfootball/anthropic/api-key" \
  --rotation-lambda-arn "arn:aws:lambda:region:account:function:rotate-anthropic-key" \
  --rotation-rules "AutomaticallyAfterDays=90"
```

### 4. Monitoring & Auditing

```bash
# CloudTrail logging for secret access
{
  "eventSource": "secretsmanager.amazonaws.com",
  "eventName": "GetSecretValue",
  "resources": [{
    "ARN": "arn:aws:secretsmanager:*:*:secret:fantasyfootball/*"
  }]
}
```

## Deployment Commands

### Manual Secret Setup

```bash
# Create secrets before deployment
aws secretsmanager create-secret \
  --name "fantasyfootball/anthropic/api-key" \
  --secret-string "$ANTHROPIC_API_KEY"

# Deploy AgentCore with secret references
agentcore deploy --secrets-from-aws --region us-east-1
```

### Infrastructure as Code (CloudFormation)

```yaml
Resources:
  AnthropicAPIKeySecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: fantasyfootball/anthropic/api-key
      Description: Claude API key for Fantasy Football Assistant
      SecretString: !Ref AnthropicAPIKey
      
  AgentCoreExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      Policies:
        - PolicyName: SecretsAccess
          PolicyDocument:
            Statement:
              - Effect: Allow
                Action: secretsmanager:GetSecretValue
                Resource: !Ref AnthropicAPIKeySecret
```

## Cost Optimization

- **Secrets Manager**: $0.40/secret/month + $0.05/10,000 API calls
- **Parameter Store**: Free for standard parameters, $0.05/advanced parameter/month
- **KMS**: $1/key/month + $0.03/10,000 requests

**Recommendation**: Use Secrets Manager for API keys (auto-rotation) and Parameter Store for configuration values.

## Local vs Production Summary

| Environment | Storage | Access | Rotation |
|-------------|---------|---------|----------|
| Local | .env.local | Direct file | Manual |
| AgentCore | Secrets Manager | IAM Role | Automatic |
| Backup | Parameter Store | IAM Role | Manual |

This architecture ensures your API keys are secure in production while maintaining easy local development.