#!/usr/bin/env python3
"""
Verify Amazon Bedrock is enabled and accessible
"""

import boto3
import json
from botocore.exceptions import ClientError

def verify_bedrock():
    """Check Bedrock access and available models"""
    
    print("🔍 Verifying Amazon Bedrock Access")
    print("=" * 50)
    
    # Initialize Bedrock client
    bedrock = boto3.client('bedrock', region_name='us-east-1')
    
    try:
        # Step 1: Check if we can list models
        print("\n1️⃣ Checking Bedrock API access...")
        response = bedrock.list_foundation_models()
        print("✅ Bedrock API is accessible!")
        
        # Step 2: List available Claude models
        print("\n2️⃣ Available Claude models:")
        claude_models = []
        for model in response['modelSummaries']:
            if 'claude' in model['modelId'].lower():
                claude_models.append(model)
                status = "✅" if model.get('modelLifecycle', {}).get('status') == 'ACTIVE' else "⏳"
                print(f"   {status} {model['modelId']}")
                print(f"      Provider: {model['providerName']}")
                print(f"      Name: {model['modelName']}")
                print()
        
        if not claude_models:
            print("   ⚠️ No Claude models found. Please enable them in the console.")
            return False
            
        # Step 3: Test model invocation
        print("3️⃣ Testing model invocation...")
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Try to invoke Claude 3.5 Sonnet
        test_model = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
        
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": "Say 'Hello, Bedrock is working!' in 5 words or less."
                    }
                ]
            })
            
            response = bedrock_runtime.invoke_model(
                modelId=test_model,
                body=body,
                contentType='application/json',
                accept='application/json'
            )
            
            result = json.loads(response['body'].read())
            message = result['content'][0]['text']
            print(f"✅ Model invocation successful!")
            print(f"   Response: {message}")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                print(f"⚠️ Model {test_model} not found. Trying alternate...")
                # Try alternate model ID
                test_model = 'anthropic.claude-3-sonnet-20240229-v1:0'
                try:
                    response = bedrock_runtime.invoke_model(
                        modelId=test_model,
                        body=body,
                        contentType='application/json',
                        accept='application/json'
                    )
                    print(f"✅ Alternate model {test_model} works!")
                except:
                    print(f"❌ Model invocation failed. Model may not be enabled.")
                    print(f"   Please enable Claude models in the AWS Console.")
            elif error_code == 'AccessDeniedException':
                print(f"❌ Access denied. Please enable the model in AWS Console.")
            else:
                print(f"❌ Error: {error_code}")
                
        # Step 4: Check IAM permissions
        print("\n4️⃣ Checking IAM permissions...")
        iam = boto3.client('iam')
        sts = boto3.client('sts')
        
        identity = sts.get_caller_identity()
        print(f"   Current user: {identity['Arn']}")
        
        # Summary
        print("\n" + "=" * 50)
        if claude_models:
            print("✅ BEDROCK IS READY!")
            print(f"   Found {len(claude_models)} Claude models")
            print("\n📝 Next steps:")
            print("   1. Run: ./scripts/setup_iam.sh")
            print("   2. Run: python bedrock-agentcore/agents/recommendation_agent.py")
            return True
        else:
            print("⚠️ BEDROCK NEEDS SETUP")
            print("\n📝 Action required:")
            print("   1. Go to AWS Console > Bedrock > Model access")
            print("   2. Enable Anthropic Claude models")
            print("   3. Run this script again")
            return False
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDeniedException':
            print("❌ Access Denied!")
            print("\n📝 To fix this:")
            print("   1. Go to AWS IAM Console")
            print("   2. Add this policy to your user:")
            print("""
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:*"
            ],
            "Resource": "*"
        }
    ]
}
            """)
        else:
            print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    verify_bedrock()