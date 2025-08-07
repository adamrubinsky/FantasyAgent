#!/bin/bash

# Amazon Bedrock AgentCore Environment Setup Script
# This script sets up the development environment for Fantasy Football Draft Assistant

set -e  # Exit on error

echo "🚀 Setting up Amazon Bedrock AgentCore Development Environment"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    echo -e "${GREEN}✓ Python $python_version meets requirements${NC}"
else
    echo -e "${RED}✗ Python $python_version is too old. Please install Python 3.10+${NC}"
    exit 1
fi

# Check AWS CLI
echo -e "${YELLOW}Checking AWS CLI...${NC}"
if command -v aws &> /dev/null; then
    aws_account=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ AWS CLI configured (Account: $aws_account)${NC}"
    else
        echo -e "${RED}✗ AWS CLI not configured. Run 'aws configure'${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ AWS CLI not installed${NC}"
    exit 1
fi

# Check AWS region
AWS_REGION=$(aws configure get region)
echo -e "${GREEN}✓ AWS Region: $AWS_REGION${NC}"

# Check Bedrock availability in region
echo -e "${YELLOW}Checking Amazon Bedrock availability...${NC}"
bedrock_check=$(aws bedrock list-foundation-models --region $AWS_REGION 2>&1)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Amazon Bedrock is available in $AWS_REGION${NC}"
else
    echo -e "${RED}✗ Amazon Bedrock might not be available in $AWS_REGION${NC}"
    echo "  Consider using us-east-1 or us-west-2"
fi

# Create virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
cd "$(dirname "$0")/.."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install requirements
echo -e "${YELLOW}Installing Python requirements...${NC}"
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓ Requirements installed${NC}"

# Create .env file if it doesn't exist
if [ ! -f "../.env.bedrock" ]; then
    echo -e "${YELLOW}Creating .env.bedrock file...${NC}"
    cat > ../.env.bedrock << EOF
# Amazon Bedrock AgentCore Configuration
AWS_REGION=$AWS_REGION
AWS_ACCOUNT_ID=$aws_account

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_AGENT_ALIAS=fantasy-draft-assistant
BEDROCK_KNOWLEDGE_BASE_ID=

# Agent Runtime Configuration
AGENT_RUNTIME_ROLE_ARN=
AGENT_EXECUTION_ROLE_ARN=

# Memory Configuration
MEMORY_TYPE=dynamodb
MEMORY_TABLE_NAME=fantasy-draft-memory

# Gateway Configuration
GATEWAY_ENDPOINT=
API_GATEWAY_ID=

# Existing API Keys (migrate from .env.local)
ANTHROPIC_API_KEY=
FANTASYPROS_API_KEY=
SLEEPER_USERNAME=
SLEEPER_LEAGUE_ID=

# Monitoring
ENABLE_XRAY=true
ENABLE_CLOUDWATCH=true
LOG_LEVEL=INFO
EOF
    echo -e "${GREEN}✓ Created .env.bedrock template${NC}"
    echo -e "${YELLOW}  Please update .env.bedrock with your API keys${NC}"
else
    echo -e "${GREEN}✓ .env.bedrock already exists${NC}"
fi

# Copy existing environment variables if available
if [ -f "../.env.local" ]; then
    echo -e "${YELLOW}Migrating API keys from .env.local...${NC}"
    # Extract and update specific keys
    for key in ANTHROPIC_API_KEY FANTASYPROS_API_KEY SLEEPER_USERNAME SLEEPER_LEAGUE_ID; do
        value=$(grep "^$key=" ../.env.local | cut -d'=' -f2-)
        if [ ! -z "$value" ]; then
            sed -i.bak "s|^$key=.*|$key=$value|" ../.env.bedrock
        fi
    done
    echo -e "${GREEN}✓ API keys migrated${NC}"
fi

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ Bedrock AgentCore environment setup complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source bedrock-agentcore/venv/bin/activate"
echo "2. Update .env.bedrock with any missing API keys"
echo "3. Run the IAM setup script: ./scripts/setup_iam.sh"
echo "4. Deploy the infrastructure: ./scripts/deploy_infrastructure.sh"
echo ""