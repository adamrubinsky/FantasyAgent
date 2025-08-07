#!/bin/bash

# Create dedicated IAM user and roles for Fantasy Draft Assistant
# Run this with your root account or admin user

set -e

echo "🔐 Creating IAM Setup for Fantasy Draft Assistant"
echo "=================================================="

# Configuration
PROJECT_NAME="fantasy-draft"
IAM_USER="${PROJECT_NAME}-deployer"
DEPLOYMENT_ROLE="${PROJECT_NAME}-deployment-role"
LAMBDA_ROLE="${PROJECT_NAME}-lambda-execution-role"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Creating IAM resources for project: ${PROJECT_NAME}${NC}"
echo "Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo ""

# Step 1: Create IAM User
echo -e "${YELLOW}Step 1: Creating IAM User: ${IAM_USER}${NC}"
aws iam create-user \
    --user-name ${IAM_USER} \
    --tags "Key=Project,Value=FantasyDraftAssistant" "Key=Environment,Value=Production" \
    2>/dev/null || echo -e "${GREEN}✓ User already exists${NC}"

# Step 2: Create Access Keys for the user
echo -e "${YELLOW}Step 2: Creating Access Keys${NC}"
ACCESS_KEY_RESULT=$(aws iam create-access-key --user-name ${IAM_USER} 2>/dev/null || echo "EXISTS")

if [ "$ACCESS_KEY_RESULT" != "EXISTS" ]; then
    ACCESS_KEY_ID=$(echo $ACCESS_KEY_RESULT | jq -r '.AccessKey.AccessKeyId')
    SECRET_ACCESS_KEY=$(echo $ACCESS_KEY_RESULT | jq -r '.AccessKey.SecretAccessKey')
    
    # Save credentials to a secure file
    cat > fantasy-draft-credentials.txt << EOF
AWS Access Credentials for Fantasy Draft Assistant
==================================================
IMPORTANT: Save these credentials securely. The secret key cannot be retrieved again.

User Name: ${IAM_USER}
Access Key ID: ${ACCESS_KEY_ID}
Secret Access Key: ${SECRET_ACCESS_KEY}

To configure AWS CLI with these credentials:
aws configure --profile fantasy-draft

Or add to ~/.aws/credentials:
[fantasy-draft]
aws_access_key_id = ${ACCESS_KEY_ID}
aws_secret_access_key = ${SECRET_ACCESS_KEY}
region = ${AWS_REGION}
EOF
    
    echo -e "${GREEN}✓ Access keys created and saved to fantasy-draft-credentials.txt${NC}"
    echo -e "${RED}⚠️  IMPORTANT: Save these credentials securely and delete the file!${NC}"
else
    echo -e "${GREEN}✓ User already has access keys${NC}"
fi

# Step 3: Create comprehensive policy for the project
echo -e "${YELLOW}Step 3: Creating Project Policy${NC}"

cat > /tmp/fantasy-draft-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockFullAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:*",
                "bedrock-runtime:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "LambdaManagement",
            "Effect": "Allow",
            "Action": [
                "lambda:CreateFunction",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:GetFunction",
                "lambda:GetFunctionConfiguration",
                "lambda:InvokeFunction",
                "lambda:ListFunctions",
                "lambda:DeleteFunction",
                "lambda:PublishVersion",
                "lambda:CreateAlias",
                "lambda:UpdateAlias",
                "lambda:GetPolicy",
                "lambda:PutFunctionConcurrency",
                "lambda:AddPermission",
                "lambda:RemovePermission",
                "lambda:TagResource"
            ],
            "Resource": [
                "arn:aws:lambda:*:${AWS_ACCOUNT_ID}:function:${PROJECT_NAME}-*"
            ]
        },
        {
            "Sid": "APIGatewayManagement",
            "Effect": "Allow",
            "Action": [
                "apigateway:*"
            ],
            "Resource": [
                "arn:aws:apigateway:*::/restapis/*",
                "arn:aws:apigateway:*::/apis/*"
            ]
        },
        {
            "Sid": "DynamoDBManagement",
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:UpdateTable",
                "dynamodb:DeleteTable",
                "dynamodb:DescribeTable",
                "dynamodb:ListTables",
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:TagResource"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:${AWS_ACCOUNT_ID}:table/${PROJECT_NAME}-*"
            ]
        },
        {
            "Sid": "S3Management",
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:DeleteBucket",
                "s3:ListBucket",
                "s3:GetBucketLocation",
                "s3:GetBucketPolicy",
                "s3:PutBucketPolicy",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucketVersions",
                "s3:GetBucketWebsite",
                "s3:PutBucketWebsite"
            ],
            "Resource": [
                "arn:aws:s3:::${PROJECT_NAME}-*",
                "arn:aws:s3:::${PROJECT_NAME}-*/*"
            ]
        },
        {
            "Sid": "CloudFormationManagement",
            "Effect": "Allow",
            "Action": [
                "cloudformation:CreateStack",
                "cloudformation:UpdateStack",
                "cloudformation:DeleteStack",
                "cloudformation:DescribeStacks",
                "cloudformation:DescribeStackEvents",
                "cloudformation:GetTemplate",
                "cloudformation:ValidateTemplate",
                "cloudformation:CreateChangeSet",
                "cloudformation:ExecuteChangeSet"
            ],
            "Resource": [
                "arn:aws:cloudformation:*:${AWS_ACCOUNT_ID}:stack/${PROJECT_NAME}-*/*"
            ]
        },
        {
            "Sid": "IAMRoleManagement",
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:GetRole",
                "iam:GetRolePolicy",
                "iam:PassRole",
                "iam:ListRolePolicies",
                "iam:UpdateAssumeRolePolicy",
                "iam:TagRole"
            ],
            "Resource": [
                "arn:aws:iam::${AWS_ACCOUNT_ID}:role/${PROJECT_NAME}-*"
            ]
        },
        {
            "Sid": "CloudWatchLogging",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:GetLogEvents",
                "logs:FilterLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:*:${AWS_ACCOUNT_ID}:log-group:/aws/lambda/${PROJECT_NAME}-*"
            ]
        },
        {
            "Sid": "SecretsManager",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:CreateSecret",
                "secretsmanager:GetSecretValue",
                "secretsmanager:UpdateSecret",
                "secretsmanager:DeleteSecret",
                "secretsmanager:DescribeSecret",
                "secretsmanager:TagResource"
            ],
            "Resource": [
                "arn:aws:secretsmanager:*:${AWS_ACCOUNT_ID}:secret:${PROJECT_NAME}-*"
            ]
        },
        {
            "Sid": "CloudFrontManagement",
            "Effect": "Allow",
            "Action": [
                "cloudfront:CreateDistribution",
                "cloudfront:UpdateDistribution",
                "cloudfront:GetDistribution",
                "cloudfront:DeleteDistribution",
                "cloudfront:CreateInvalidation"
            ],
            "Resource": "*"
        },
        {
            "Sid": "BasicServices",
            "Effect": "Allow",
            "Action": [
                "sts:GetCallerIdentity",
                "ec2:DescribeRegions",
                "ec2:DescribeAvailabilityZones"
            ],
            "Resource": "*"
        }
    ]
}
EOF

# Create the policy
POLICY_NAME="${PROJECT_NAME}-deployment-policy"
echo -e "${YELLOW}Creating policy: ${POLICY_NAME}${NC}"

POLICY_ARN=$(aws iam create-policy \
    --policy-name ${POLICY_NAME} \
    --policy-document file:///tmp/fantasy-draft-policy.json \
    --description "Comprehensive policy for Fantasy Draft Assistant deployment" \
    --query 'Policy.Arn' \
    --output text 2>/dev/null) || \
    POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"

echo -e "${GREEN}✓ Policy created/exists: ${POLICY_ARN}${NC}"

# Step 4: Attach policy to user
echo -e "${YELLOW}Step 4: Attaching policy to user${NC}"
aws iam attach-user-policy \
    --user-name ${IAM_USER} \
    --policy-arn ${POLICY_ARN} \
    2>/dev/null || echo -e "${GREEN}✓ Policy already attached${NC}"

# Step 5: Create Lambda Execution Role
echo -e "${YELLOW}Step 5: Creating Lambda Execution Role${NC}"

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
    --role-name ${LAMBDA_ROLE} \
    --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
    --description "Execution role for Fantasy Draft Lambda functions" \
    --tags "Key=Project,Value=FantasyDraftAssistant" \
    2>/dev/null || echo -e "${GREEN}✓ Lambda role already exists${NC}"

# Attach AWS managed policy for Lambda basic execution
aws iam attach-role-policy \
    --role-name ${LAMBDA_ROLE} \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
    2>/dev/null || echo -e "${GREEN}✓ Lambda policy already attached${NC}"

# Create Lambda-specific policy for accessing other services
cat > /tmp/lambda-service-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock-runtime:InvokeModel",
                "bedrock-runtime:InvokeModelWithResponseStream"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": "arn:aws:dynamodb:*:${AWS_ACCOUNT_ID}:table/${PROJECT_NAME}-*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:*:${AWS_ACCOUNT_ID}:secret:${PROJECT_NAME}-*"
        }
    ]
}
EOF

LAMBDA_POLICY_NAME="${PROJECT_NAME}-lambda-service-policy"
LAMBDA_POLICY_ARN=$(aws iam create-policy \
    --policy-name ${LAMBDA_POLICY_NAME} \
    --policy-document file:///tmp/lambda-service-policy.json \
    --query 'Policy.Arn' \
    --output text 2>/dev/null) || \
    LAMBDA_POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${LAMBDA_POLICY_NAME}"

aws iam attach-role-policy \
    --role-name ${LAMBDA_ROLE} \
    --policy-arn ${LAMBDA_POLICY_ARN} \
    2>/dev/null || echo -e "${GREEN}✓ Lambda service policy already attached${NC}"

# Clean up temporary files
rm -f /tmp/fantasy-draft-policy.json
rm -f /tmp/lambda-trust-policy.json
rm -f /tmp/lambda-service-policy.json

# Step 6: Create .env.aws file with configuration
echo -e "${YELLOW}Step 6: Creating .env.aws configuration file${NC}"

cat > ../.env.aws << EOF
# AWS Configuration for Fantasy Draft Assistant
# Generated: $(date)

# AWS Account
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
AWS_REGION=${AWS_REGION}

# IAM Resources
IAM_USER=${IAM_USER}
IAM_POLICY_ARN=${POLICY_ARN}
LAMBDA_EXECUTION_ROLE_ARN=arn:aws:iam::${AWS_ACCOUNT_ID}:role/${LAMBDA_ROLE}

# Project Configuration
PROJECT_NAME=${PROJECT_NAME}
STACK_NAME=${PROJECT_NAME}-stack
S3_BUCKET=${PROJECT_NAME}-${AWS_ACCOUNT_ID}

# To use these credentials:
# aws configure --profile fantasy-draft
# export AWS_PROFILE=fantasy-draft
EOF

echo -e "${GREEN}✓ Created .env.aws configuration${NC}"

# Summary
echo ""
echo -e "${GREEN}=============================================="
echo -e "✅ IAM Setup Complete!"
echo -e "=============================================="
echo -e "${NC}"
echo "Created Resources:"
echo "  📤 IAM User: ${IAM_USER}"
echo "  📋 Deployment Policy: ${POLICY_NAME}"
echo "  ⚡ Lambda Role: ${LAMBDA_ROLE}"
echo ""
echo "Next Steps:"
echo "1. Configure AWS CLI with new credentials:"
echo "   aws configure --profile fantasy-draft"
echo ""
echo "2. Use the profile for deployments:"
echo "   export AWS_PROFILE=fantasy-draft"
echo ""
echo "3. Deploy the application:"
echo "   ./deploy_with_profile.sh"
echo ""
if [ -f "fantasy-draft-credentials.txt" ]; then
    echo -e "${RED}⚠️  IMPORTANT: Save credentials from fantasy-draft-credentials.txt securely!${NC}"
fi