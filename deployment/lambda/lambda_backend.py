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
            # Smart AI chat response based on message content
            message = body.get('message', '').lower()
            
            # Provide context-aware responses
            if 'after' in message and 'qb' in message:
                response_text = "After securing your QBs, target elite WRs like CeeDee Lamb, Tyreek Hill, or A.J. Brown. Then grab a top RB like Breece Hall, Bijan Robinson, or Jonathan Taylor. Don't forget a TE - Travis Kelce or Sam LaPorta are great picks."
            elif 'player' in message or 'who should' in message or 'pick' in message:
                response_text = "Top targets right now:\n• QBs: Josh Allen, Lamar Jackson, Dak Prescott\n• RBs: Christian McCaffrey, Breece Hall, Bijan Robinson\n• WRs: CeeDee Lamb, Tyreek Hill, Justin Jefferson\n• TEs: Travis Kelce, Sam LaPorta, Mark Andrews"
            elif 'rb' in message or 'running back' in message:
                response_text = "Best available RBs:\n1. Christian McCaffrey (SF)\n2. Breece Hall (NYJ)\n3. Bijan Robinson (ATL)\n4. Jonathan Taylor (IND)\n5. Saquon Barkley (PHI)"
            elif 'wr' in message or 'receiver' in message:
                response_text = "Top WRs to target:\n1. CeeDee Lamb (DAL)\n2. Tyreek Hill (MIA)\n3. Justin Jefferson (MIN)\n4. A.J. Brown (PHI)\n5. Amon-Ra St. Brown (DET)"
            else:
                response_text = f"For SUPERFLEX: Prioritize 2 QBs early (Allen, Jackson, Prescott), then best RB/WR available. Specific question about '{body.get('message', '')}' - ask for player names or positions!"
            
            response_data = {
                'success': True,
                'response': response_text,
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