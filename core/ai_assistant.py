"""
Fantasy Football Draft Assistant - AI Assistant with Claude
Day 4 (Aug 8): Natural language analysis and conversational interface

This module provides the AI brain of the draft assistant, capable of:
- Natural language queries about players and strategy
- Player comparisons with detailed reasoning
- Context-aware draft recommendations
- Conversational interface (ready for web/AgentCore deployment)
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# Anthropic Claude integration
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("⚠️ Anthropic package not installed. Install with: pip install anthropic")

from core.league_context import league_manager
from core.mcp_integration import MCPClient
from api.sleeper_client import SleeperClient


class FantasyAIAssistant:
    """
    AI-powered fantasy football assistant using Claude
    
    Provides conversational interface for draft analysis, player comparisons,
    and strategic advice. Designed to work both in CLI and future web interface.
    """
    
    def __init__(self, anthropic_api_key: str = None):
        """
        Initialize AI assistant
        
        Args:
            anthropic_api_key: Claude API key (or from environment)
        """
        self.api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key and HAS_ANTHROPIC:
            print("⚠️ No ANTHROPIC_API_KEY found. AI features will be limited.")
        
        # Initialize Claude client
        if HAS_ANTHROPIC and self.api_key:
            self.claude = anthropic.AsyncAnthropic(api_key=self.api_key)
            self.has_ai = True
        else:
            self.claude = None
            self.has_ai = False
        
        # Context for conversations
        self.conversation_history = []
        self.current_draft_context = {}
    
    def _build_system_prompt(self) -> str:
        """
        Build comprehensive system prompt with league context and current data
        """
        # Get current league context
        context = league_manager.get_current_context()
        
        if context:
            league_info = f"""
LEAGUE CONTEXT:
- League: {context.league_name}
- Platform: {context.platform.title()}
- Scoring: {context.scoring_format.upper()} ({context.receptions} points per reception)
- Teams: {context.total_teams}
- Format: {'SUPERFLEX' if context.is_superflex else 'Standard'} ({context.total_qb_spots} QB spots)
- Roster: {', '.join(context.roster_positions)}
- Position Scarcity: {context.get_position_scarcity()}
"""
        else:
            league_info = "LEAGUE CONTEXT: Using default SUPERFLEX Half-PPR settings"
        
        return f"""You are an expert fantasy football draft assistant with deep knowledge of player analysis, draft strategy, and league dynamics.

{league_info}

CURRENT DATE: {datetime.now().strftime('%B %d, %Y')}
DRAFT DATE: August 14, 2025

YOUR EXPERTISE:
- Player analysis and comparisons
- Draft strategy optimization
- Injury and trend analysis
- Matchup evaluation
- Roster construction
- Value identification
- Positional scarcity understanding

PERSONALITY:
- Direct and analytical, but conversational
- Focus on actionable insights
- Explain your reasoning clearly
- Consider multiple factors in recommendations
- Acknowledge uncertainty when appropriate
- Be enthusiastic about good picks/strategy

RESPONSE STYLE:
- Start with a clear recommendation or answer
- Provide 2-3 key supporting points
- Include relevant stats or context when helpful
- End with actionable advice
- Use fantasy football terminology appropriately
- Keep responses concise but comprehensive (2-4 paragraphs max)

IMPORTANT CONSIDERATIONS:
- SUPERFLEX leagues make QBs much more valuable
- Position scarcity varies by league settings
- ADP vs current availability creates value opportunities
- Injury status and preseason performance matter
- Playoff schedule (weeks 14-16) is crucial for late-season players
- Keeper/dynasty vs redraft strategies differ significantly

Always consider the user's specific league context in your analysis."""

    async def ask(self, question: str, context: Dict[str, Any] = None) -> str:
        """
        Answer any fantasy football question with AI analysis
        
        Args:
            question: User's question in natural language
            context: Additional context (draft pick, available players, etc.)
            
        Returns:
            AI-generated response with analysis and recommendations
        """
        if not self.has_ai:
            return self._fallback_response(question)
        
        # Build comprehensive context
        full_context = await self._gather_context(context or {})
        
        # Create the prompt
        messages = [
            {
                "role": "user",
                "content": f"""
QUESTION: {question}

CURRENT CONTEXT:
{json.dumps(full_context, indent=2)}

Please provide a detailed analysis and recommendation based on the current league settings, available data, and fantasy football best practices.
"""
            }
        ]
        
        try:
            # Call Claude API
            response = await self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.3,
                system=self._build_system_prompt(),
                messages=messages
            )
            
            ai_response = response.content[0].text
            
            # Store in conversation history for context
            self.conversation_history.append({
                "question": question,
                "response": ai_response,
                "timestamp": datetime.now().isoformat(),
                "context": full_context
            })
            
            return ai_response
            
        except Exception as e:
            return f"❌ AI Error: {str(e)}\n\nFalling back to basic analysis..."
    
    async def compare_players(self, player1: str, player2: str, context: Dict[str, Any] = None) -> str:
        """
        Compare two players with detailed AI analysis
        
        Args:
            player1: First player name
            player2: Second player name
            context: Additional context (draft position, team needs, etc.)
            
        Returns:
            Detailed comparison with recommendation
        """
        if not self.has_ai:
            return self._fallback_comparison(player1, player2)
        
        # Get player data
        player_data = await self._get_player_comparison_data([player1, player2])
        full_context = await self._gather_context(context or {})
        
        question = f"Compare {player1} vs {player2} for my draft. Who should I pick and why?"
        
        messages = [
            {
                "role": "user", 
                "content": f"""
PLAYER COMPARISON REQUEST: {player1} vs {player2}

PLAYER DATA:
{json.dumps(player_data, indent=2)}

DRAFT CONTEXT:
{json.dumps(full_context, indent=2)}

Please provide a detailed head-to-head comparison considering:
1. Current rankings and ADP value
2. Projected performance and ceiling/floor
3. Injury risk and reliability  
4. Schedule and playoff matchups
5. Fit with my league settings
6. Clear recommendation with reasoning

Format as: RECOMMENDATION, KEY FACTORS, ANALYSIS
"""
            }
        ]
        
        try:
            response = await self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1200,
                temperature=0.3,
                system=self._build_system_prompt(),
                messages=messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"❌ AI Error: {str(e)}\n\n{self._fallback_comparison(player1, player2)}"
    
    async def get_draft_recommendation(self, current_pick: int, available_players: List[str] = None, context: Dict[str, Any] = None) -> str:
        """
        Get AI-powered draft recommendation for current pick
        
        Args:
            current_pick: Current draft pick number
            available_players: List of available player names
            context: Additional context (team needs, strategy, etc.)
            
        Returns:
            Detailed recommendation with reasoning
        """
        if not self.has_ai:
            return self._fallback_recommendation(current_pick)
        
        # Gather comprehensive data
        full_context = await self._gather_context(context or {})
        full_context['current_pick'] = current_pick
        
        # Get available players data if not provided
        if not available_players:
            available_players = await self._get_top_available_players(current_pick, limit=20)
        
        # Get detailed analysis of top options
        player_analysis = await self._get_player_comparison_data(available_players[:10])
        
        messages = [
            {
                "role": "user",
                "content": f"""
DRAFT RECOMMENDATION REQUEST for Pick #{current_pick}

AVAILABLE PLAYERS (Top 10):
{json.dumps(player_analysis, indent=2)}

DRAFT CONTEXT:
{json.dumps(full_context, indent=2)}

Please provide a draft recommendation considering:
1. Best value picks based on ADP
2. Positional needs and scarcity  
3. Tier breaks and falloffs
4. League-specific strategy
5. Risk/reward analysis
6. Alternative scenarios

Provide:
- PRIMARY RECOMMENDATION with clear reasoning
- 2-3 ALTERNATIVE OPTIONS
- STRATEGY NOTES for future picks
"""
            }
        ]
        
        try:
            response = await self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1200,
                temperature=0.3,
                system=self._build_system_prompt(),
                messages=messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"❌ AI Error: {str(e)}\n\n{self._fallback_recommendation(current_pick)}"
    
    async def _gather_context(self, additional_context: Dict[str, Any]) -> Dict[str, Any]:
        """Gather all relevant context for AI analysis"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "league": None,
            "draft_status": None,
            **additional_context
        }
        
        # Add league context
        league_context = league_manager.get_current_context()
        if league_context:
            context["league"] = {
                "name": league_context.league_name,
                "scoring": league_context.scoring_format,
                "teams": league_context.total_teams,
                "superflex": league_context.is_superflex,
                "qb_spots": league_context.total_qb_spots,
                "position_scarcity": league_context.get_position_scarcity()
            }
        
        return context
    
    async def _get_player_comparison_data(self, player_names: List[str]) -> Dict[str, Any]:
        """Get comprehensive data for player comparison"""
        data = {"players": {}}
        
        async with MCPClient() as mcp:
            # Get rankings for these players
            rankings = await mcp.get_rankings(limit=200)
            
            # Get projections
            projections = await mcp.get_projections(player_names)
            
            for name in player_names:
                player_info = {"name": name}
                
                # Find in rankings
                for player in rankings.get('players', []):
                    if player['name'].lower() == name.lower():
                        player_info.update({
                            "rank": player['rank'],
                            "adp": player['adp'],
                            "tier": player['tier'],
                            "position": player['position'],
                            "team": player['team']
                        })
                        break
                
                # Add projections
                if name in projections.get('players', {}):
                    player_info["projections"] = projections['players'][name]
                
                data["players"][name] = player_info
        
        return data
    
    async def _get_top_available_players(self, current_pick: int, limit: int = 20) -> List[str]:
        """Get top available players for current draft state"""
        try:
            # This would integrate with the draft monitor to get actual available players
            # For now, return mock data
            return [
                "Saquon Barkley", "Josh Allen", "CeeDee Lamb", "Justin Jefferson",
                "Lamar Jackson", "Tyreek Hill", "Jahmyr Gibbs", "Bijan Robinson",
                "Patrick Mahomes", "Dak Prescott"
            ][:limit]
        except Exception:
            return []
    
    def _fallback_response(self, question: str) -> str:
        """Fallback response when AI is not available"""
        return f"""
🤖 AI Assistant Unavailable

Your question: "{question}"

To get AI-powered analysis, please:
1. Install anthropic package: pip install anthropic
2. Set ANTHROPIC_API_KEY in your .env.local file
3. Get Claude API access at: https://console.anthropic.com/

For now, try these commands:
- python3 main.py rankings -p QB
- python3 main.py strategy
- python3 main.py value -p {85}
"""
    
    def _fallback_comparison(self, player1: str, player2: str) -> str:
        """Fallback comparison when AI is not available"""
        return f"""
🤖 AI Comparison Unavailable

Comparing: {player1} vs {player2}

For detailed player comparisons, enable AI features:
1. Set ANTHROPIC_API_KEY in .env.local
2. Run: python3 main.py compare "{player1}" "{player2}"

Basic analysis available with:
- python3 main.py rankings
- python3 main.py value -p [pick_number]
"""
    
    def _fallback_recommendation(self, current_pick: int) -> str:
        """Fallback recommendation when AI is not available"""
        return f"""
🤖 AI Recommendations Unavailable

For pick #{current_pick}, try:
- python3 main.py value -p {current_pick}
- python3 main.py rankings -p QB -l 10
- python3 main.py strategy

Enable AI for personalized recommendations:
1. Set ANTHROPIC_API_KEY in .env.local
2. Run: python3 main.py recommend -p {current_pick}
"""


# Test function
async def test_ai_assistant():
    """Test the AI assistant functionality"""
    assistant = FantasyAIAssistant()
    
    print("🤖 Testing AI Assistant...")
    
    # Test basic question
    response = await assistant.ask("Should I draft Josh Allen in the first round of a SUPERFLEX league?")
    print(f"\nQ: Should I draft Josh Allen in round 1?\nA: {response}")
    
    # Test comparison
    comparison = await assistant.compare_players("Josh Allen", "Lamar Jackson")
    print(f"\nComparison: Josh Allen vs Lamar Jackson\n{comparison}")
    
    # Test recommendation  
    recommendation = await assistant.get_draft_recommendation(current_pick=25)
    print(f"\nRecommendation for pick #25:\n{recommendation}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    load_dotenv()
    
    asyncio.run(test_ai_assistant())