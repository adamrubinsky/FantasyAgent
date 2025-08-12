#!/usr/bin/env python3
"""Quick test to see FantasyPros data structure"""

import asyncio
import sys
import os
from dotenv import load_dotenv
import json

sys.path.append('.')

from core.official_fantasypros import OfficialFantasyProsMCP

async def quick_test():
    """Quick test to see data structure"""
    
    # Load environment variables
    load_dotenv('.env.local')
    api_key = os.getenv('FANTASYPROS_API_KEY')
    
    if not api_key:
        print("❌ FANTASYPROS_API_KEY not found in .env.local")
        return
    
    client = OfficialFantasyProsMCP(api_key)
    
    # Get SUPERFLEX rankings
    print("Fetching SUPERFLEX rankings...")
    rankings = await client.get_rankings(
        sport="NFL",
        position="OP",  # SUPERFLEX
        scoring="HALF",
        limit=5  # Just get a few to see structure
    )
    
    if rankings and len(rankings) > 0:
        print(f"\nFetched {len(rankings)} players")
        print("\nFirst player structure:")
        print(json.dumps(rankings[0], indent=2))
        
        # Print available keys
        print("\nAvailable fields:")
        for key in rankings[0].keys():
            print(f"  - {key}: {rankings[0][key]}")
    else:
        print("No rankings fetched")

if __name__ == "__main__":
    asyncio.run(quick_test())