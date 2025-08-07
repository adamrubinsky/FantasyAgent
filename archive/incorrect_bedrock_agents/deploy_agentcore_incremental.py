#!/usr/bin/env python3
"""
Incremental AgentCore Deployment - Handle timeouts and prepare agents step by step
"""

import boto3
import json
import time
from botocore.exceptions import ClientError

class IncrementalAgentDeployer:
    def __init__(self, region_name: str = 'us-east-1'):
        self.region_name = region_name
        self.agent_client = boto3.client('bedrock-agent', region_name=region_name)
        self.runtime_client = boto3.client('bedrock-agent-runtime', region_name=region_name)
        self.foundation_model = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
        
    def check_existing_agents(self) -> dict:
        """Check what agents already exist"""
        try:
            response = self.agent_client.list_agents()
            agents = {}
            
            print("🔍 Checking existing AgentCore agents...")
            
            for agent in response.get('agentSummaries', []):
                name = agent['agentName']
                agent_id = agent['agentId']
                status = agent['agentStatus']
                
                print(f"📤 {name}: {agent_id} (Status: {status})")
                agents[name] = {
                    'id': agent_id,
                    'status': status
                }
            
            return agents
            
        except ClientError as e:
            print(f"❌ Error checking agents: {e}")
            return {}
    
    def prepare_agent(self, agent_id: str, agent_name: str) -> bool:
        """Prepare an agent that's in NOT_PREPARED status"""
        try:
            print(f"🔧 Preparing {agent_name} (ID: {agent_id})...")
            
            # Prepare the agent
            self.agent_client.prepare_agent(agentId=agent_id)
            
            print(f"⏳ Waiting for {agent_name} to be prepared...")
            
            # Wait for preparation (this can take several minutes)
            max_wait = 600  # 10 minutes
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                response = self.agent_client.get_agent(agentId=agent_id)
                status = response['agent']['agentStatus']
                
                if status == 'PREPARED':
                    print(f"✅ {agent_name} is now PREPARED!")
                    return True
                elif status in ['FAILED', 'DELETING']:
                    print(f"❌ {agent_name} failed with status: {status}")
                    return False
                else:
                    print(f"⏳ {agent_name} status: {status} (waiting...)")
                    time.sleep(30)  # Check every 30 seconds
                    
            print(f"⚠️ {agent_name} not prepared after {max_wait} seconds")
            return False
            
        except ClientError as e:
            print(f"❌ Error preparing {agent_name}: {e}")
            return False
    
    def create_single_agent(self, agent_config: dict) -> str:
        """Create a single agent with given configuration"""
        try:
            print(f"🏗️ Creating {agent_config['name']} agent...")
            
            response = self.agent_client.create_agent(
                agentName=agent_config['name'],
                description=agent_config['description'],
                foundationModel=self.foundation_model,
                instruction=agent_config['instruction'],
                idleSessionTTLInSeconds=1800,
                tags=agent_config['tags']
            )
            
            agent_id = response['agent']['agentId']
            print(f"✅ {agent_config['name']} created with ID: {agent_id}")
            
            return agent_id
            
        except ClientError as e:
            print(f"❌ Failed to create {agent_config['name']}: {e}")
            return None
    
    def create_agent_alias(self, agent_id: str, agent_name: str) -> str:
        """Create alias for a prepared agent"""
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
            print(f"✅ Created alias for {agent_name}: {alias_id}")
            
            return alias_id
            
        except ClientError as e:
            print(f"❌ Failed to create alias for {agent_name}: {e}")
            return None
    
    def get_agent_configs(self) -> list:
        """Get all agent configurations"""
        return [
            {
                'name': 'fantasy-data-collector',
                'description': 'Collects and aggregates fantasy football data from multiple sources',
                'instruction': '''You are a Fantasy Football Data Collector Agent. Your role is to:

1. Gather player data from multiple sources (FantasyPros, Yahoo, ESPN)
2. Collect real-time injury reports and news
3. Aggregate ADP (Average Draft Position) data
4. Compile player rankings across different scoring formats
5. Collect weather and game conditions
6. Format data for analysis agents

Always return structured JSON data. Focus on accuracy and completeness.
Handle API failures gracefully with fallback data sources.''',
                'tags': {
                    'Project': 'FantasyDraftAssistant',
                    'AgentType': 'DataCollector',
                    'Environment': 'Production'
                }
            },
            {
                'name': 'fantasy-analysis-agent',
                'description': 'Analyzes player data and provides statistical insights',
                'instruction': '''You are a Fantasy Football Analysis Agent. Your role is to:

1. Analyze player performance trends and patterns
2. Evaluate matchup advantages and disadvantages  
3. Calculate value-based rankings and positional scarcity
4. Assess injury impact and return timelines
5. Analyze target share, snap counts, and usage patterns
6. Provide statistical projections and confidence intervals

Use advanced analytics and historical data patterns.
Consider league scoring format (SUPERFLEX prioritizes QBs).
Provide clear reasoning for all analysis conclusions.''',
                'tags': {
                    'Project': 'FantasyDraftAssistant',
                    'AgentType': 'Analysis',
                    'Environment': 'Production'
                }
            },
            {
                'name': 'fantasy-strategy-agent',
                'description': 'Develops optimal draft strategies and contingency plans',
                'instruction': '''You are a Fantasy Football Strategy Agent. Your role is to:

1. Develop draft strategies based on league settings and format
2. Calculate optimal draft position approaches (early QB in SUPERFLEX)
3. Identify value picks and sleepers at each draft position
4. Plan contingency strategies for different draft flows
5. Balance risk vs reward for each draft choice
6. Adapt strategy based on other managers' selections

Consider SUPERFLEX format where QBs have premium value.
Account for positional scarcity and bye week considerations.
Provide multiple strategic options with clear trade-offs.''',
                'tags': {
                    'Project': 'FantasyDraftAssistant',
                    'AgentType': 'Strategy',
                    'Environment': 'Production'
                }
            },
            {
                'name': 'fantasy-draft-advisor',
                'description': 'Provides real-time draft recommendations and advice',
                'instruction': '''You are a Fantasy Football Draft Advisor Agent. Your role is to:

1. Provide real-time draft pick recommendations
2. Synthesize input from data, analysis, and strategy agents  
3. Communicate clearly with fantasy managers during live drafts
4. Explain reasoning behind each recommendation
5. Adapt advice based on draft flow and available players
6. Handle time pressure of live draft situations

Be concise but thorough in explanations.
Prioritize actionable advice over complex analysis.
Always provide backup options in case primary pick is taken.
Consider the human manager's preferences and risk tolerance.''',
                'tags': {
                    'Project': 'FantasyDraftAssistant',
                    'AgentType': 'Advisor',
                    'Environment': 'Production'
                }
            }
        ]
    
    def deploy_step_by_step(self):
        """Deploy agents step by step with status checking"""
        
        print("🚀 INCREMENTAL AGENTCORE DEPLOYMENT")
        print("=" * 50)
        
        # Check existing agents
        existing_agents = self.check_existing_agents()
        
        # Get agent configs
        agent_configs = self.get_agent_configs()
        
        deployment_status = {}
        
        for config in agent_configs:
            agent_name = config['name']
            
            if agent_name in existing_agents:
                # Agent exists, check status
                existing_info = existing_agents[agent_name]
                agent_id = existing_info['id']
                status = existing_info['status']
                
                print(f"\n🔍 {agent_name} already exists (Status: {status})")
                
                if status == 'NOT_PREPARED':
                    # Prepare the agent
                    if self.prepare_agent(agent_id, agent_name):
                        deployment_status[agent_name] = {
                            'id': agent_id,
                            'status': 'PREPARED'
                        }
                elif status == 'PREPARED':
                    print(f"✅ {agent_name} already prepared")
                    deployment_status[agent_name] = {
                        'id': agent_id,
                        'status': 'PREPARED'
                    }
            else:
                # Create new agent
                print(f"\n🆕 Creating new agent: {agent_name}")
                agent_id = self.create_single_agent(config)
                
                if agent_id:
                    # Prepare the newly created agent
                    if self.prepare_agent(agent_id, agent_name):
                        deployment_status[agent_name] = {
                            'id': agent_id,
                            'status': 'PREPARED'
                        }
        
        # Create aliases for prepared agents
        aliases = {}
        for agent_name, info in deployment_status.items():
            if info['status'] == 'PREPARED':
                alias_id = self.create_agent_alias(info['id'], agent_name)
                if alias_id:
                    aliases[agent_name] = alias_id
        
        # Save deployment info
        final_deployment = {
            'agent_ids': {name: info['id'] for name, info in deployment_status.items()},
            'aliases': aliases,
            'deployment_time': time.time(),
            'region': self.region_name,
            'foundation_model': self.foundation_model
        }
        
        with open('agentcore_deployment.json', 'w') as f:
            json.dump(final_deployment, f, indent=2)
        
        print(f"\n🎉 DEPLOYMENT COMPLETE!")
        print(f"✅ {len(deployment_status)} agents processed")
        print(f"✅ {len(aliases)} aliases created")
        print(f"📁 Deployment saved to: agentcore_deployment.json")
        
        return final_deployment

def main():
    deployer = IncrementalAgentDeployer()
    deployment = deployer.deploy_step_by_step()
    
    if deployment:
        print("\n🎯 Next Steps:")
        print("1. Run: python3 agentcore_fantasy_client.py")
        print("2. Test agent invocations via AgentCore runtime")
        print("3. Integrate with web UI for live draft assistance")

if __name__ == "__main__":
    main()