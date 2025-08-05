"""
Fantasy Football Draft Assistant - MCP Integration
Day 3: Integration layer for MCP servers (FantasyPros and others)

This module provides a unified interface to MCP servers, whether running
locally during development or deployed to AWS Bedrock AgentCore.
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import asyncio
import aiohttp

# For local development, we'll import and use the MCP server directly
# In production, this would make HTTP calls to the AgentCore-hosted MCP server
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from mcp_servers.fantasypros_mcp import (
        get_rankings, 
        get_projections, 
        get_adp_analysis,
        get_tier_breaks,
        get_superflex_strategy
    )
    LOCAL_MODE = True
except ImportError:
    LOCAL_MODE = False


class MCPClient:
    """
    Client for interacting with MCP servers
    
    During development: Uses local MCP functions directly
    In production: Makes HTTP calls to AgentCore-hosted MCP servers
    """
    
    def __init__(self, agent_url: str = None, auth_token: str = None):
        """
        Initialize MCP client
        
        Args:
            agent_url: URL of the AgentCore-hosted MCP server (for production)
            auth_token: Authentication token for AgentCore (for production)
        """
        self.agent_url = agent_url or os.getenv('AGENTCORE_MCP_URL')
        self.auth_token = auth_token or os.getenv('AGENTCORE_AUTH_TOKEN')
        self.session = None
        
        # Determine if we're in local or production mode
        # Force local mode for development if no agent URL is provided
        self.is_local = LOCAL_MODE or not self.agent_url
        
        if self.is_local:
            print("📍 Running in LOCAL mode - using direct MCP functions")
        else:
            print("☁️ Running in PRODUCTION mode - connecting to AgentCore")
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not self.is_local:
            # Create HTTP session for AgentCore calls
            headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call an MCP tool with the given parameters
        
        Args:
            tool_name: Name of the MCP tool to call
            **kwargs: Tool parameters
            
        Returns:
            Tool response as a dictionary
        """
        if self.is_local:
            # Local mode - call functions directly
            tool_map = {
                'get_rankings': get_rankings,
                'get_projections': get_projections,
                'get_adp_analysis': get_adp_analysis,
                'get_tier_breaks': get_tier_breaks,
                'get_superflex_strategy': get_superflex_strategy
            }
            
            if tool_name in tool_map:
                return tool_map[tool_name](**kwargs)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        
        else:
            # Production mode - make HTTP call to AgentCore
            if not self.session:
                raise RuntimeError("MCPClient not initialized properly")
            
            payload = {
                "tool": tool_name,
                "parameters": kwargs
            }
            
            try:
                async with self.session.post(f"{self.agent_url}/mcp", json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"MCP call failed: {response.status}"}
            except Exception as e:
                return {"error": f"MCP call error: {str(e)}"}
    
    async def get_rankings(self, scoring_format: str = "half_ppr", 
                          league_type: str = "superflex",
                          position: str = None,
                          limit: int = 50) -> Dict[str, Any]:
        """Get consensus rankings from FantasyPros MCP server"""
        return await self.call_tool(
            "get_rankings",
            scoring_format=scoring_format,
            league_type=league_type,
            position=position,
            limit=limit
        )
    
    async def get_projections(self, player_names: List[str],
                             week: str = "season",
                             scoring_format: str = "half_ppr") -> Dict[str, Any]:
        """Get player projections from FantasyPros MCP server"""
        return await self.call_tool(
            "get_projections",
            player_names=player_names,
            week=week,
            scoring_format=scoring_format
        )
    
    async def get_adp_analysis(self, current_pick: int,
                               available_players: List[str],
                               scoring_format: str = "half_ppr") -> Dict[str, Any]:
        """Get ADP-based value analysis from FantasyPros MCP server"""
        return await self.call_tool(
            "get_adp_analysis",
            current_pick=current_pick,
            available_players=available_players,
            scoring_format=scoring_format
        )
    
    async def get_tier_breaks(self, position: str,
                             scoring_format: str = "half_ppr",
                             league_type: str = "superflex") -> Dict[str, Any]:
        """Get tier analysis for a position from FantasyPros MCP server"""
        return await self.call_tool(
            "get_tier_breaks",
            position=position,
            scoring_format=scoring_format,
            league_type=league_type
        )
    
    async def get_superflex_strategy(self) -> Dict[str, Any]:
        """Get SUPERFLEX-specific strategy advice"""
        return await self.call_tool("get_superflex_strategy")


# Enhanced Rankings Manager that integrates MCP data
class EnhancedRankingsManager:
    """
    Enhanced rankings manager that combines Sleeper data with MCP server data
    """
    
    def __init__(self, sleeper_client, mcp_client: MCPClient):
        self.sleeper_client = sleeper_client
        self.mcp_client = mcp_client
        self.merged_data = {}
    
    async def get_enhanced_player_data(self, player_name: str) -> Dict[str, Any]:
        """
        Get comprehensive player data combining Sleeper and MCP sources
        
        Args:
            player_name: Player name to look up
            
        Returns:
            Enhanced player data with rankings, projections, and analysis
        """
        # Get base player data from Sleeper
        players = await self.sleeper_client.get_all_players()
        
        # Find player in Sleeper database
        player_data = None
        player_id = None
        for pid, pdata in players.items():
            full_name = f"{pdata.get('first_name', '')} {pdata.get('last_name', '')}".strip()
            if full_name.lower() == player_name.lower():
                player_data = pdata
                player_id = pid
                break
        
        if not player_data:
            return {"error": f"Player {player_name} not found"}
        
        # Get MCP rankings data
        rankings = await self.mcp_client.get_rankings(limit=200)
        
        # Find player in rankings
        player_ranking = None
        if 'players' in rankings:
            for p in rankings['players']:
                if p['name'].lower() == player_name.lower():
                    player_ranking = p
                    break
        
        # Get projections
        projections = await self.mcp_client.get_projections([player_name])
        player_projection = projections.get('players', {}).get(player_name, {})
        
        # Merge all data
        enhanced_data = {
            'player_id': player_id,
            'name': player_name,
            'team': player_data.get('team'),
            'positions': player_data.get('fantasy_positions', []),
            'age': player_data.get('age'),
            'years_exp': player_data.get('years_exp'),
            
            # Rankings data
            'sleeper_rank': player_data.get('search_rank'),
            'fantasypros_rank': player_ranking.get('rank') if player_ranking else None,
            'adp': player_ranking.get('adp') if player_ranking else None,
            'tier': player_ranking.get('tier') if player_ranking else None,
            
            # Projections
            'projections': player_projection,
            
            # Status
            'injury_status': player_data.get('injury_status'),
            'active': player_data.get('active', True)
        }
        
        return enhanced_data
    
    async def get_draft_recommendations(self, current_pick: int, 
                                      available_player_ids: List[str],
                                      roster_needs: Dict[str, int]) -> Dict[str, Any]:
        """
        Get AI-powered draft recommendations combining all data sources
        
        Args:
            current_pick: Current draft pick number
            available_player_ids: List of available Sleeper player IDs
            roster_needs: Dict of position -> number needed
            
        Returns:
            Comprehensive recommendations with reasoning
        """
        # Get player names for available players
        players = await self.sleeper_client.get_all_players()
        available_names = []
        
        for player_id in available_player_ids[:50]:  # Top 50 available
            if player_id in players:
                player = players[player_id]
                name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
                available_names.append(name)
        
        # Get ADP analysis from MCP
        adp_analysis = await self.mcp_client.get_adp_analysis(
            current_pick=current_pick,
            available_players=available_names
        )
        
        # Get tier breaks for needed positions
        tier_analysis = {}
        for position in roster_needs.keys():
            if position in ['QB', 'RB', 'WR', 'TE']:
                tier_data = await self.mcp_client.get_tier_breaks(position)
                tier_analysis[position] = tier_data
        
        # Get SUPERFLEX strategy
        strategy = await self.mcp_client.get_superflex_strategy()
        
        return {
            'current_pick': current_pick,
            'best_values': adp_analysis.get('value_picks', [])[:5],
            'position_recommendations': self._analyze_roster_needs(
                roster_needs, tier_analysis, strategy
            ),
            'overall_recommendation': self._generate_recommendation(
                adp_analysis, roster_needs, strategy
            )
        }
    
    def _analyze_roster_needs(self, roster_needs: Dict[str, int], 
                             tier_analysis: Dict[str, Any],
                             strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze roster needs based on tiers and strategy"""
        recommendations = []
        
        for position, needed in roster_needs.items():
            if needed > 0 and position in tier_analysis:
                tiers = tier_analysis[position].get('tiers', [])
                if tiers:
                    recommendations.append({
                        'position': position,
                        'needed': needed,
                        'next_tier_drop': tiers[0]['count'] if tiers else 0,
                        'urgency': 'HIGH' if needed >= 2 else 'MEDIUM'
                    })
        
        return sorted(recommendations, key=lambda x: x['urgency'], reverse=True)
    
    def _generate_recommendation(self, adp_analysis: Dict[str, Any],
                                roster_needs: Dict[str, int],
                                strategy: Dict[str, Any]) -> str:
        """Generate overall draft recommendation"""
        best_value = adp_analysis.get('best_value')
        
        if best_value:
            return f"RECOMMENDED: {best_value['name']} ({best_value['position']}) - {best_value['recommendation']}"
        elif roster_needs.get('QB', 0) > 0:
            return "RECOMMENDED: Target a QB soon (SUPERFLEX value)"
        else:
            return "RECOMMENDED: Best player available strategy"


# Test function
async def test_mcp_integration():
    """Test MCP integration with mock data"""
    print("🧪 Testing MCP Integration...")
    
    async with MCPClient() as mcp:
        # Test rankings
        print("\n📊 Testing Rankings...")
        rankings = await mcp.get_rankings(position="QB", limit=5)
        print(json.dumps(rankings, indent=2))
        
        # Test projections
        print("\n📈 Testing Projections...")
        projections = await mcp.get_projections(["Josh Allen", "Lamar Jackson"])
        print(json.dumps(projections, indent=2))
        
        # Test ADP analysis
        print("\n💰 Testing ADP Analysis...")
        adp = await mcp.get_adp_analysis(
            current_pick=25,
            available_players=["Josh Allen", "Patrick Mahomes", "Dak Prescott"]
        )
        print(json.dumps(adp, indent=2))
        
        # Test SUPERFLEX strategy
        print("\n🏈 Testing SUPERFLEX Strategy...")
        strategy = await mcp.get_superflex_strategy()
        print(json.dumps(strategy, indent=2))


if __name__ == "__main__":
    # Load environment
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    load_dotenv()
    
    # Run test
    asyncio.run(test_mcp_integration())