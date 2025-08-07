#!/usr/bin/env python3
"""
Deploy AgentCore agents with proper service role
"""

import boto3
import json
import time
from botocore.exceptions import ClientError

class AgentCoreRoleDeployer:
    def __init__(self, region_name: str = 'us-east-1'):
        self.region_name = region_name
        self.agent_client = boto3.client('bedrock-agent', region_name=region_name)
        self.runtime_client = boto3.client('bedrock-agent-runtime', region_name=region_name)
        self.foundation_model = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
        
        # Load service role
        try:
            with open('agentcore_role.json', 'r') as f:
                role_info = json.load(f)
                self.service_role_arn = role_info['role_arn']
                print(f"🔑 Using service role: {self.service_role_arn}")
        except FileNotFoundError:
            raise FileNotFoundError("Service role not found. Run create_agentcore_service_role.py first.")
        
    def delete_existing_agents(self):
        """Clean up existing agents first"""
        try:
            print("🧹 Cleaning up existing agents...")
            
            response = self.agent_client.list_agents()
            agents_to_delete = []
            
            for agent in response.get('agentSummaries', []):
                if agent['agentName'].startswith('fantasy-'):
                    agents_to_delete.append((agent['agentId'], agent['agentName']))
            
            for agent_id, agent_name in agents_to_delete:
                try:
                    print(f"🗑️ Deleting {agent_name}...")
                    self.agent_client.delete_agent(agentId=agent_id)
                    print(f"✅ Deleted {agent_name}")
                except ClientError as e:
                    print(f"⚠️ Could not delete {agent_name}: {e}")
                    
            if agents_to_delete:
                print("⏳ Waiting for deletions to complete...")
                time.sleep(30)
            
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")
    
    def create_data_collector(self) -> str:
        """Create the data collector agent"""
        
        print("🏗️ Creating Data Collector Agent...")
        
        try:
            response = self.agent_client.create_agent(
                agentName='fantasy-data-collector',
                description='Collects fantasy football data from multiple sources',
                foundationModel=self.foundation_model,
                agentResourceRoleArn=self.service_role_arn,  # KEY: Add the service role
                instruction='''You are a Fantasy Football Data Collector. Gather player rankings, 
ADP data, injury reports, and news from available sources. Return structured data.'''
            )
            
            agent_id = response['agent']['agentId']
            print(f"✅ Data Collector created: {agent_id}")
            return agent_id
            
        except ClientError as e:
            print(f"❌ Failed to create Data Collector: {e}")
            return None
    
    def prepare_agent(self, agent_id: str, agent_name: str) -> bool:
        """Prepare agent for use"""
        try:
            # First wait for agent to finish creating
            print(f"⏳ Waiting for {agent_name} to finish creating...")
            
            max_wait = 300  # 5 minutes
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                response = self.agent_client.get_agent(agentId=agent_id)
                status = response['agent']['agentStatus']
                
                print(f"⏳ {agent_name} status: {status}")
                
                if status == 'NOT_PREPARED':
                    print(f"✅ {agent_name} finished creating, now preparing...")
                    break
                elif status in ['FAILED', 'DELETING']:
                    print(f"❌ {agent_name} creation failed with status: {status}")
                    return False
                
                time.sleep(20)
            else:
                print(f"⚠️ {agent_name} creation timed out")
                return False
            
            # Now prepare the agent
            print(f"🔧 Preparing {agent_name}...")
            self.agent_client.prepare_agent(agentId=agent_id)
            
            # Wait for preparation to complete
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                response = self.agent_client.get_agent(agentId=agent_id)
                status = response['agent']['agentStatus']
                
                print(f"⏳ {agent_name} preparation status: {status}")
                
                if status == 'PREPARED':
                    print(f"✅ {agent_name} is ready!")
                    return True
                elif status in ['FAILED']:
                    print(f"❌ {agent_name} preparation failed")
                    return False
                
                time.sleep(30)
            
            print(f"⚠️ {agent_name} preparation timed out")
            return False
            
        except ClientError as e:
            print(f"❌ Error preparing {agent_name}: {e}")
            return False
    
    def create_simple_test_agent(self):
        """Create a single test agent to verify the setup"""
        
        print("🚀 CREATING SIMPLE TEST AGENT")
        print("=" * 40)
        
        # Clean up first
        self.delete_existing_agents()
        
        # Create one agent
        agent_id = self.create_data_collector()
        
        if not agent_id:
            print("❌ Failed to create agent")
            return
        
        # Prepare it
        if self.prepare_agent(agent_id, 'data-collector'):
            # Create alias
            try:
                alias_response = self.agent_client.create_agent_alias(
                    agentId=agent_id,
                    agentAliasName='data-collector-live',
                    description='Live alias for data collector'
                )
                
                alias_id = alias_response['agentAlias']['agentAliasId']
                print(f"✅ Alias created: {alias_id}")
                
                # Test invocation
                print("🧪 Testing agent invocation...")
                
                response = self.runtime_client.invoke_agent(
                    agentId=agent_id,
                    agentAliasId=alias_id,
                    sessionId=f"test-{int(time.time())}",
                    inputText="Hello, provide a brief test response."
                )
                
                # Process response
                full_response = ""
                for event in response['completion']:
                    if 'chunk' in event and 'bytes' in event['chunk']:
                        chunk_text = event['chunk']['bytes'].decode('utf-8')
                        full_response += chunk_text
                        print(chunk_text, end='', flush=True)
                
                print(f"\n🎉 SUCCESS! Agent responded correctly.")
                
                # Save deployment info
                deployment = {
                    'agent_ids': {'data-collector': agent_id},
                    'aliases': {'data-collector': alias_id},
                    'service_role_arn': self.service_role_arn,
                    'region': self.region_name,
                    'deployment_time': time.time()
                }
                
                with open('agentcore_deployment.json', 'w') as f:
                    json.dump(deployment, f, indent=2)
                
                print(f"💾 Deployment saved to agentcore_deployment.json")
                
            except ClientError as e:
                print(f"❌ Failed to create alias or test: {e}")
        else:
            print("❌ Agent preparation failed")

def main():
    try:
        deployer = AgentCoreRoleDeployer()
        deployer.create_simple_test_agent()
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        print("📋 Manual steps needed:")
        print("1. Attach AmazonBedrockFullAccess to the fantasy-draft-agentcore-role")
        print("2. Or ask your AWS admin to add required policies")

if __name__ == "__main__":
    main()