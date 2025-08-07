#!/bin/bash

# Hybrid AWS Deployment Script for Fantasy Draft Assistant
# Deploys using Lambda + API Gateway with direct Anthropic API

set -e

echo "🚀 Fantasy Draft Assistant - Hybrid AWS Deployment"
echo "=================================================="
echo "This deploys your app to AWS Lambda with API Gateway"
echo "Using direct Anthropic API (no Bedrock required)"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
STACK_NAME="fantasy-draft-assistant"
S3_BUCKET="fantasy-draft-${AWS_ACCOUNT_ID}"
LAMBDA_FUNCTION="fantasy-draft-api"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Account: $AWS_ACCOUNT_ID"
echo "  Region: $AWS_REGION"
echo "  Stack: $STACK_NAME"
echo ""

# Step 1: Create S3 bucket for deployment artifacts
echo -e "${YELLOW}Step 1: Creating S3 bucket for deployment...${NC}"
aws s3 mb "s3://${S3_BUCKET}" --region $AWS_REGION 2>/dev/null || echo -e "${GREEN}✓ Bucket already exists${NC}"

# Step 2: Package the Lambda function
echo -e "${YELLOW}Step 2: Packaging Lambda function...${NC}"

# Create temp directory for Lambda package
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/package"
mkdir -p $PACKAGE_DIR

echo "  Copying application files..."
# Copy main application files
cp -r ../../web_app.py $PACKAGE_DIR/
cp -r ../../api $PACKAGE_DIR/
cp -r ../../core $PACKAGE_DIR/
cp -r ../../agents $PACKAGE_DIR/
cp -r ../../templates $PACKAGE_DIR/
cp -r ../../static $PACKAGE_DIR/
cp ../../.env.local $PACKAGE_DIR/.env 2>/dev/null || echo "  No .env.local found"

# Create Lambda handler
cat > $PACKAGE_DIR/lambda_handler.py << 'EOF'
"""
AWS Lambda handler for Fantasy Draft Assistant
Uses Mangum to adapt FastAPI for Lambda
"""

import os
import json
from mangum import Mangum
from web_app import app

# Configure for Lambda environment
os.environ['AWS_LAMBDA_FUNCTION_NAME'] = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', '')

# Create the handler
handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    """Main Lambda entry point"""
    # Log the event for debugging
    print(f"Event: {json.dumps(event)}")
    
    # Handle WebSocket connections separately
    if event.get('requestContext', {}).get('eventType') == 'CONNECT':
        return {
            'statusCode': 200,
            'body': 'Connected'
        }
    elif event.get('requestContext', {}).get('eventType') == 'DISCONNECT':
        return {
            'statusCode': 200,
            'body': 'Disconnected'
        }
    
    # Use Mangum for HTTP requests
    return handler(event, context)
EOF

# Create requirements for Lambda
cat > $PACKAGE_DIR/requirements.txt << 'EOF'
fastapi==0.110.0
mangum==0.17.0
anthropic==0.25.0
boto3
uvicorn
websockets
httpx
python-dotenv
aiofiles
pydantic
sleeper-api-wrapper
EOF

echo "  Installing dependencies..."
cd $PACKAGE_DIR
pip install -r requirements.txt -t . --platform manylinux2014_x86_64 --python-version 3.11 --only-binary :all: --quiet

# Create deployment package
echo "  Creating ZIP package..."
zip -r $TEMP_DIR/lambda-package.zip . -q

# Upload to S3
echo -e "${YELLOW}Step 3: Uploading to S3...${NC}"
aws s3 cp $TEMP_DIR/lambda-package.zip "s3://${S3_BUCKET}/lambda-package.zip"
echo -e "${GREEN}✓ Package uploaded${NC}"

# Step 4: Create CloudFormation template
echo -e "${YELLOW}Step 4: Creating CloudFormation template...${NC}"

cat > $TEMP_DIR/template.yaml << EOF
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Fantasy Draft Assistant - Hybrid Deployment

Parameters:
  AnthropicApiKey:
    Type: String
    NoEcho: true
    Description: Anthropic API Key
    Default: ''
  
  FantasyProsApiKey:
    Type: String
    NoEcho: true
    Description: FantasyPros API Key
    Default: ''
  
  SleeperUsername:
    Type: String
    Description: Sleeper Username
    Default: ''

Resources:
  # Lambda Function
  FantasyDraftFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: ${LAMBDA_FUNCTION}
      Runtime: python3.11
      Handler: lambda_handler.lambda_handler
      Code:
        S3Bucket: ${S3_BUCKET}
        S3Key: lambda-package.zip
      MemorySize: 1024
      Timeout: 30
      Environment:
        Variables:
          ANTHROPIC_API_KEY: !Ref AnthropicApiKey
          FANTASYPROS_API_KEY: !Ref FantasyProsApiKey
          SLEEPER_USERNAME: !Ref SleeperUsername
      Role: !GetAtt LambdaRole.Arn

  # Lambda Execution Role
  LambdaRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: DynamoDBAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - dynamodb:*
                Resource: '*'

  # API Gateway
  ApiGateway:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: fantasy-draft-api
      ProtocolType: HTTP
      CorsConfiguration:
        AllowOrigins:
          - '*'
        AllowMethods:
          - GET
          - POST
          - OPTIONS
        AllowHeaders:
          - '*'

  # API Integration
  ApiIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref ApiGateway
      IntegrationType: AWS_PROXY
      IntegrationUri: !Sub 'arn:aws:apigatewayv2:\${AWS::Region}:lambda:path/2015-03-31/functions/\${FantasyDraftFunction.Arn}/invocations'
      PayloadFormatVersion: '2.0'

  # API Route
  ApiRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref ApiGateway
      RouteKey: '\$default'
      Target: !Sub 'integrations/\${ApiIntegration}'

  # API Stage
  ApiStage:
    Type: AWS::ApiGatewayV2::Stage
    Properties:
      ApiId: !Ref ApiGateway
      StageName: prod
      AutoDeploy: true

  # Lambda Permission for API Gateway
  LambdaApiPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref FantasyDraftFunction
      Action: lambda:InvokeFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub 'arn:aws:execute-api:\${AWS::Region}:\${AWS::AccountId}:\${ApiGateway}/*/*'

  # WebSocket API for real-time features
  WebSocketApi:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: fantasy-draft-websocket
      ProtocolType: WEBSOCKET
      RouteSelectionExpression: '\$request.body.action'

  # DynamoDB Table for session storage
  SessionTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: fantasy-draft-sessions
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: session_id
          AttributeType: S
      KeySchema:
        - AttributeName: session_id
          KeyType: HASH

Outputs:
  ApiUrl:
    Description: API Gateway URL
    Value: !Sub 'https://\${ApiGateway}.execute-api.\${AWS::Region}.amazonaws.com/prod'
  
  WebSocketUrl:
    Description: WebSocket API URL
    Value: !Sub 'wss://\${WebSocketApi}.execute-api.\${AWS::Region}.amazonaws.com/prod'
  
  FunctionArn:
    Description: Lambda Function ARN
    Value: !GetAtt FantasyDraftFunction.Arn
EOF

# Step 5: Deploy with CloudFormation
echo -e "${YELLOW}Step 5: Deploying CloudFormation stack...${NC}"

# Get API keys from .env.local
if [ -f "../../.env.local" ]; then
    source ../../.env.local
fi

aws cloudformation deploy \
    --template-file $TEMP_DIR/template.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        AnthropicApiKey="${ANTHROPIC_API_KEY:-}" \
        FantasyProsApiKey="${FANTASYPROS_API_KEY:-}" \
        SleeperUsername="${SLEEPER_USERNAME:-}" \
    --capabilities CAPABILITY_IAM \
    --region $AWS_REGION

echo -e "${GREEN}✓ Stack deployed${NC}"

# Step 6: Get outputs
echo -e "${YELLOW}Step 6: Getting deployment URLs...${NC}"

API_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
    --output text)

WS_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`WebSocketUrl`].OutputValue' \
    --output text)

# Clean up
rm -rf $TEMP_DIR

echo ""
echo -e "${GREEN}=================================================="
echo -e "✅ Deployment Complete!"
echo -e "=================================================="
echo -e "${NC}"
echo "🌐 Web UI: $API_URL"
echo "🔌 WebSocket: $WS_URL"
echo ""
echo "Test your deployment:"
echo "  curl $API_URL"
echo ""
echo "To update:"
echo "  ./scripts/deploy_hybrid.sh"
echo ""
echo "To delete:"
echo "  aws cloudformation delete-stack --stack-name $STACK_NAME"
echo ""