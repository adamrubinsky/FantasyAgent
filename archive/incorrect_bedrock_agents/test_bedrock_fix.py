#!/usr/bin/env python3
"""
Test Bedrock with correct model ID
"""

import json
import boto3
from botocore.exceptions import ClientError

def test_bedrock_models():
    """Test different Bedrock model IDs to find working one"""
    
    bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # Try different model IDs
    model_ids_to_try = [
        'anthropic.claude-3-5-sonnet-20241022-v2:0',  # Original
        'anthropic.claude-3-5-sonnet-20240620-v1:0',   # Alternative
        'anthropic.claude-3-sonnet-20240229-v1:0',     # Older version
        'anthropic.claude-3-haiku-20240307-v1:0',      # Haiku (cheaper/faster)
        'us.anthropic.claude-3-5-sonnet-20241022-v2:0', # With region prefix
    ]
    
    print("🔍 Testing Bedrock Model IDs...")
    print("=" * 50)
    
    for model_id in model_ids_to_try:
        try:
            print(f"\n🧪 Testing: {model_id}")
            
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,
                "messages": [{"role": "user", "content": "Say 'Working!' in 3 words."}]
            })
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=body
            )
            
            result = json.loads(response['body'].read())
            message = result['content'][0]['text']
            
            print(f"   ✅ SUCCESS: {message.strip()}")
            print(f"   🎯 WORKING MODEL: {model_id}")
            return model_id
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message'][:100]
            print(f"   ❌ FAILED: {error_code} - {error_msg}...")
        
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)[:100]}...")
    
    print(f"\n❌ No working model found")
    return None

def test_bedrock_list_models():
    """List available models"""
    try:
        bedrock = boto3.client('bedrock', region_name='us-east-1')
        
        print("\n🔍 Listing Available Foundation Models...")
        print("=" * 50)
        
        response = bedrock.list_foundation_models()
        
        claude_models = []
        for model in response['modelSummaries']:
            if 'claude' in model['modelId'].lower():
                claude_models.append(model)
        
        print(f"Found {len(claude_models)} Claude models:")
        for model in claude_models[:10]:  # Show first 10
            status = "✅" if model.get('modelLifecycle', {}).get('status') == 'ACTIVE' else "⏳"
            print(f"   {status} {model['modelId']}")
            if model.get('inferenceTypesSupported'):
                print(f"      └─ Inference: {model['inferenceTypesSupported']}")
        
        return claude_models
        
    except Exception as e:
        print(f"❌ Could not list models: {e}")
        return []

if __name__ == "__main__":
    print("🏈 Bedrock Model Testing for Fantasy Draft Assistant")
    print("=" * 60)
    
    # Test available models
    available_models = test_bedrock_list_models()
    
    # Test model invocation
    working_model = test_bedrock_models()
    
    if working_model:
        print(f"\n🎉 SUCCESS! Use this model ID:")
        print(f"   {working_model}")
        
        # Update the verification script
        print(f"\n📝 Next: Update your code to use: {working_model}")
    else:
        print(f"\n⚠️ No models working. Check Bedrock model access in AWS Console.")
        print(f"   Go to: Bedrock > Model access > Manage model access")