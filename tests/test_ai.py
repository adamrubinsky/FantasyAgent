#!/usr/bin/env python3
"""
Quick AI test script to verify Claude integration
Run this after adding your API key to .env.local
"""

import asyncio
import os
from dotenv import load_dotenv
from core.ai_assistant import FantasyAIAssistant

# Load environment
load_dotenv('.env.local')
load_dotenv()

async def test_ai_features():
    """Test all AI features quickly"""
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your-claude-api-key-here':
        print("❌ Please add your ANTHROPIC_API_KEY to .env.local first!")
        print("   Edit .env.local and replace 'your-claude-api-key-here' with your actual key")
        return
    
    print("🤖 Testing AI features...")
    print(f"API Key: {api_key[:20]}...{api_key[-10:]}")  # Show partial key for verification
    
    assistant = FantasyAIAssistant()
    
    if not assistant.has_ai:
        print("❌ AI not initialized properly")
        return
    
    print("✅ AI initialized successfully!")
    
    # Test 1: Simple question
    print("\n🧪 Test 1: Simple Question")
    try:
        response = await assistant.ask("Is Josh Allen worth a first round pick in SUPERFLEX?")
        print("✅ AI Response received!")
        print(f"Response preview: {response[:150]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Player comparison
    print("\n🧪 Test 2: Player Comparison")
    try:
        comparison = await assistant.compare_players("Josh Allen", "Lamar Jackson")
        print("✅ Comparison received!")
        print(f"Comparison preview: {comparison[:150]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🎉 AI testing complete! If you see responses above, everything is working!")

if __name__ == "__main__":
    asyncio.run(test_ai_features())