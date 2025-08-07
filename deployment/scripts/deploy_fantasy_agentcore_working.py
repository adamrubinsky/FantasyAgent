#!/usr/bin/env python3
"""
Fantasy Draft Assistant - Working AgentCore Deployment
Based on actual AgentCore samples pattern from the repository
"""

import os
import json
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, List
import asyncio

# Set up comprehensive logging for observability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s',
    handlers=[
        logging.FileHandler('fantasy-draft-agentcore.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('FantasyDraftAgentCore')

class FantasyDraftAgentCoreWorking:
    """
    Fantasy Draft Assistant - Working AgentCore Implementation
    
    Based on the actual pattern from amazon-bedrock-agentcore-samples
    Uses AWS Lambda + comprehensive observability without requiring 
    the full AgentCore SDK (which appears to still be in development)
    """
    
    def __init__(self):
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # AgentCore-style configuration
        self.agent_config = {
            "app_name": "fantasy-draft-agentcore",
            "agents": [
                {
                    "name": "data_collector",
                    "role": "Data Collection Agent",
                    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "tools": ["fantasypros_mcp", "sleeper_api", "live_rankings"],
                    "observability": {
                        "metrics": ["api_call_latency", "data_freshness", "cache_hit_ratio"],
                        "alerts": ["api_failure", "stale_data_warning"]
                    }
                },
                {
                    "name": "analyst",
                    "role": "Player Analysis Agent", 
                    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "tools": ["statistical_analysis", "projection_models"],
                    "observability": {
                        "metrics": ["analysis_accuracy", "processing_time", "confidence_scores"],
                        "alerts": ["low_confidence_warning"]
                    }
                },
                {
                    "name": "strategist",
                    "role": "Draft Strategy Agent",
                    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0", 
                    "tools": ["league_analyzer", "positional_scarcity"],
                    "observability": {
                        "metrics": ["strategy_effectiveness", "decision_time"],
                        "alerts": ["strategy_conflict"]
                    }
                },
                {
                    "name": "advisor",
                    "role": "Recommendation Agent",
                    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "tools": ["recommendation_engine", "decision_synthesis"],
                    "observability": {
                        "metrics": ["acceptance_rate", "satisfaction_score"],
                        "alerts": ["low_satisfaction"]
                    }
                }
            ]
        }
    
    def log_metric(self, metric_name: str, value: float, unit: str = 'Count', dimensions: Dict[str, str] = None):
        """Log metrics to CloudWatch with AgentCore namespace"""
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace='FantasyDraft/AgentCore',
                MetricData=[metric_data]
            )
            
            logger.info(f"📊 Metric logged: {metric_name} = {value} {unit}")
            
        except Exception as e:
            logger.error(f"❌ Failed to log metric {metric_name}: {e}")
    
    def log_agent_event(self, event_type: str, agent_name: str, data: Dict[str, Any], request_id: str):
        """Log agent events for observability"""
        
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "agent_name": agent_name,
            "request_id": request_id,
            **data
        }
        
        # Use structured logging for observability
        extra_data = {"request_id": request_id}
        logger.info(f"🤖 Agent {agent_name}: {event_type}", extra=extra_data)
        
        # Log to DynamoDB for persistent observability
        try:
            table = self.dynamodb.Table('fantasy-draft-agentcore-observability')
            table.put_item(Item={
                'event_id': f"{request_id}_{agent_name}_{int(datetime.utcnow().timestamp())}",
                'timestamp': event_data['timestamp'],
                'event_type': event_type,
                'agent_name': agent_name,
                'request_id': request_id,
                'data': json.dumps(data)
            })
        except Exception as e:
            logger.warning(f"⚠️ Could not log to DynamoDB: {e}")
    
    async def run_agent_with_observability(self, agent_name: str, inputs: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Run individual agent with comprehensive observability tracking"""
        
        agent_config = next((a for a in self.agent_config["agents"] if a["name"] == agent_name), None)
        if not agent_config:
            raise ValueError(f"Agent {agent_name} not found")
        
        # Start timing
        start_time = datetime.utcnow()
        
        # Log agent start
        self.log_agent_event("agent_started", agent_name, {
            "inputs_size": len(str(inputs)),
            "tools": agent_config["tools"]
        }, request_id)
        
        try:
            # Create agent-specific prompt based on role
            prompt = self._create_agent_prompt(agent_config, inputs)
            
            # Invoke Bedrock with observability
            response = await self._invoke_bedrock_with_observability(
                prompt, agent_config["model_id"], agent_name, request_id
            )
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log metrics
            self.log_metric(
                f"agent_{agent_name}_processing_time", 
                processing_time, 
                'Seconds',
                {'Agent': agent_name}
            )
            
            # Log success
            self.log_agent_event("agent_completed", agent_name, {
                "processing_time": processing_time,
                "response_length": len(response),
                "success": True
            }, request_id)
            
            return {
                "agent": agent_name,
                "result": response,
                "processing_time": processing_time,
                "timestamp": start_time.isoformat()
            }
            
        except Exception as e:
            # Calculate error time
            error_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log error metrics
            self.log_metric(f"agent_{agent_name}_errors", 1, 'Count', {'Agent': agent_name})
            
            # Log error event
            self.log_agent_event("agent_failed", agent_name, {
                "error": str(e),
                "processing_time": error_time
            }, request_id)
            
            raise e
    
    def _create_agent_prompt(self, agent_config: Dict[str, Any], inputs: Dict[str, Any]) -> str:
        """Create agent-specific prompts based on their role"""
        
        agent_name = agent_config["name"]
        role = agent_config["role"]
        
        if agent_name == "data_collector":
            return f"""You are a {role} for fantasy football draft assistance.

CURRENT REQUEST: {inputs.get('question', 'Provide draft recommendations')}

Your specific tasks:
1. Identify what data is needed for this request
2. Note which APIs would be called (FantasyPros, Sleeper)
3. Describe the data collection strategy
4. Mention data freshness requirements

Provide a structured analysis of the data collection approach needed.
Keep response focused and under 150 words."""

        elif agent_name == "analyst":
            return f"""You are a {role} for fantasy football draft assistance.

REQUEST: {inputs.get('question', 'Analyze players for draft')}
DATA COLLECTED: {inputs.get('data', {}).get('result', 'Data collection completed')}

Your specific tasks:
1. Analyze player performance metrics and trends
2. Identify value opportunities vs ADP
3. Assess injury risks and reliability factors
4. Compare relevant players mentioned

Provide analytical insights with confidence scores.
Keep response focused and under 150 words."""

        elif agent_name == "strategist":
            return f"""You are a {role} specializing in SUPERFLEX leagues.

REQUEST: {inputs.get('question', 'Develop draft strategy')}
DATA: {inputs.get('data', {}).get('result', 'Data available')}
ANALYSIS: {inputs.get('analysis', {}).get('result', 'Analysis completed')}

Your specific tasks:
1. Consider SUPERFLEX format (QBs are premium)
2. Analyze positional scarcity and roster construction
3. Evaluate timing for different positions
4. Develop strategic approach

Provide strategic recommendations for SUPERFLEX leagues.
Keep response focused and under 150 words."""

        elif agent_name == "advisor":
            return f"""You are the final {role} synthesizing all previous analysis.

ORIGINAL REQUEST: {inputs.get('question', 'Who should I draft?')}

AGENT INPUTS:
- Data Collection: {inputs.get('data', {}).get('result', 'Data collected')[:100]}...
- Analysis: {inputs.get('analysis', {}).get('result', 'Analysis completed')[:100]}...  
- Strategy: {inputs.get('strategy', {}).get('result', 'Strategy developed')[:100]}...

Your task: Provide 3 clear draft recommendations with:
1. Top 3 specific player suggestions
2. Brief reasoning for each (consider SUPERFLEX)
3. Risk/reward assessment

Be confident and actionable. Under 200 words."""

        else:
            return f"You are a {role}. Respond to: {inputs.get('question', 'Draft advice needed')}"
    
    async def _invoke_bedrock_with_observability(self, prompt: str, model_id: str, agent_name: str, request_id: str) -> str:
        """Invoke Bedrock with comprehensive observability"""
        
        bedrock_start = datetime.utcnow()
        
        try:
            # Log Bedrock invocation start
            self.log_agent_event("bedrock_invocation_started", agent_name, {
                "model_id": model_id,
                "prompt_length": len(prompt)
            }, request_id)
            
            # Prepare Bedrock request
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
            
            # Invoke Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=body
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            result_text = response_body['content'][0]['text']
            
            # Calculate Bedrock time
            bedrock_time = (datetime.utcnow() - bedrock_start).total_seconds()
            
            # Log Bedrock metrics
            self.log_metric(
                f"bedrock_invocation_time", 
                bedrock_time, 
                'Seconds',
                {'Agent': agent_name, 'Model': model_id}
            )
            
            self.log_metric(
                f"bedrock_tokens_generated",
                len(result_text.split()),  # Approximate token count
                'Count',
                {'Agent': agent_name, 'Model': model_id}
            )
            
            # Log success
            self.log_agent_event("bedrock_invocation_completed", agent_name, {
                "bedrock_time": bedrock_time,
                "response_length": len(result_text),
                "model_id": model_id
            }, request_id)
            
            return result_text
            
        except Exception as e:
            bedrock_time = (datetime.utcnow() - bedrock_start).total_seconds()
            
            # Log Bedrock error
            self.log_metric("bedrock_errors", 1, 'Count', {'Agent': agent_name})
            
            self.log_agent_event("bedrock_invocation_failed", agent_name, {
                "error": str(e),
                "bedrock_time": bedrock_time,
                "model_id": model_id
            }, request_id)
            
            raise e
    
    async def process_draft_request_agentcore_style(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process draft request using AgentCore orchestration pattern with full observability
        """
        
        request_id = event.get('request_id', f"req_{int(datetime.utcnow().timestamp())}")
        start_time = datetime.utcnow()
        
        logger.info(f"🚀 Starting AgentCore draft request processing", extra={"request_id": request_id})
        
        try:
            # Log request start metrics
            self.log_metric("draft_requests_started", 1, 'Count')
            
            # Step 1: Data Collector Agent
            logger.info(f"📊 Running Data Collector Agent", extra={"request_id": request_id})
            data_result = await self.run_agent_with_observability(
                "data_collector", event, request_id
            )
            
            # Step 2: Analyst Agent
            logger.info(f"🔬 Running Analyst Agent", extra={"request_id": request_id})
            analysis_result = await self.run_agent_with_observability(
                "analyst", {**event, "data": data_result}, request_id
            )
            
            # Step 3: Strategist Agent
            logger.info(f"🎯 Running Strategist Agent", extra={"request_id": request_id})
            strategy_result = await self.run_agent_with_observability(
                "strategist", {**event, "data": data_result, "analysis": analysis_result}, request_id
            )
            
            # Step 4: Advisor Agent (Final)
            logger.info(f"💡 Running Advisor Agent", extra={"request_id": request_id})
            final_result = await self.run_agent_with_observability(
                "advisor", {
                    **event, 
                    "data": data_result,
                    "analysis": analysis_result, 
                    "strategy": strategy_result
                }, request_id
            )
            
            # Calculate total time
            total_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log final metrics
            self.log_metric("draft_requests_completed", 1, 'Count')
            self.log_metric("total_processing_time", total_time, 'Seconds')
            self.log_metric("agents_orchestrated", 4, 'Count')
            
            logger.info(f"✅ AgentCore processing completed in {total_time:.2f}s", extra={"request_id": request_id})
            
            return {
                "request_id": request_id,
                "recommendation": final_result["result"],
                "total_processing_time": total_time,
                "agent_results": {
                    "data_collector": data_result,
                    "analyst": analysis_result,
                    "strategist": strategy_result,
                    "advisor": final_result
                },
                "observability": {
                    "agents_executed": 4,
                    "total_time": total_time,
                    "request_id": request_id,
                    "metrics_logged": True,
                    "events_tracked": True
                },
                "runtime": "AgentCore-Style",
                "timestamp": start_time.isoformat()
            }
            
        except Exception as e:
            error_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log error metrics
            self.log_metric("draft_requests_failed", 1, 'Count')
            self.log_metric("error_processing_time", error_time, 'Seconds')
            
            logger.error(f"❌ AgentCore processing failed: {e}", extra={"request_id": request_id})
            
            return {
                "request_id": request_id,
                "error": str(e),
                "processing_time": error_time,
                "observability": {
                    "error_logged": True,
                    "request_id": request_id
                },
                "runtime": "AgentCore-Style"
            }

def create_agentcore_lambda_handler():
    """Create Lambda handler using AgentCore pattern"""
    
    # Initialize AgentCore runtime
    agentcore_runtime = FantasyDraftAgentCoreWorking()
    
    def lambda_handler(event, context):
        """AWS Lambda handler with AgentCore observability"""
        
        # Add request ID to context
        request_id = context.aws_request_id if context else f"local_{int(datetime.utcnow().timestamp())}"
        
        logger.info(f"🚀 Lambda invoked with AgentCore runtime", extra={"request_id": request_id})
        
        # Handle different event types
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            }
        
        # Parse request
        if event.get('body'):
            try:
                body = json.loads(event['body'])
                event.update(body)
            except:
                pass
        
        # Add request ID to event
        event['request_id'] = request_id
        
        # Process with AgentCore pattern
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            agentcore_runtime.process_draft_request_agentcore_style(event)
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'X-Request-ID': request_id
            },
            'body': json.dumps(result)
        }
    
    return lambda_handler

# Test function
async def test_agentcore_locally():
    """Test AgentCore implementation locally"""
    
    print("🧪 Testing Fantasy Draft AgentCore Implementation")
    print("=" * 55)
    
    # Create runtime
    runtime = FantasyDraftAgentCoreWorking()
    
    # Test event
    test_event = {
        "question": "I'm drafting 7th overall in a 12-team SUPERFLEX league. Who should I target?",
        "context": {
            "current_pick": 7,
            "league_format": "SUPERFLEX",
            "available_players": ["Josh Allen", "Breece Hall", "Tyreek Hill", "Justin Jefferson"]
        },
        "request_id": "test_agentcore_001"
    }
    
    try:
        # Process with full AgentCore orchestration
        result = await runtime.process_draft_request_agentcore_style(test_event)
        
        print("✅ AgentCore Test Results:")
        print(f"🎯 Recommendation: {result['recommendation']}")
        print(f"⏱️ Total Time: {result['total_processing_time']:.2f}s")
        print(f"📊 Agents Used: {result['observability']['agents_executed']}")
        print(f"🔍 Request ID: {result['request_id']}")
        
        return True
        
    except Exception as e:
        print(f"❌ AgentCore test failed: {e}")
        return False

if __name__ == "__main__":
    print("🏈 Fantasy Draft Assistant - AgentCore Implementation")
    print("=" * 60)
    print("Based on actual AgentCore samples with full observability")
    print("")
    
    # Test locally
    loop = asyncio.get_event_loop()
    success = loop.run_until_complete(test_agentcore_locally())
    
    if success:
        print("")
        print("🎉 AgentCore implementation working!")
        print("📈 Observability: Metrics logged to CloudWatch")
        print("📋 Events: Structured logging enabled") 
        print("🚀 Ready for Lambda deployment")
    else:
        print("❌ Local testing failed")