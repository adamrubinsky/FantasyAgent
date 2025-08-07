#!/usr/bin/env python3
"""
AWS AgentCore Deployment - Using Direct Anthropic API
No Bedrock required! Uses AgentCore patterns with Lambda + API Gateway
"""

import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
import boto3
from typing import Dict, Any

class AgentCoreDeployer:
    """Deploy Fantasy Draft Assistant using AgentCore patterns on AWS"""
    
    def __init__(self):
        self.aws_account = boto3.client('sts').get_caller_identity()['Account']
        self.region = boto3.Session().region_name or 'us-east-1'
        self.stack_name = 'fantasy-draft-agentcore'
        self.bucket_name = f'fantasy-draft-{self.aws_account}'
        
    def deploy(self):
        """Main deployment process"""
        print("🚀 Deploying Fantasy Draft Assistant with AgentCore Architecture")
        print("=" * 60)
        print(f"Account: {self.aws_account}")
        print(f"Region: {self.region}")
        print("Using: Direct Anthropic API (No Bedrock needed!)")
        print("=" * 60)
        
        # Step 1: Package Lambda functions
        print("\n📦 Step 1: Packaging Lambda functions...")
        lambda_package = self.create_lambda_package()
        
        # Step 2: Create CloudFormation template
        print("\n📝 Step 2: Creating infrastructure template...")
        template = self.create_cloudformation_template()
        
        # Step 3: Deploy to AWS
        print("\n☁️ Step 3: Deploying to AWS...")
        result = self.deploy_stack(template, lambda_package)
        
        print("\n✅ Deployment Complete!")
        print("=" * 60)
        print(f"🌐 Web UI: {result['WebUrl']}")
        print(f"🔌 WebSocket: {result['WebSocketUrl']}")
        print(f"📡 API Endpoint: {result['ApiUrl']}")
        
        return result
    
    def create_lambda_package(self) -> str:
        """Package Lambda functions with AgentCore pattern"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir) / "package"
            package_dir.mkdir()
            
            # Create main Lambda handler with AgentCore orchestration
            handler_code = '''
import json
import os
from typing import Dict, Any
from anthropic import Anthropic
import asyncio

# AgentCore Pattern - Multi-Agent Orchestrator
class AgentCoreOrchestrator:
    """Implements AgentCore pattern with direct Anthropic API"""
    
    def __init__(self):
        self.client = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
        self.agents = self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize specialized agents using AgentCore pattern"""
        return {
            "data_collector": DataCollectorAgent(self.client),
            "analyst": AnalystAgent(self.client),
            "strategist": StrategyAgent(self.client),
            "advisor": AdvisorAgent(self.client)
        }
    
    async def process_request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through agent pipeline"""
        
        # AgentCore pattern: Sequential agent processing
        context = {"request": event}
        
        # Step 1: Data Collection
        context = await self.agents["data_collector"].process(context)
        
        # Step 2: Analysis
        context = await self.agents["analyst"].process(context)
        
        # Step 3: Strategy
        context = await self.agents["strategist"].process(context)
        
        # Step 4: Final Recommendation
        result = await self.agents["advisor"].process(context)
        
        return result

class BaseAgent:
    """Base agent following AgentCore pattern"""
    
    def __init__(self, client: Anthropic):
        self.client = client
        
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process context through agent"""
        # Agent-specific logic here
        return context

class DataCollectorAgent(BaseAgent):
    """Collects data from various sources"""
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Implement data collection logic
        context["data"] = {"players": [], "rankings": []}
        return context

class AnalystAgent(BaseAgent):
    """Analyzes collected data"""
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Implement analysis logic
        context["analysis"] = {"insights": []}
        return context

class StrategyAgent(BaseAgent):
    """Develops strategy based on analysis"""
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Implement strategy logic
        context["strategy"] = {"recommendations": []}
        return context

class AdvisorAgent(BaseAgent):
    """Provides final recommendations"""
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Use Anthropic API for final recommendation
        prompt = f"Based on this context, provide draft advice: {json.dumps(context)}"
        
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return {
            "recommendation": response.content[0].text,
            "context": context
        }

# Lambda Handler
orchestrator = AgentCoreOrchestrator()

def lambda_handler(event, context):
    """AWS Lambda entry point"""
    
    # Handle different event types
    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        }
    
    # Process through AgentCore orchestrator
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(orchestrator.process_request(event))
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(result)
    }
'''
            
            # Write handler
            (package_dir / "lambda_function.py").write_text(handler_code)
            
            # Copy necessary files
            files_to_copy = [
                "web_app.py",
                "main.py",
                ".env.local"
            ]
            
            dirs_to_copy = [
                "api",
                "core", 
                "agents",
                "templates",
                "static"
            ]
            
            for file in files_to_copy:
                if Path(file).exists():
                    shutil.copy(file, package_dir)
            
            for dir_name in dirs_to_copy:
                if Path(dir_name).exists():
                    shutil.copytree(dir_name, package_dir / dir_name)
            
            # Create requirements
            requirements = """
anthropic>=0.25.0
boto3>=1.34.0
fastapi>=0.110.0
mangum>=0.17.0
websockets>=12.0
httpx>=0.26.0
python-dotenv>=1.0.0
aiofiles>=23.2.0
"""
            (package_dir / "requirements.txt").write_text(requirements)
            
            # Install dependencies
            subprocess.run([
                "pip", "install", "-r", "requirements.txt",
                "-t", str(package_dir),
                "--platform", "manylinux2014_x86_64",
                "--only-binary", ":all:",
                "--quiet"
            ], cwd=package_dir)
            
            # Create zip
            zip_path = Path(temp_dir) / "lambda-package.zip"
            shutil.make_archive(str(zip_path.with_suffix('')), 'zip', package_dir)
            
            # Upload to S3
            s3 = boto3.client('s3')
            s3.create_bucket(Bucket=self.bucket_name, CreateBucketConfiguration={'LocationConstraint': self.region})
            s3.upload_file(str(zip_path), self.bucket_name, "lambda-package.zip")
            
            return f"s3://{self.bucket_name}/lambda-package.zip"
    
    def create_cloudformation_template(self) -> Dict[str, Any]:
        """Create CloudFormation template with AgentCore architecture"""
        
        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "Fantasy Draft Assistant - AgentCore Architecture (No Bedrock)",
            
            "Parameters": {
                "AnthropicApiKey": {
                    "Type": "String",
                    "NoEcho": True,
                    "Description": "Direct Anthropic API Key"
                }
            },
            
            "Resources": {
                # Lambda Function for AgentCore
                "AgentCoreFunction": {
                    "Type": "AWS::Lambda::Function",
                    "Properties": {
                        "FunctionName": "fantasy-draft-agentcore",
                        "Runtime": "python3.11",
                        "Handler": "lambda_function.lambda_handler",
                        "Code": {
                            "S3Bucket": self.bucket_name,
                            "S3Key": "lambda-package.zip"
                        },
                        "MemorySize": 1024,
                        "Timeout": 30,
                        "Environment": {
                            "Variables": {
                                "ANTHROPIC_API_KEY": {"Ref": "AnthropicApiKey"}
                            }
                        },
                        "Role": {"Fn::GetAtt": ["LambdaRole", "Arn"]}
                    }
                },
                
                # IAM Role
                "LambdaRole": {
                    "Type": "AWS::IAM::Role",
                    "Properties": {
                        "AssumeRolePolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [{
                                "Effect": "Allow",
                                "Principal": {"Service": "lambda.amazonaws.com"},
                                "Action": "sts:AssumeRole"
                            }]
                        },
                        "ManagedPolicyArns": [
                            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                        ]
                    }
                },
                
                # API Gateway for REST
                "ApiGateway": {
                    "Type": "AWS::ApiGatewayV2::Api",
                    "Properties": {
                        "Name": "fantasy-draft-agentcore-api",
                        "ProtocolType": "HTTP",
                        "CorsConfiguration": {
                            "AllowOrigins": ["*"],
                            "AllowMethods": ["GET", "POST", "OPTIONS"],
                            "AllowHeaders": ["*"]
                        }
                    }
                },
                
                # WebSocket API
                "WebSocketApi": {
                    "Type": "AWS::ApiGatewayV2::Api",
                    "Properties": {
                        "Name": "fantasy-draft-agentcore-ws",
                        "ProtocolType": "WEBSOCKET",
                        "RouteSelectionExpression": "$request.body.action"
                    }
                },
                
                # DynamoDB for state
                "StateTable": {
                    "Type": "AWS::DynamoDB::Table",
                    "Properties": {
                        "TableName": "fantasy-draft-agentcore-state",
                        "BillingMode": "PAY_PER_REQUEST",
                        "AttributeDefinitions": [
                            {"AttributeName": "id", "AttributeType": "S"}
                        ],
                        "KeySchema": [
                            {"AttributeName": "id", "KeyType": "HASH"}
                        ]
                    }
                }
            },
            
            "Outputs": {
                "WebUrl": {
                    "Value": {"Fn::Sub": "https://${ApiGateway}.execute-api.${AWS::Region}.amazonaws.com/prod"}
                },
                "WebSocketUrl": {
                    "Value": {"Fn::Sub": "wss://${WebSocketApi}.execute-api.${AWS::Region}.amazonaws.com/prod"}
                },
                "ApiUrl": {
                    "Value": {"Fn::Sub": "https://${ApiGateway}.execute-api.${AWS::Region}.amazonaws.com/prod/api"}
                }
            }
        }
        
        return template
    
    def deploy_stack(self, template: Dict[str, Any], lambda_package: str) -> Dict[str, Any]:
        """Deploy CloudFormation stack"""
        
        cf = boto3.client('cloudformation')
        
        # Get API key from environment
        api_key = os.getenv('ANTHROPIC_API_KEY', '')
        
        # Deploy stack
        cf.create_stack(
            StackName=self.stack_name,
            TemplateBody=json.dumps(template),
            Parameters=[
                {"ParameterKey": "AnthropicApiKey", "ParameterValue": api_key}
            ],
            Capabilities=['CAPABILITY_IAM']
        )
        
        # Wait for completion
        waiter = cf.get_waiter('stack_create_complete')
        waiter.wait(StackName=self.stack_name)
        
        # Get outputs
        stack = cf.describe_stacks(StackName=self.stack_name)['Stacks'][0]
        outputs = {o['OutputKey']: o['OutputValue'] for o in stack.get('Outputs', [])}
        
        return outputs


if __name__ == "__main__":
    deployer = AgentCoreDeployer()
    deployer.deploy()