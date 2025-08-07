"""
Amazon Bedrock AgentCore - Fantasy Draft Recommendation Agent
Proof of Concept: Single agent migration from CrewAI to Bedrock
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import asyncio
from dotenv import load_dotenv

# Load Bedrock environment
load_dotenv('../.env.bedrock')

class BedrockRecommendationAgent:
    """
    Fantasy Football Draft Recommendation Agent for Bedrock AgentCore
    
    This agent synthesizes data from multiple sources to provide
    clear, actionable draft recommendations.
    """
    
    def __init__(self):
        """Initialize Bedrock client and configuration"""
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        
        # Initialize Bedrock clients
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=self.region
        )
        
        self.bedrock_agent = boto3.client(
            service_name='bedrock-agent-runtime',
            region_name=self.region
        )
        
        # Agent configuration
        self.agent_config = {
            "name": "fantasy-draft-recommendation-agent",
            "description": "Provides draft recommendations based on analysis",
            "instruction": """You are an expert Fantasy Football Draft Advisor specializing in SUPERFLEX leagues.
            
            Your role is to:
            1. Synthesize data from multiple sources (rankings, projections, league context)
            2. Provide clear, confident draft recommendations
            3. Explain reasoning in simple terms
            4. Consider SUPERFLEX format where QBs are premium
            5. Balance best player available vs roster needs
            
            Always provide:
            - Top 3 player recommendations
            - Clear reasoning for each
            - Risk/reward assessment
            - Alternative options if needed
            
            Keep responses concise but informative (under 200 words).
            """,
            "tools": self._define_tools()
        }
        
        # Cache for performance
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define tools available to the agent"""
        return [
            {
                "toolSpec": {
                    "name": "get_live_rankings",
                    "description": "Fetch current FantasyPros rankings",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "position": {
                                    "type": "string",
                                    "description": "Position filter (QB, RB, WR, TE, ALL)"
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Number of players to return",
                                    "default": 20
                                }
                            }
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_available_players",
                    "description": "Get list of available players in current draft",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "draft_id": {
                                    "type": "string",
                                    "description": "Current draft ID"
                                },
                                "position": {
                                    "type": "string",
                                    "description": "Optional position filter"
                                }
                            },
                            "required": ["draft_id"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "analyze_roster_needs",
                    "description": "Analyze current roster and identify needs",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "current_roster": {
                                    "type": "array",
                                    "description": "List of currently drafted players"
                                }
                            },
                            "required": ["current_roster"]
                        }
                    }
                }
            }
        ]
    
    async def get_recommendation(
        self,
        context: Dict[str, Any],
        question: Optional[str] = None
    ) -> str:
        """
        Get draft recommendation based on current context
        
        Args:
            context: Current draft context (pick number, available players, etc.)
            question: Optional specific question from user
            
        Returns:
            Recommendation string with reasoning
        """
        try:
            # Check cache first
            cache_key = f"{context.get('current_pick', 0)}_{question or 'default'}"
            if cache_key in self._cache:
                cached_time, cached_response = self._cache[cache_key]
                if (datetime.now() - cached_time).seconds < self._cache_ttl:
                    return f"📍 (Cached) {cached_response}"
            
            # Prepare the prompt
            prompt = self._build_prompt(context, question)
            
            # Invoke Bedrock model
            response = await self._invoke_bedrock(prompt)
            
            # Cache the response
            self._cache[cache_key] = (datetime.now(), response)
            
            return response
            
        except Exception as e:
            print(f"❌ Bedrock agent error: {e}")
            return self._get_fallback_recommendation(context)
    
    def _build_prompt(self, context: Dict[str, Any], question: Optional[str]) -> str:
        """Build prompt for Bedrock model"""
        current_pick = context.get('current_pick', 'Unknown')
        available_players = context.get('available_players', [])[:10]
        user_roster = context.get('user_roster', [])
        
        prompt = f"""
        CONTEXT:
        - League Format: SUPERFLEX Half-PPR, 12 teams
        - Current Pick: #{current_pick}
        - Your Current Roster: {', '.join(user_roster) if user_roster else 'Empty'}
        
        TOP AVAILABLE PLAYERS:
        {chr(10).join(available_players) if available_players else 'No data available'}
        
        USER QUESTION: {question or 'Who should I draft with this pick?'}
        
        Provide a clear recommendation with:
        1. Top 3 player suggestions
        2. Brief reasoning for each (1-2 sentences)
        3. Consider SUPERFLEX premium on QBs
        
        Keep response under 200 words for quick decision making.
        """
        
        return prompt
    
    async def _invoke_bedrock(self, prompt: str) -> str:
        """Invoke Bedrock model for recommendation"""
        try:
            # Prepare the request
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
            
            # Make the API call
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType='application/json',
                accept='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            recommendation = response_body.get('content', [{}])[0].get('text', '')
            
            return f"🎯 **AI Recommendation**:\n\n{recommendation}"
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ThrottlingException':
                # Wait and retry once
                await asyncio.sleep(1)
                return await self._invoke_bedrock(prompt)
            else:
                raise e
    
    def _get_fallback_recommendation(self, context: Dict[str, Any]) -> str:
        """Provide fallback recommendation if Bedrock fails"""
        current_pick = context.get('current_pick', 'Unknown')
        
        # Simple pick-based recommendations
        if current_pick <= 4:
            return """🎯 **Quick Recommendation** (Fallback):

**Top 3 Options:**
1. **Elite QB** (Josh Allen/Lamar Jackson) - SUPERFLEX premium makes them worth early picks
2. **Elite RB** (Christian McCaffrey/Breece Hall) - Workhorse backs are scarce
3. **Elite WR** (Tyreek Hill/CeeDee Lamb) - Consistent high-floor producers

In SUPERFLEX, don't be afraid to take a QB early - they score more and are more consistent than other positions."""
        
        elif current_pick <= 8:
            return """🎯 **Quick Recommendation** (Fallback):

**Top 3 Options:**
1. **Tier 2 QB** (Dak Prescott/Jalen Hurts) - Still elite in SUPERFLEX format
2. **Top RB** (Bijan Robinson/Jonathan Taylor) - Volume-based RB1s
3. **Elite WR** (Justin Jefferson/Ja'Marr Chase) - Target monsters

Focus on securing at least one QB in the first 3 rounds for SUPERFLEX advantage."""
        
        else:
            return """🎯 **Quick Recommendation** (Fallback):

**Top 3 Options:**
1. **Value QB** (Trevor Lawrence/Tua) - Don't wait too long on QB2
2. **Upside RB** (James Cook/Rachaad White) - PPR value backs
3. **Target WR** (Chris Olave/DK Metcalf) - High-upside WR2s

From late position, consider going RB-heavy early then grabbing QBs in rounds 3-5."""
    
    async def create_bedrock_agent(self) -> Dict[str, Any]:
        """
        Create or update the agent in Bedrock
        
        Returns:
            Agent details including ID and ARN
        """
        try:
            agent_name = self.agent_config['name']
            role_arn = os.getenv('AGENT_RUNTIME_ROLE_ARN')
            
            if not role_arn:
                raise ValueError("AGENT_RUNTIME_ROLE_ARN not set in .env.bedrock")
            
            # Create agent request
            response = self.bedrock_agent.create_agent(
                agentName=agent_name,
                agentResourceRoleArn=role_arn,
                description=self.agent_config['description'],
                foundationModel=self.model_id,
                instruction=self.agent_config['instruction'],
                idleSessionTTLInSeconds=600
            )
            
            agent_id = response['agent']['agentId']
            agent_arn = response['agent']['agentArn']
            
            print(f"✅ Created Bedrock Agent: {agent_id}")
            print(f"   ARN: {agent_arn}")
            
            return {
                "agent_id": agent_id,
                "agent_arn": agent_arn,
                "status": "CREATED"
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                print(f"ℹ️ Agent already exists, fetching details...")
                # Get existing agent details
                return await self._get_existing_agent()
            else:
                raise e
    
    async def _get_existing_agent(self) -> Dict[str, Any]:
        """Get details of existing agent"""
        # List agents and find ours
        response = self.bedrock_agent.list_agents()
        
        for agent in response.get('agentSummaries', []):
            if agent['agentName'] == self.agent_config['name']:
                return {
                    "agent_id": agent['agentId'],
                    "agent_arn": agent['agentArn'],
                    "status": agent['agentStatus']
                }
        
        raise ValueError(f"Agent {self.agent_config['name']} not found")


# Test function
async def test_bedrock_agent():
    """Test the Bedrock Recommendation Agent"""
    print("🧪 Testing Bedrock Recommendation Agent")
    print("=" * 50)
    
    agent = BedrockRecommendationAgent()
    
    # Test context
    test_context = {
        "current_pick": 7,
        "available_players": [
            "Josh Allen (QB) - Rank: 3",
            "Breece Hall (RB) - Rank: 5", 
            "Tyreek Hill (WR) - Rank: 4",
            "Justin Jefferson (WR) - Rank: 2",
            "Bijan Robinson (RB) - Rank: 6",
            "Dak Prescott (QB) - Rank: 8",
            "Garrett Wilson (WR) - Rank: 12",
            "Travis Etienne (RB) - Rank: 10",
            "CeeDee Lamb (WR) - Rank: 7",
            "Lamar Jackson (QB) - Rank: 9"
        ],
        "user_roster": []
    }
    
    # Test 1: Basic recommendation
    print("\n📋 Test 1: Basic Pick Recommendation")
    recommendation = await agent.get_recommendation(test_context)
    print(recommendation)
    
    # Test 2: Specific question
    print("\n📋 Test 2: Player Comparison")
    recommendation = await agent.get_recommendation(
        test_context,
        "Should I take Josh Allen or Justin Jefferson?"
    )
    print(recommendation)
    
    # Test 3: Create agent in Bedrock (optional)
    print("\n📋 Test 3: Create Bedrock Agent")
    try:
        agent_details = await agent.create_bedrock_agent()
        print(f"✅ Agent Details: {json.dumps(agent_details, indent=2)}")
    except Exception as e:
        print(f"⚠️ Could not create agent: {e}")
        print("   (This is normal if IAM roles aren't set up yet)")
    
    print("\n" + "=" * 50)
    print("✅ Bedrock Agent tests complete!")


if __name__ == "__main__":
    asyncio.run(test_bedrock_agent())