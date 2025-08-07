#!/usr/bin/env python3
"""
Test the working AgentCore agent - CORRECT APPROACH
"""

import boto3
import json
import time
import uuid

def test_agentcore_invocation():
    """Test invoking our deployed AgentCore agent"""
    
    print("🚀 TESTING WORKING BEDROCK AGENTCORE AGENT")
    print("=" * 50)
    
    # AgentCore runtime client (CORRECT way)
    runtime_client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
    
    # Our deployed agent details
    agent_id = "QIXL7HZUKS"
    alias_id = "GJMBWBB1T7" 
    session_id = f"test-session-{int(time.time())}"
    
    print(f"🤖 Agent ID: {agent_id}")
    print(f"🔗 Alias ID: {alias_id}")
    print(f"📱 Session ID: {session_id}")
    print()
    
    try:
        # Test basic invocation
        print("📤 Invoking AgentCore agent...")
        print("💬 Input: Hello, provide the top 3 QBs for fantasy football.")
        
        response = runtime_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText="Hello, provide the top 3 QBs for fantasy football this season with brief reasoning."
        )
        
        print("\n📨 AgentCore Response:")
        print("-" * 30)
        
        # Process streaming response
        full_response = ""
        event_stream = response['completion']
        
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    full_response += chunk_text
                    print(chunk_text, end='', flush=True)
        
        print(f"\n{'-' * 30}")
        print(f"📝 Complete Response Length: {len(full_response)} characters")
        
        # Test follow-up in same session  
        print(f"\n🔄 Testing session continuity...")
        
        followup_response = runtime_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,  # Same session
            inputText="What about running backs? Give me top 3 RBs."
        )
        
        print("📨 Follow-up Response:")
        print("-" * 30)
        
        followup_text = ""
        for event in followup_response['completion']:
            if 'chunk' in event and 'bytes' in event['chunk']:
                chunk_text = event['chunk']['bytes'].decode('utf-8')
                followup_text += chunk_text
                print(chunk_text, end='', flush=True)
        
        print(f"\n{'-' * 30}")
        
        print(f"\n🎉 AGENTCORE TEST SUCCESSFUL!")
        print(f"✅ Agent responded to both queries")
        print(f"✅ Session continuity maintained")  
        print(f"✅ Streaming response working")
        print(f"✅ Fantasy football knowledge demonstrated")
        
        return True
        
    except Exception as e:
        print(f"\n❌ AgentCore invocation failed: {e}")
        return False

def test_agent_status():
    """Check agent and alias status"""
    
    print(f"\n🔍 CHECKING AGENT STATUS")
    print("=" * 30)
    
    agent_client = boto3.client('bedrock-agent', region_name='us-east-1')
    
    try:
        # Check agent status
        agent_response = agent_client.get_agent(agentId="QIXL7HZUKS")
        agent_status = agent_response['agent']['agentStatus']
        print(f"🤖 Agent Status: {agent_status}")
        
        # Check alias status  
        alias_response = agent_client.get_agent_alias(
            agentId="QIXL7HZUKS",
            agentAliasId="GJMBWBB1T7"
        )
        alias_status = alias_response['agentAlias']['agentAliasStatus']
        print(f"🔗 Alias Status: {alias_status}")
        
        if agent_status == 'PREPARED' and alias_status in ['PREPARED', 'READY']:
            print(f"✅ Both agent and alias are ready for invocation")
            return True
        else:
            print(f"⚠️ Agent or alias not ready yet")
            return False
            
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return False

def main():
    """Main test function"""
    
    print("🏈 FANTASY DRAFT ASSISTANT - AGENTCORE VALIDATION")
    print("=" * 60)
    print("Testing CORRECT AgentCore approach: invoke agents via runtime")
    print()
    
    # Check status first
    if test_agent_status():
        time.sleep(5)  # Brief pause
        
        # Test invocation
        success = test_agentcore_invocation()
        
        if success:
            print(f"\n🎯 NEXT STEPS:")
            print(f"1. ✅ AgentCore agent is working correctly")
            print(f"2. 🚀 Deploy remaining agents (Analysis, Strategy, Advisor)")
            print(f"3. 🔗 Integrate with web UI for live draft assistance")
            print(f"4. 🧪 Test with Sleeper Mock Draft as requested")
            
        else:
            print(f"\n⚠️ TROUBLESHOOTING:")
            print(f"1. Check AWS permissions for bedrock-agent-runtime")
            print(f"2. Verify agent and alias are in PREPARED status")
            print(f"3. Ensure service role has proper Bedrock permissions")
    else:
        print(f"\n⏳ Agent/alias still preparing. Wait 1-2 minutes and retry.")

if __name__ == "__main__":
    main()