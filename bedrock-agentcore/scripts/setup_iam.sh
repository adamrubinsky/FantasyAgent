#!/bin/bash

# Amazon Bedrock AgentCore IAM Setup Script
# Creates necessary IAM roles and policies for Bedrock Agents

set -e

echo "🔐 Setting up IAM roles for Bedrock AgentCore"
echo "============================================="

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Create Bedrock Agent Execution Role
echo -e "${YELLOW}Creating Bedrock Agent Execution Role...${NC}"

# Trust policy for Bedrock
cat > /tmp/bedrock-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "bedrock.amazonaws.com",
                    "lambda.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# Create the execution role
ROLE_NAME="FantasyDraftBedrockExecutionRole"
echo -e "${YELLOW}Creating role: $ROLE_NAME${NC}"

aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file:///tmp/bedrock-trust-policy.json \
    --description "Execution role for Fantasy Draft Bedrock Agents" \
    2>/dev/null || echo -e "${GREEN}✓ Role already exists${NC}"

# Create custom policy for Bedrock Agent
cat > /tmp/bedrock-agent-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:CreateAgent",
                "bedrock:UpdateAgent",
                "bedrock:GetAgent",
                "bedrock:ListAgents",
                "bedrock:DeleteAgent",
                "bedrock:InvokeAgent",
                "bedrock:CreateAgentAlias",
                "bedrock:UpdateAgentAlias",
                "bedrock:GetAgentAlias",
                "bedrock:ListAgentAliases",
                "bedrock:DeleteAgentAlias"
            ],
            "Resource": "arn:aws:bedrock:${AWS_REGION}:${AWS_ACCOUNT_ID}:agent/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:CreateKnowledgeBase",
                "bedrock:UpdateKnowledgeBase",
                "bedrock:GetKnowledgeBase",
                "bedrock:ListKnowledgeBases",
                "bedrock:DeleteKnowledgeBase",
                "bedrock:Retrieve"
            ],
            "Resource": "arn:aws:bedrock:${AWS_REGION}:${AWS_ACCOUNT_ID}:knowledge-base/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "lambda:CreateFunction",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:GetFunction",
                "lambda:InvokeFunction",
                "lambda:ListFunctions",
                "lambda:DeleteFunction"
            ],
            "Resource": "arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:fantasy-draft-*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DescribeTable",
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/fantasy-draft-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::fantasy-draft-*",
                "arn:aws:s3:::fantasy-draft-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:CreateSecret",
                "secretsmanager:UpdateSecret"
            ],
            "Resource": "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:fantasy-draft-*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "xray:PutTraceSegments",
                "xray:PutTelemetryRecords"
            ],
            "Resource": "*"
        }
    ]
}
EOF

# Create and attach the policy
POLICY_NAME="FantasyDraftBedrockAgentPolicy"
echo -e "${YELLOW}Creating policy: $POLICY_NAME${NC}"

POLICY_ARN=$(aws iam create-policy \
    --policy-name $POLICY_NAME \
    --policy-document file:///tmp/bedrock-agent-policy.json \
    --description "Policy for Fantasy Draft Bedrock Agents" \
    --query 'Policy.Arn' \
    --output text 2>/dev/null) || \
    POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"

echo -e "${GREEN}✓ Policy ARN: $POLICY_ARN${NC}"

# Attach policy to role
echo -e "${YELLOW}Attaching policy to role...${NC}"
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $POLICY_ARN \
    2>/dev/null || echo -e "${GREEN}✓ Policy already attached${NC}"

# Create Lambda execution role for agent tools
LAMBDA_ROLE_NAME="FantasyDraftLambdaExecutionRole"
echo -e "${YELLOW}Creating Lambda execution role: $LAMBDA_ROLE_NAME${NC}"

cat > /tmp/lambda-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

aws iam create-role \
    --role-name $LAMBDA_ROLE_NAME \
    --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
    --description "Execution role for Fantasy Draft Lambda functions" \
    2>/dev/null || echo -e "${GREEN}✓ Lambda role already exists${NC}"

# Attach basic Lambda execution policy
aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
    2>/dev/null || echo -e "${GREEN}✓ Lambda policy already attached${NC}"

# Store role ARNs in environment file
BEDROCK_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
LAMBDA_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${LAMBDA_ROLE_NAME}"

echo -e "${YELLOW}Updating .env.bedrock with role ARNs...${NC}"
if [ -f "../.env.bedrock" ]; then
    sed -i.bak "s|^AGENT_RUNTIME_ROLE_ARN=.*|AGENT_RUNTIME_ROLE_ARN=${BEDROCK_ROLE_ARN}|" ../.env.bedrock
    sed -i.bak "s|^AGENT_EXECUTION_ROLE_ARN=.*|AGENT_EXECUTION_ROLE_ARN=${LAMBDA_ROLE_ARN}|" ../.env.bedrock
    echo -e "${GREEN}✓ Updated .env.bedrock${NC}"
fi

# Clean up temp files
rm -f /tmp/bedrock-trust-policy.json
rm -f /tmp/bedrock-agent-policy.json
rm -f /tmp/lambda-trust-policy.json

echo ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}✅ IAM setup complete!${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""
echo "Created resources:"
echo "  - Bedrock Execution Role: $BEDROCK_ROLE_ARN"
echo "  - Lambda Execution Role: $LAMBDA_ROLE_ARN"
echo "  - Agent Policy: $POLICY_ARN"
echo ""
echo "Next step: Run ./scripts/deploy_infrastructure.sh"
echo ""