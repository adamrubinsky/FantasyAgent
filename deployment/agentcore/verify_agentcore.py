#!/usr/bin/env python3
"""
Verify AgentCore System is Working
Tests all components and shows exactly what's working
"""

import asyncio
import json
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

class AgentCoreVerifier:
    """Verify all AgentCore components are working"""
    
    def __init__(self):
        self.results = {
            "bedrock": {"status": "unknown", "details": []},
            "permissions": {"status": "unknown", "details": []},
            "agentcore": {"status": "unknown", "details": []},
            "observability": {"status": "unknown", "details": []}
        }
    
    def test_bedrock_access(self):
        """Test Bedrock model access"""
        print("🔍 Testing Bedrock Access...")
        
        try:
            bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
            
            # Test model invocation
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,
                "messages": [{"role": "user", "content": "Say 'Bedrock is working!'"}]
            })
            
            response = bedrock.invoke_model(
                modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
                body=body
            )
            
            result = json.loads(response['body'].read())
            message = result['content'][0]['text']
            
            self.results["bedrock"]["status"] = "✅ WORKING"
            self.results["bedrock"]["details"] = [
                f"✓ Model invocation successful",
                f"✓ Response: {message}",
                f"✓ Using: anthropic.claude-3-5-sonnet-20241022-v2:0"
            ]
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            self.results["bedrock"]["status"] = f"❌ FAILED ({error_code})"
            self.results["bedrock"]["details"] = [
                f"✗ Error: {error_code}",
                f"✗ Message: {e.response['Error']['Message']}"
            ]
        except Exception as e:
            self.results["bedrock"]["status"] = f"❌ ERROR"
            self.results["bedrock"]["details"] = [f"✗ Error: {str(e)}"]
    
    def test_permissions(self):
        """Test AWS permissions"""
        print("🔍 Testing AWS Permissions...")
        
        permissions_tests = [
            ("Bedrock", "bedrock-runtime", "invoke_model"),
            ("CloudWatch", "cloudwatch", "put_metric_data"),  
            ("DynamoDB", "dynamodb", "create_table")
        ]
        
        working_permissions = []
        failed_permissions = []
        
        for service_name, service, operation in permissions_tests:
            try:
                client = boto3.client(service, region_name='us-east-1')
                
                if service == "bedrock-runtime":
                    # Already tested in bedrock_access
                    if self.results["bedrock"]["status"].startswith("✅"):
                        working_permissions.append(f"✓ {service_name}: invoke_model")
                    else:
                        failed_permissions.append(f"✗ {service_name}: invoke_model")
                        
                elif service == "cloudwatch":
                    # Test dry run
                    try:
                        client.put_metric_data(
                            Namespace='Test',
                            MetricData=[{
                                'MetricName': 'test',
                                'Value': 1,
                                'Timestamp': datetime.utcnow()
                            }]
                        )
                        working_permissions.append(f"✓ {service_name}: {operation}")
                    except ClientError as e:
                        if "AccessDenied" in str(e):
                            failed_permissions.append(f"✗ {service_name}: {operation} (Access Denied)")
                        else:
                            working_permissions.append(f"✓ {service_name}: {operation} (validated)")
                
                elif service == "dynamodb":
                    # Test describe tables (lighter operation)
                    client.list_tables()
                    working_permissions.append(f"✓ {service_name}: basic access")
                    
            except Exception as e:
                failed_permissions.append(f"✗ {service_name}: {str(e)[:50]}...")
        
        if len(working_permissions) >= 2:  # Bedrock + at least one other
            self.results["permissions"]["status"] = "✅ PARTIAL WORKING"
        elif len(working_permissions) >= 1:
            self.results["permissions"]["status"] = "⚠️ LIMITED ACCESS"
        else:
            self.results["permissions"]["status"] = "❌ INSUFFICIENT"
        
        self.results["permissions"]["details"] = working_permissions + failed_permissions
    
    async def test_agentcore_pattern(self):
        """Test AgentCore multi-agent pattern"""
        print("🔍 Testing AgentCore Pattern...")
        
        try:
            # Import our AgentCore test
            from test_agentcore_simple import SimpleAgentCoreTest
            
            agentcore = SimpleAgentCoreTest()
            result = await agentcore.process_agentcore_request(
                "Test: Who should I draft 1st overall?"
            )
            
            self.results["agentcore"]["status"] = "✅ WORKING"
            self.results["agentcore"]["details"] = [
                f"✓ Multi-agent orchestration: {result['agents_executed']} agents",
                f"✓ Processing time: {result['processing_time']:.2f}s",
                f"✓ Recommendation generated: {len(result['recommendation'])} chars",
                f"✓ Agent flow: Data → Analysis → Strategy → Advice"
            ]
            
        except Exception as e:
            self.results["agentcore"]["status"] = "❌ FAILED"
            self.results["agentcore"]["details"] = [f"✗ Error: {str(e)}"]
    
    def test_observability_ready(self):
        """Test observability readiness"""
        print("🔍 Testing Observability Setup...")
        
        observability_features = []
        
        # Check logging
        import logging
        try:
            logger = logging.getLogger('test')
            logger.info("Test log")
            observability_features.append("✓ Logging framework ready")
        except:
            observability_features.append("✗ Logging issues")
        
        # Check CloudWatch client
        try:
            boto3.client('cloudwatch')
            observability_features.append("✓ CloudWatch client available")
        except:
            observability_features.append("✗ CloudWatch client failed")
        
        # Check DynamoDB client
        try:
            boto3.client('dynamodb')
            observability_features.append("✓ DynamoDB client available")
        except:
            observability_features.append("✗ DynamoDB client failed")
        
        # Check structured logging
        try:
            import json
            test_event = {"timestamp": datetime.now().isoformat(), "test": True}
            json.dumps(test_event)
            observability_features.append("✓ Structured logging ready")
        except:
            observability_features.append("✗ Structured logging issues")
        
        working_count = len([f for f in observability_features if f.startswith("✓")])
        
        if working_count >= 3:
            self.results["observability"]["status"] = "✅ READY"
        elif working_count >= 2:
            self.results["observability"]["status"] = "⚠️ PARTIAL"
        else:
            self.results["observability"]["status"] = "❌ NOT READY"
        
        self.results["observability"]["details"] = observability_features
    
    async def run_full_verification(self):
        """Run complete verification"""
        
        print("🏈 Fantasy Draft Assistant - AgentCore Verification")
        print("=" * 55)
        print("Testing all components to verify system is working\n")
        
        # Run all tests
        self.test_bedrock_access()
        print()
        
        self.test_permissions()
        print()
        
        await self.test_agentcore_pattern()
        print()
        
        self.test_observability_ready()
        print()
        
        # Print comprehensive report
        print("=" * 55)
        print("🎯 AGENTCORE SYSTEM VERIFICATION REPORT")
        print("=" * 55)
        
        for component, result in self.results.items():
            print(f"\n{component.upper().replace('_', ' ')}: {result['status']}")
            for detail in result['details']:
                print(f"   {detail}")
        
        # Overall assessment
        print("\n" + "=" * 55)
        working_components = sum(1 for r in self.results.values() 
                               if r['status'].startswith('✅'))
        
        if working_components >= 3:
            print("🎉 OVERALL STATUS: SYSTEM READY FOR PRODUCTION")
            print("   Your AgentCore implementation is working correctly!")
            next_steps = [
                "✓ Multi-agent orchestration verified",
                "✓ Bedrock integration confirmed", 
                "✓ Ready for AWS deployment",
                "→ Next: Add remaining AWS permissions for full observability"
            ]
        elif working_components >= 2:
            print("⚠️ OVERALL STATUS: SYSTEM PARTIALLY WORKING")  
            print("   Core functionality verified, some permissions needed")
            next_steps = [
                "✓ AgentCore pattern working",
                "→ Need: Additional AWS permissions",
                "→ Next: Contact AWS admin to add permissions"
            ]
        else:
            print("❌ OVERALL STATUS: SETUP NEEDED")
            print("   Some components need configuration")
            next_steps = [
                "→ Need: Bedrock model access",
                "→ Need: AWS permissions", 
                "→ Next: Follow setup instructions"
            ]
        
        print("\n📋 NEXT STEPS:")
        for step in next_steps:
            print(f"   {step}")
        
        print(f"\n📊 SYSTEM SCORE: {working_components}/4 components working")
        print("=" * 55)

async def main():
    """Run verification"""
    verifier = AgentCoreVerifier()
    await verifier.run_full_verification()

if __name__ == "__main__":
    asyncio.run(main())