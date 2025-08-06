#!/usr/bin/env python3
"""
Simple FantasyPros API Key Test Script
Run this periodically to check when your API key becomes active
"""

import asyncio
import aiohttp
import os
import ssl
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

async def test_fantasypros_api():
    """Test the FantasyPros API key activation status"""
    
    api_key = os.getenv('FANTASYPROS_API_KEY')
    if not api_key:
        print("❌ No FANTASYPROS_API_KEY found in .env.local")
        return False
    
    print(f"🔑 Testing FantasyPros API key: {api_key[:8]}...")
    
    # For development - disable SSL verification (common Mac issue)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    headers = {
        'x-api-key': api_key,
        'User-Agent': 'FantasyAgent/1.0'
    }
    
    test_endpoints = [
        {
            'name': 'Players',
            'url': 'https://api.fantasypros.com/public/v2/nfl/players',
            'description': 'Basic player data endpoint'
        },
        {
            'name': 'Rankings', 
            'url': 'https://api.fantasypros.com/public/v2/nfl/2025/consensus-rankings?position=QB&scoring=HALF',
            'description': 'QB rankings for superflex leagues'
        }
    ]
    
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        print("\n🧪 Testing FantasyPros API Endpoints:")
        print("=" * 50)
        
        all_success = True
        
        for endpoint in test_endpoints:
            print(f"\n📊 Testing {endpoint['name']}: {endpoint['description']}")
            
            try:
                async with session.get(endpoint['url']) as response:
                    print(f"   Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list):
                            print(f"   ✅ SUCCESS: Retrieved {len(data)} items")
                        elif isinstance(data, dict):
                            print(f"   ✅ SUCCESS: Retrieved data with {len(data)} keys")
                        else:
                            print(f"   ✅ SUCCESS: Retrieved data")
                            
                        # Show sample data for rankings
                        if 'rankings' in endpoint['url'] and isinstance(data, list) and data:
                            print(f"   📈 Sample: {data[0].get('player_name', 'Unknown')} - Rank {data[0].get('rank', 'N/A')}")
                            
                    elif response.status == 403:
                        error_data = await response.json()
                        if 'Missing Authentication Token' in str(error_data):
                            print(f"   ⏳ API key not yet active (403: Missing Authentication Token)")
                            all_success = False
                        else:
                            print(f"   ❌ Access denied: {error_data}")
                            all_success = False
                    else:
                        error_data = await response.text()
                        print(f"   ❌ Failed: {error_data}")
                        all_success = False
                        
            except Exception as e:
                print(f"   ❌ Error: {e}")
                all_success = False
        
        print("\n" + "=" * 50)
        if all_success:
            print("🎉 FantasyPros API is ACTIVE and working!")
            print("✅ You can now use live rankings in the draft assistant")
            print("\n🚀 Run this to test with live data:")
            print("   python main.py available -p QB --enhanced")
        else:
            print("⏳ FantasyPros API key is not yet active")
            print("💡 Try running this script again in 10-15 minutes")
            print("📧 Sometimes there's a delay after the activation email")
            
        return all_success

if __name__ == "__main__":
    asyncio.run(test_fantasypros_api())