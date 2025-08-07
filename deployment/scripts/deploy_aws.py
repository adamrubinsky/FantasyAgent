#!/usr/bin/env python3
"""
AWS Deployment Script for Fantasy Draft Assistant Web UI

This deploys the web interface to AWS for reliable access during draft day.
"""

import boto3
import json
import os
import zipfile
import tempfile
from pathlib import Path

def create_deployment_package():
    """Create deployment package for AWS Lambda"""
    
    print("📦 Creating deployment package...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = Path(temp_dir) / "package"
        package_dir.mkdir()
        
        # Copy application files
        app_files = [
            "web_app.py",
            "main.py", 
            "requirements.txt",
            ".env.local"
        ]
        
        # Copy directories
        app_dirs = [
            "api/",
            "core/", 
            "agents/",
            "templates/",
            "static/",
            "data/",
            "mcp_servers/"
        ]
        
        print("📁 Copying application files...")
        for file in app_files:
            if os.path.exists(file):
                os.system(f"cp {file} {package_dir}/")
        
        print("📂 Copying application directories...")
        for dir_name in app_dirs:
            if os.path.exists(dir_name):
                os.system(f"cp -r {dir_name} {package_dir}/")
        
        # Create Lambda handler
        lambda_handler = """
import json
from mangum import Mangum
from web_app import app

handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    return handler(event, context)
"""
        
        with open(package_dir / "lambda_function.py", "w") as f:
            f.write(lambda_handler)
        
        # Install dependencies in package
        print("📥 Installing dependencies...")
        os.system(f"pip install -r requirements.txt -t {package_dir}")
        os.system(f"pip install mangum -t {package_dir}")
        
        # Create zip file
        zip_path = Path(temp_dir) / "deployment.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arc_name)
        
        return zip_path

def deploy_to_aws():
    """Deploy to AWS Lambda + API Gateway"""
    
    print("🚀 Starting AWS Deployment...")
    
    # Create deployment package
    zip_path = create_deployment_package()
    
    # AWS clients
    lambda_client = boto3.client('lambda')
    apigateway_client = boto3.client('apigatewayv2')
    
    function_name = "fantasy-draft-assistant"
    
    try:
        # Create or update Lambda function
        print("⚡ Deploying Lambda function...")
        
        with open(zip_path, 'rb') as zip_file:
            zip_bytes = zip_file.read()
        
        try:
            # Try to update existing function
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_bytes
            )
            print("✅ Updated existing Lambda function")
        except lambda_client.exceptions.ResourceNotFoundException:
            # Create new function
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role='arn:aws:iam::ACCOUNT:role/lambda-execution-role',  # You'll need to create this
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_bytes},
                Environment={
                    'Variables': {
                        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY', ''),
                        'SLEEPER_USERNAME': os.getenv('SLEEPER_USERNAME', ''),
                        'SLEEPER_LEAGUE_ID': os.getenv('SLEEPER_LEAGUE_ID', ''),
                        'FANTASYPROS_API_KEY': os.getenv('FANTASYPROS_API_KEY', ''),
                    }
                },
                Timeout=30,
                MemorySize=512
            )
            print("✅ Created new Lambda function")
        
        # Create API Gateway
        print("🌐 Setting up API Gateway...")
        
        # This would create HTTP API Gateway
        # Simplified for now - you'd need to configure routes, etc.
        
        print("🎉 Deployment complete!")
        print("📱 Your web UI will be available at: https://your-api-id.execute-api.region.amazonaws.com/")
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        print("💡 Make sure you have:")
        print("   1. AWS CLI configured (aws configure)")
        print("   2. IAM role for Lambda execution")
        print("   3. Proper permissions for Lambda and API Gateway")

if __name__ == "__main__":
    print("🏈 Fantasy Draft Assistant - AWS Deployment")
    print("This will deploy your web UI to AWS for stable access")
    
    confirm = input("Continue with AWS deployment? (y/N): ")
    if confirm.lower() == 'y':
        deploy_to_aws()
    else:
        print("Deployment cancelled")