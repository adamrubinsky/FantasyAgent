#!/usr/bin/env python3
"""
Fantasy Draft Assistant Client - Using AgentCore Runtime
CORRECT APPROACH: Invoke deployed agents via AgentCore runtime API
"""

import boto3
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError

class FantasyAgentCoreClient:
    def __init__(self, deployment_file: str = 'agentcore_deployment.json'):
        # Load deployment info
        try:
            with open(deployment_file, 'r') as f:
                self.deployment = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Deployment file {deployment_file} not found. Run deploy_fantasy_agents_to_agentcore.py first.")
        
        # AgentCore runtime client (CORRECT client for invoking agents)
        self.runtime_client = boto3.client(
            'bedrock-agent-runtime', 
            region_name=self.deployment.get('region', 'us-east-1')
        )
        
        self.agent_ids = self.deployment['agent_ids']
        self.aliases = self.deployment['aliases']
        
        # Session for maintaining conversation context
        self.session_id = str(uuid.uuid4())
        
    def invoke_agent(self, agent_name: str, input_text: str, session_id: Optional[str] = None) -> str:
        """Invoke a specific agent via AgentCore runtime"""
        
        if agent_name not in self.agent_ids:
            raise ValueError(f"Agent {agent_name} not found in deployment")
        
        agent_id = self.agent_ids[agent_name]
        alias_id = self.aliases.get(agent_name)
        
        if not alias_id:
            raise ValueError(f"No alias found for agent {agent_name}")
        
        # Use provided session or default
        current_session = session_id or self.session_id
        
        try:
            print(f"🤖 Invoking {agent_name} agent...")
            
            # CORRECT AgentCore invocation
            response = self.runtime_client.invoke_agent(
                agentId=agent_id,
                agentAliasId=alias_id,
                sessionId=current_session,
                inputText=input_text
            )
            
            # Process streaming response from AgentCore
            event_stream = response['completion']
            full_response = ""
            
            for event in event_stream:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        chunk_text = chunk['bytes'].decode('utf-8')
                        full_response += chunk_text
                        print(f"📝 {chunk_text}", end='', flush=True)
            
            print()  # New line after streaming
            return full_response
            
        except ClientError as e:
            print(f"❌ Error invoking {agent_name}: {e}")
            raise
    
    def collect_player_data(self, position: str = "QB", count: int = 20) -> str:
        """Use Data Collector agent to gather player data"""
        
        input_text = f"""Collect the top {count} {position} players for fantasy football draft. 
        Include: rankings, ADP, injury status, recent news.
        Format as JSON with player name, team, ranking, adp, status."""
        
        return self.invoke_agent('data-collector', input_text)
    
    def analyze_players(self, player_data: str) -> str:
        """Use Analysis agent to analyze player data"""
        
        input_text = f"""Analyze this player data for fantasy football value:

{player_data}

Provide: value assessment, breakout/bust candidates, injury concerns, 
positional scarcity analysis. Focus on SUPERFLEX league format."""
        
        return self.invoke_agent('analysis', input_text)
    
    def get_draft_strategy(self, draft_position: int, league_size: int = 12) -> str:
        """Use Strategy agent to develop draft approach"""
        
        input_text = f"""Create draft strategy for SUPERFLEX league:
- Draft position: {draft_position} of {league_size}
- Format: SUPERFLEX (2 QB/1 SUPERFLEX)
- Scoring: PPR

Provide: early round targets, QB prioritization, value picks by round, 
contingency plans."""
        
        return self.invoke_agent('strategy', input_text)
    
    def get_draft_advice(self, context: Dict[str, Any]) -> str:
        """Use Advisor agent for real-time draft recommendations"""
        
        available_players = context.get('available_players', [])
        current_roster = context.get('current_roster', [])
        draft_position = context.get('draft_position', 1)
        round_number = context.get('round', 1)
        
        input_text = f"""LIVE DRAFT ADVICE NEEDED:

Current Situation:
- Round: {round_number}
- Pick: {draft_position}
- My Roster: {current_roster}

Top Available Players: {available_players[:10]}

Provide: 
1. Top 3 recommendations with reasoning
2. Backup options if primary pick is taken
3. Position needs assessment
4. Value vs need analysis"""
        
        return self.invoke_agent('advisor', input_text)
    
    def run_complete_draft_analysis(self) -> None:
        """Run complete multi-agent draft preparation"""
        
        print("🏈 FANTASY DRAFT ASSISTANT - AGENTCORE POWERED")
        print("=" * 60)
        print("Using Bedrock AgentCore multi-agent orchestration")
        print()
        
        # Step 1: Collect QB data (high priority in SUPERFLEX)
        print("📊 Step 1: Collecting QB Data...")
        print("-" * 40)
        qb_data = self.collect_player_data("QB", 15)
        
        time.sleep(2)  # Brief pause between agents
        
        # Step 2: Analyze the QB data
        print("\n🔍 Step 2: Analyzing QB Value...")
        print("-" * 40)
        qb_analysis = self.analyze_players(qb_data)
        
        time.sleep(2)
        
        # Step 3: Get draft strategy
        print("\n📋 Step 3: Developing Draft Strategy...")
        print("-" * 40)
        draft_strategy = self.get_draft_strategy(draft_position=8, league_size=12)
        
        time.sleep(2)
        
        # Step 4: Get specific advice
        print("\n🎯 Step 4: Getting Draft Recommendations...")
        print("-" * 40)
        mock_context = {
            'available_players': ['Josh Allen', 'Lamar Jackson', 'Justin Jefferson', 'Tyreek Hill'],
            'current_roster': [],
            'draft_position': 8,
            'round': 1
        }
        draft_advice = self.get_draft_advice(mock_context)
        
        print("\n" + "=" * 60)
        print("🎉 COMPLETE DRAFT ANALYSIS FINISHED!")
        print("✅ All 4 AgentCore agents successfully invoked")
        print("🤖 AgentCore handled model selection and orchestration")
        print("=" * 60)
    
    def list_deployed_agents(self) -> None:
        """Show information about deployed agents"""
        
        print("🤖 DEPLOYED AGENTCORE AGENTS")
        print("=" * 40)
        
        for agent_name, agent_id in self.agent_ids.items():
            alias_id = self.aliases.get(agent_name, 'No alias')
            print(f"📤 {agent_name.upper()}")
            print(f"   Agent ID: {agent_id}")
            print(f"   Alias ID: {alias_id}")
            print()
        
        print(f"🔗 Session ID: {self.session_id}")
        print(f"🌍 Region: {self.deployment.get('region', 'us-east-1')}")

def main():
    """Run Fantasy Draft Assistant using AgentCore"""
    
    try:
        # Initialize client
        client = FantasyAgentCoreClient()
        
        # Show deployed agents
        client.list_deployed_agents()
        
        # Run complete analysis
        client.run_complete_draft_analysis()
        
    except FileNotFoundError:
        print("❌ No deployment found!")
        print("📋 Run: python3 deploy_fantasy_agents_to_agentcore.py")
    except Exception as e:
        print(f"❌ Error running client: {e}")

if __name__ == "__main__":
    main()