#!/usr/bin/env python3
"""
Deploy Fantasy Draft Agents to Bedrock AgentCore Runtime
CORRECT APPROACH: Deploy agents TO AgentCore, then invoke via runtime
"""

import boto3
import json
import time
from typing import Dict, List, Optional
from botocore.exceptions import ClientError

class FantasyAgentCoreDeployer:
    def __init__(self, region_name: str = 'us-east-1'):
        self.region_name = region_name
        self.agent_client = boto3.client('bedrock-agent', region_name=region_name)
        self.runtime_client = boto3.client('bedrock-agent-runtime', region_name=region_name)
        
        # Foundation model for agents (AgentCore manages this internally)
        self.foundation_model = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
        
    def create_data_collector_agent(self) -> Optional[str]:
        """Create Data Collector Agent in AgentCore"""
        
        print("🏗️ Creating Data Collector Agent...")
        
        agent_instruction = """You are a Fantasy Football Data Collector Agent. Your role is to:

1. Gather player data from multiple sources (FantasyPros, Yahoo, ESPN)
2. Collect real-time injury reports and news
3. Aggregate ADP (Average Draft Position) data
4. Compile player rankings across different scoring formats
5. Collect weather and game conditions
6. Format data for analysis agents

Always return structured JSON data. Focus on accuracy and completeness.
Handle API failures gracefully with fallback data sources.
"""
        
        try:
            response = self.agent_client.create_agent(
                agentName='fantasy-data-collector',
                description='Collects and aggregates fantasy football data from multiple sources',
                foundationModel=self.foundation_model,
                instruction=agent_instruction,
                idleSessionTTLInSeconds=1800,  # 30 minutes
                tags={
                    'Project': 'FantasyDraftAssistant',
                    'AgentType': 'DataCollector',
                    'Environment': 'Production'
                }
            )
            
            agent_id = response['agent']['agentId']
            print(f"✅ Data Collector Agent created: {agent_id}")
            
            # Wait for agent to be ready
            self._wait_for_agent_ready(agent_id)
            
            return agent_id
            
        except ClientError as e:
            print(f"❌ Failed to create Data Collector Agent: {e}")
            return None
    
    def create_analysis_agent(self) -> Optional[str]:
        """Create Analysis Agent in AgentCore"""
        
        print("🏗️ Creating Analysis Agent...")
        
        agent_instruction = """You are a Fantasy Football Analysis Agent. Your role is to:

1. Analyze player performance trends and patterns
2. Evaluate matchup advantages and disadvantages  
3. Calculate value-based rankings and positional scarcity
4. Assess injury impact and return timelines
5. Analyze target share, snap counts, and usage patterns
6. Provide statistical projections and confidence intervals

Use advanced analytics and historical data patterns.
Consider league scoring format (SUPERFLEX prioritizes QBs).
Provide clear reasoning for all analysis conclusions.
"""
        
        try:
            response = self.agent_client.create_agent(
                agentName='fantasy-analysis-agent',
                description='Analyzes player data and provides statistical insights',
                foundationModel=self.foundation_model,
                instruction=agent_instruction,
                idleSessionTTLInSeconds=1800,
                tags={
                    'Project': 'FantasyDraftAssistant',
                    'AgentType': 'Analysis',
                    'Environment': 'Production'
                }
            )
            
            agent_id = response['agent']['agentId']
            print(f"✅ Analysis Agent created: {agent_id}")
            
            self._wait_for_agent_ready(agent_id)
            
            return agent_id
            
        except ClientError as e:
            print(f"❌ Failed to create Analysis Agent: {e}")
            return None
    
    def create_strategy_agent(self) -> Optional[str]:
        """Create Strategy Agent in AgentCore"""
        
        print("🏗️ Creating Strategy Agent...")
        
        agent_instruction = """You are a Fantasy Football Strategy Agent. Your role is to:

1. Develop draft strategies based on league settings and format
2. Calculate optimal draft position approaches (early QB in SUPERFLEX)
3. Identify value picks and sleepers at each draft position
4. Plan contingency strategies for different draft flows
5. Balance risk vs reward for each draft choice
6. Adapt strategy based on other managers' selections

Consider SUPERFLEX format where QBs have premium value.
Account for positional scarcity and bye week considerations.
Provide multiple strategic options with clear trade-offs.
"""
        
        try:
            response = self.agent_client.create_agent(
                agentName='fantasy-strategy-agent',
                description='Develops optimal draft strategies and contingency plans',
                foundationModel=self.foundation_model,
                instruction=agent_instruction,
                idleSessionTTLInSeconds=1800,
                tags={
                    'Project': 'FantasyDraftAssistant',
                    'AgentType': 'Strategy', 
                    'Environment': 'Production'
                }
            )
            
            agent_id = response['agent']['agentId']
            print(f"✅ Strategy Agent created: {agent_id}")
            
            self._wait_for_agent_ready(agent_id)
            
            return agent_id
            
        except ClientError as e:
            print(f"❌ Failed to create Strategy Agent: {e}")
            return None
    
    def create_advisor_agent(self) -> Optional[str]:
        """Create Advisor Agent in AgentCore"""
        
        print("🏗️ Creating Advisor Agent...")
        
        agent_instruction = """You are a Fantasy Football Draft Advisor Agent. Your role is to:

1. Provide real-time draft pick recommendations
2. Synthesize input from data, analysis, and strategy agents  
3. Communicate clearly with fantasy managers during live drafts
4. Explain reasoning behind each recommendation
5. Adapt advice based on draft flow and available players
6. Handle time pressure of live draft situations

Be concise but thorough in explanations.
Prioritize actionable advice over complex analysis.
Always provide backup options in case primary pick is taken.
Consider the human manager's preferences and risk tolerance.
"""
        
        try:
            response = self.agent_client.create_agent(
                agentName='fantasy-draft-advisor',
                description='Provides real-time draft recommendations and advice',
                foundationModel=self.foundation_model,
                instruction=agent_instruction,
                idleSessionTTLInSeconds=1800,
                tags={
                    'Project': 'FantasyDraftAssistant',
                    'AgentType': 'Advisor',
                    'Environment': 'Production'
                }
            )
            
            agent_id = response['agent']['agentId']
            print(f"✅ Advisor Agent created: {agent_id}")
            
            self._wait_for_agent_ready(agent_id)
            
            return agent_id
            
        except ClientError as e:
            print(f"❌ Failed to create Advisor Agent: {e}")
            return None
    
    def _wait_for_agent_ready(self, agent_id: str, max_wait: int = 300):
        """Wait for agent to be in PREPARED state"""
        
        print(f"⏳ Waiting for agent {agent_id} to be ready...")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = self.agent_client.get_agent(agentId=agent_id)
                status = response['agent']['agentStatus']
                
                if status == 'PREPARED':
                    print(f"✅ Agent {agent_id} is ready!")
                    return True
                elif status in ['FAILED', 'DELETING']:
                    print(f"❌ Agent {agent_id} failed with status: {status}")
                    return False
                else:
                    print(f"⏳ Agent status: {status}, waiting...")
                    time.sleep(10)
                    
            except ClientError as e:
                print(f"❌ Error checking agent status: {e}")
                return False
        
        print(f"⚠️ Agent {agent_id} not ready after {max_wait} seconds")
        return False
    
    def create_agent_aliases(self, agent_ids: Dict[str, str]) -> Dict[str, str]:
        """Create aliases for all agents"""
        
        print("🔗 Creating agent aliases...")
        aliases = {}
        
        for agent_name, agent_id in agent_ids.items():
            if not agent_id:
                continue
                
            try:
                response = self.agent_client.create_agent_alias(
                    agentId=agent_id,
                    agentAliasName=f"{agent_name}-live",
                    description=f"Live production alias for {agent_name}",
                    tags={
                        'Environment': 'Production',
                        'AgentName': agent_name
                    }
                )
                
                alias_id = response['agentAlias']['agentAliasId']
                aliases[agent_name] = alias_id
                print(f"✅ Created alias for {agent_name}: {alias_id}")
                
            except ClientError as e:
                print(f"❌ Failed to create alias for {agent_name}: {e}")
        
        return aliases
    
    def test_agent_invocation(self, agent_id: str, alias_id: str, agent_name: str):
        """Test invoking an agent through AgentCore runtime"""
        
        print(f"🧪 Testing {agent_name} invocation...")
        
        try:
            # This is the CORRECT way - invoke via AgentCore runtime
            response = self.runtime_client.invoke_agent(
                agentId=agent_id,
                agentAliasId=alias_id,
                sessionId=f"test-session-{int(time.time())}",
                inputText="Hello, please provide a brief test response."
            )
            
            # AgentCore returns streaming response
            event_stream = response['completion']
            
            full_response = ""
            for event in event_stream:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        full_response += chunk['bytes'].decode('utf-8')
            
            print(f"✅ {agent_name} response received: {full_response[:100]}...")
            return True
            
        except ClientError as e:
            print(f"❌ Failed to invoke {agent_name}: {e}")
            return False
    
    def deploy_all_agents(self) -> Dict[str, str]:
        """Deploy all fantasy draft agents to AgentCore"""
        
        print("🚀 DEPLOYING FANTASY DRAFT AGENTS TO BEDROCK AGENTCORE")
        print("=" * 60)
        print("Using CORRECT approach: Deploying TO AgentCore runtime")
        print()
        
        # Create all agents
        agent_ids = {}
        
        # Data Collector
        data_collector_id = self.create_data_collector_agent()
        if data_collector_id:
            agent_ids['data-collector'] = data_collector_id
        
        # Analysis Agent
        analysis_id = self.create_analysis_agent()
        if analysis_id:
            agent_ids['analysis'] = analysis_id
        
        # Strategy Agent
        strategy_id = self.create_strategy_agent()
        if strategy_id:
            agent_ids['strategy'] = strategy_id
        
        # Advisor Agent
        advisor_id = self.create_advisor_agent()
        if advisor_id:
            agent_ids['advisor'] = advisor_id
        
        print(f"\n📋 Created {len(agent_ids)} agents successfully")
        
        # Create aliases
        aliases = self.create_agent_aliases(agent_ids)
        
        # Test invocations
        print("\n🧪 Testing agent invocations...")
        for agent_name in agent_ids:
            if agent_name in aliases:
                self.test_agent_invocation(
                    agent_ids[agent_name],
                    aliases[agent_name], 
                    agent_name
                )
        
        # Save deployment info
        deployment_info = {
            'agent_ids': agent_ids,
            'aliases': aliases,
            'deployment_time': time.time(),
            'region': self.region_name,
            'foundation_model': self.foundation_model
        }
        
        with open('agentcore_deployment.json', 'w') as f:
            json.dump(deployment_info, f, indent=2)
        
        print(f"\n✅ AGENTCORE DEPLOYMENT COMPLETE!")
        print(f"📁 Deployment info saved to: agentcore_deployment.json")
        print(f"🤖 {len(agent_ids)} agents deployed to AgentCore runtime")
        
        return agent_ids

def main():
    """Deploy Fantasy Draft Assistant to AgentCore"""
    
    deployer = FantasyAgentCoreDeployer()
    agent_ids = deployer.deploy_all_agents()
    
    if agent_ids:
        print("\n🎉 SUCCESS: Fantasy Draft Assistant deployed to AgentCore!")
        print("🔗 Use the runtime client to invoke agents via agent IDs")
        print("📚 AgentCore handles model selection and orchestration automatically")
    else:
        print("\n❌ DEPLOYMENT FAILED: Check permissions and try again")

if __name__ == "__main__":
    main()