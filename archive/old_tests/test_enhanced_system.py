#!/usr/bin/env python3
"""
Test the enhanced recommendation system with all optimizations
"""

import requests
import time
import json

def test_enhanced_recommendations():
    print('🧪 TESTING ENHANCED RECOMMENDATIONS')
    print('=' * 50)
    
    # Connect to draft
    print('\nConnecting to mock draft...')
    response = requests.post('http://localhost:3000/api/start-draft-monitoring',
                             json={'draft_url': 'https://sleeper.com/draft/nfl/1260758387386241025',
                                   'user_roster_id': 5})
    
    if response.status_code == 200:
        print('✅ Connected successfully')
    else:
        print(f'❌ Connection failed: {response.status_code}')
        return
    
    # Wait for connection to stabilize
    time.sleep(2)
    
    # Test queries to see enhanced features
    test_queries = [
        'Who should I draft at pick 92?',
        'Are there any value picks falling below ADP?',
        'Should I stack a WR with my QB Burrow?',
        'What round 8 strategy should I follow?'
    ]
    
    for query in test_queries:
        print(f'\n📝 Query: "{query}"')
        print('-' * 50)
        
        start = time.time()
        try:
            response = requests.post('http://localhost:3000/api/chat',
                                    json={'message': query},
                                    timeout=45)
            elapsed = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                resp = data.get('response', '')
                
                # Check for new optimization features in response
                features = {
                    'ADP/Value': any(word in resp.lower() for word in ['adp', 'value', 'falling', 'spots']),
                    'Stacking': 'stack' in resp.lower(),
                    'Round Strategy': any(word in resp.lower() for word in ['round', 'priority', 'strategy']),
                    'Run Detection': 'run' in resp.lower(),
                    'Tier Analysis': 'tier' in resp.lower(),
                    'Keeper Value': 'keeper' in resp.lower()
                }
                
                print(f'⏱️  Response Time: {elapsed:.1f}s')
                print(f'✅ Enhanced Features Detected:')
                for feature, detected in features.items():
                    status = "✓" if detected else "✗"
                    print(f'   {status} {feature}')
                
                # Show response preview
                print(f'\n📄 Response Preview (first 600 chars):')
                print('-' * 40)
                print(resp[:600])
                
            else:
                print(f'❌ Request failed: {response.status_code}')
                
        except requests.exceptions.Timeout:
            print(f'⏱️  TIMEOUT after 45 seconds')
        except Exception as e:
            print(f'❌ Error: {e}')
    
    # Summary
    print('\n' + '=' * 50)
    print('📊 TEST SUMMARY')
    print('=' * 50)
    print('Check if the responses now include:')
    print('  1. ADP value detection (players falling)')
    print('  2. Round-specific strategy guidance')
    print('  3. Stacking recommendations')
    print('  4. Positional run awareness')
    print('  5. Faster response times (<15s)')

if __name__ == "__main__":
    test_enhanced_recommendations()