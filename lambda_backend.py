#!/usr/bin/env python3
"""
Simple Lambda backend for Fantasy Draft Assistant
Interim solution while AgentCore deployment is being resolved
"""

import json
import asyncio
from typing import Dict, Any

def lambda_handler(event, context):
    """AWS Lambda handler for Fantasy Draft Assistant"""
    
    try:
        # Parse the request
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event
            
        action = body.get('action', 'test')
        
        # Simple responses for each action
        if action == 'test':
            response_data = {
                'success': True,
                'message': 'Fantasy Draft Assistant Lambda is working!',
                'capabilities': ['draft_recommendations', 'player_analysis'],
                'league_format': 'SUPERFLEX supported',
                'status': 'Lambda backend active'
            }
            
        elif action == 'draft_advice':
            # Mock draft advice response
            context_data = body.get('context', {})
            response_data = {
                'success': True,
                'advice': {
                    'primary_pick': 'Josh Allen (QB)',
                    'reasoning': 'SUPERFLEX format - QBs have premium value. Allen is elite dual-threat.',
                    'alternatives': ['Lamar Jackson (QB)', 'Justin Jefferson (WR)', 'Christian McCaffrey (RB)'],
                    'position_need': 'QB priority in SUPERFLEX',
                    'confidence': 95
                },
                'round': context_data.get('round', 1),
                'pick': context_data.get('pick', 1)
            }
            
        elif action == 'available_players':
            # Mock available players
            response_data = {
                'success': True,
                'players': [
                    {'name': 'Josh Allen', 'position': 'QB', 'team': 'BUF', 'rank': 1, 'adp': 2.1},
                    {'name': 'Lamar Jackson', 'position': 'QB', 'team': 'BAL', 'rank': 2, 'adp': 3.2},
                    {'name': 'Justin Jefferson', 'position': 'WR', 'team': 'MIN', 'rank': 3, 'adp': 1.1},
                    {'name': 'Christian McCaffrey', 'position': 'RB', 'team': 'SF', 'rank': 4, 'adp': 1.8},
                    {'name': 'Dak Prescott', 'position': 'QB', 'team': 'DAL', 'rank': 5, 'adp': 4.5}
                ],
                'total_available': 200,
                'superflex_note': 'QBs ranked higher due to SUPERFLEX format'
            }
            
        elif action == 'chat':
            # Mock AI chat response
            message = body.get('message', '')
            response_data = {
                'success': True,
                'response': f"Based on SUPERFLEX league format, I'd recommend prioritizing elite QBs early. Josh Allen and Lamar Jackson should be targets in rounds 1-2. Your message: '{message}'",
                'agent_type': 'Fantasy AI Assistant',
                'context_understood': True
            }
            
        else:
            response_data = {
                'success': False,
                'error': f'Unknown action: {action}',
                'supported_actions': ['test', 'draft_advice', 'available_players', 'chat']
            }
        
        # Return Lambda response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'error_type': 'Lambda execution error'
            })
        }

# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        'body': json.dumps({
            'action': 'test'
        })
    }
    
    result = lambda_handler(test_event, {})
    print(json.dumps(result, indent=2))