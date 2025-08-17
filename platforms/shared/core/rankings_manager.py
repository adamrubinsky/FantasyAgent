"""
Fantasy Football Draft Assistant - Rankings Manager
Day 3 (Aug 7): Integrate rankings from multiple sources
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
import asyncio
from rich.console import Console

from api.sleeper_client import SleeperClient


class RankingsManager:
    """
    Manages player rankings from multiple sources
    
    Key Features:
    - Integrates Sleeper's built-in rankings (search_rank)
    - Supports multiple scoring formats (Standard, Half-PPR, PPR, SUPERFLEX)
    - Caches rankings with configurable TTL
    - Merges rankings from different sources
    - Provides ADP (Average Draft Position) data
    - Handles SUPERFLEX QB value adjustments
    
    This is critical for draft day - rankings drive recommendations!
    """
    
    def __init__(self, scoring_format: str = "half_ppr", league_type: str = "superflex"):
        self.console = Console()
        self.scoring_format = scoring_format.lower()
        self.league_type = league_type.lower()
        
        # Cache directory for rankings data
        self.cache_dir = Path(__file__).parent.parent / "data"
        self.rankings_cache_file = self.cache_dir / "rankings_cache.json"
        self.adp_cache_file = self.cache_dir / "adp_cache.json"
        
        # Cache TTL (1 hour for rankings, 24 hours for ADP)
        self.rankings_ttl = timedelta(hours=1)
        self.adp_ttl = timedelta(hours=24)
        
        # Store merged rankings in memory
        self.merged_rankings: Dict[str, Any] = {}
        self.last_update: Optional[datetime] = None
        
    async def get_sleeper_rankings(self, client: SleeperClient) -> Dict[str, int]:
        """
        Extract rankings from Sleeper's player database
        
        Sleeper provides a 'search_rank' field for each player which represents
        their overall fantasy ranking. Lower numbers = better players.
        
        Args:
            client: SleeperClient instance
            
        Returns:
            Dict mapping player_id to rank
        """
        # Get all players with their search ranks
        players = await client.get_all_players()
        
        rankings = {}
        for player_id, player_data in players.items():
            # Only include active players with rankings
            if player_data.get('active') and player_data.get('search_rank'):
                rankings[player_id] = player_data['search_rank']
        
        return rankings
    
    def adjust_superflex_rankings(self, rankings: Dict[str, int], players: Dict[str, Any]) -> Dict[str, int]:
        """
        Adjust rankings for SUPERFLEX leagues where QBs are more valuable
        
        In SUPERFLEX leagues, QBs should be ranked much higher because you can
        start 2 QBs. This method boosts QB rankings appropriately.
        
        Args:
            rankings: Base rankings dict
            players: Full player data dict
            
        Returns:
            Adjusted rankings dict
        """
        if self.league_type != "superflex":
            return rankings
        
        # Create a list of (player_id, rank) tuples for sorting
        ranked_players = []
        for player_id, rank in rankings.items():
            if player_id in players:
                player = players[player_id]
                positions = player.get('fantasy_positions', [])
                is_qb = 'QB' in positions
                
                # Boost QB rankings in SUPERFLEX
                if is_qb and rank > 10:  # Don't adjust top 10 (already high)
                    # Move QBs up by ~40% in rankings
                    adjusted_rank = int(rank * 0.6)
                else:
                    adjusted_rank = rank
                
                ranked_players.append((player_id, adjusted_rank, is_qb))
        
        # Sort by adjusted rank
        ranked_players.sort(key=lambda x: x[1])
        
        # Reassign ranks to maintain order without gaps
        adjusted_rankings = {}
        for i, (player_id, _, _) in enumerate(ranked_players, 1):
            adjusted_rankings[player_id] = i
        
        return adjusted_rankings
    
    async def load_adp_data(self) -> Dict[str, float]:
        """
        Load or fetch ADP (Average Draft Position) data
        
        ADP shows where players are typically being drafted across all leagues.
        This helps identify value picks (players available later than their ADP).
        
        Returns:
            Dict mapping player_id to average draft position
        """
        # Check cache first
        if self.adp_cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(self.adp_cache_file.stat().st_mtime)
            if cache_age < self.adp_ttl:
                with open(self.adp_cache_file, 'r') as f:
                    self.console.print("📊 Loaded ADP data from cache", style="dim")
                    return json.load(f)
        
        # For now, we'll simulate ADP based on Sleeper rankings
        # In production, this would fetch from FantasyPros or another source
        self.console.print("🔄 Generating ADP data from rankings...", style="yellow")
        
        # We'll use Sleeper rankings as a proxy for ADP
        # Real implementation would fetch from external source
        adp_data = {}
        
        # Save to cache
        with open(self.adp_cache_file, 'w') as f:
            json.dump(adp_data, f, indent=2)
        
        return adp_data
    
    async def update_rankings(self, client: SleeperClient, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Update rankings from all sources and merge them
        
        This is the main method that:
        1. Fetches rankings from Sleeper
        2. Adjusts for SUPERFLEX if needed
        3. Loads ADP data
        4. Merges everything into a unified ranking system
        5. Caches the results
        
        Args:
            client: SleeperClient instance
            force_refresh: Force update even if cache is fresh
            
        Returns:
            Merged rankings dict with comprehensive player data
        """
        # Check cache freshness
        if not force_refresh and self.rankings_cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(self.rankings_cache_file.stat().st_mtime)
            if cache_age < self.rankings_ttl:
                with open(self.rankings_cache_file, 'r') as f:
                    self.merged_rankings = json.load(f)
                    self.last_update = datetime.fromisoformat(self.merged_rankings.get('last_update', ''))
                    self.console.print(f"📊 Loaded rankings from cache (updated {cache_age.seconds//60} minutes ago)", style="dim")
                    return self.merged_rankings
        
        self.console.print("🔄 Updating rankings from all sources...", style="yellow")
        
        # Get player database
        players = await client.get_all_players()
        
        # Get Sleeper rankings
        sleeper_rankings = await self.get_sleeper_rankings(client)
        self.console.print(f"✅ Loaded {len(sleeper_rankings)} player rankings from Sleeper")
        
        # Adjust for SUPERFLEX
        adjusted_rankings = self.adjust_superflex_rankings(sleeper_rankings, players)
        if self.league_type == "superflex":
            self.console.print("✅ Adjusted rankings for SUPERFLEX league (QBs boosted)")
        
        # Load ADP data
        adp_data = await self.load_adp_data()
        
        # Merge all data
        self.merged_rankings = {
            'last_update': datetime.now().isoformat(),
            'scoring_format': self.scoring_format,
            'league_type': self.league_type,
            'players': {}
        }
        
        # Build comprehensive player entries
        for player_id, rank in adjusted_rankings.items():
            if player_id in players:
                player = players[player_id]
                
                # Create merged player data
                self.merged_rankings['players'][player_id] = {
                    'player_id': player_id,
                    'name': f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
                    'team': player.get('team'),
                    'positions': player.get('fantasy_positions', []),
                    'age': player.get('age'),
                    'years_exp': player.get('years_exp'),
                    
                    # Rankings data
                    'overall_rank': rank,
                    'position_rank': None,  # TODO: Calculate position-specific ranks
                    'sleeper_rank': sleeper_rankings.get(player_id),
                    'adp': adp_data.get(player_id),
                    
                    # Additional metadata
                    'injury_status': player.get('injury_status'),
                    'bye_week': None,  # TODO: Add bye week data
                    'projected_points': None,  # TODO: Add projections
                    
                    # Value indicators
                    'is_sleeper': rank > (adp_data.get(player_id, rank) + 20) if adp_data.get(player_id) else False,
                    'is_reach': rank < (adp_data.get(player_id, rank) - 20) if adp_data.get(player_id) else False,
                }
        
        # Calculate position ranks
        self._calculate_position_ranks()
        
        # Save to cache
        with open(self.rankings_cache_file, 'w') as f:
            json.dump(self.merged_rankings, f, indent=2)
        
        self.last_update = datetime.now()
        self.console.print(f"✅ Rankings updated successfully ({len(self.merged_rankings['players'])} players)")
        
        return self.merged_rankings
    
    def _calculate_position_ranks(self):
        """Calculate position-specific rankings for each player"""
        # Group players by position
        position_groups = {}
        
        for player_id, player_data in self.merged_rankings['players'].items():
            for position in player_data['positions']:
                if position not in position_groups:
                    position_groups[position] = []
                position_groups[position].append((player_id, player_data['overall_rank']))
        
        # Sort each position group and assign position ranks
        for position, players in position_groups.items():
            # Sort by overall rank
            players.sort(key=lambda x: x[1])
            
            # Assign position ranks
            for pos_rank, (player_id, _) in enumerate(players, 1):
                if self.merged_rankings['players'][player_id]['position_rank'] is None:
                    self.merged_rankings['players'][player_id]['position_rank'] = {}
                self.merged_rankings['players'][player_id]['position_rank'][position] = pos_rank
    
    def get_player_ranking_data(self, player_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive ranking data for a specific player
        
        Args:
            player_id: Sleeper player ID
            
        Returns:
            Player ranking data or None if not found
        """
        if not self.merged_rankings or 'players' not in self.merged_rankings:
            return None
        
        return self.merged_rankings['players'].get(player_id)
    
    def get_top_available_by_rank(self, available_players: List[str], position: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top available players sorted by overall rank
        
        Args:
            available_players: List of available player IDs
            position: Optional position filter
            limit: Number of players to return
            
        Returns:
            List of player ranking data sorted by rank
        """
        if not self.merged_rankings or 'players' not in self.merged_rankings:
            return []
        
        # Filter to available players
        available_with_ranks = []
        for player_id in available_players:
            if player_id in self.merged_rankings['players']:
                player_data = self.merged_rankings['players'][player_id]
                
                # Apply position filter if specified
                if position and position not in player_data['positions']:
                    continue
                
                available_with_ranks.append(player_data)
        
        # Sort by overall rank
        available_with_ranks.sort(key=lambda x: x['overall_rank'])
        
        return available_with_ranks[:limit]
    
    def identify_value_picks(self, available_players: List[str], threshold: int = 15) -> List[Dict[str, Any]]:
        """
        Identify players available later than their typical draft position
        
        Args:
            available_players: List of available player IDs
            threshold: How many picks later than ADP to consider "value"
            
        Returns:
            List of value pick players
        """
        value_picks = []
        
        for player_id in available_players:
            player_data = self.get_player_ranking_data(player_id)
            if player_data and player_data.get('adp'):
                # Calculate value differential
                current_pick = len(available_players)  # Rough estimate
                value_diff = current_pick - player_data['adp']
                
                if value_diff >= threshold:
                    player_data['value_differential'] = value_diff
                    value_picks.append(player_data)
        
        # Sort by value differential (biggest values first)
        value_picks.sort(key=lambda x: x['value_differential'], reverse=True)
        
        return value_picks


# Test function for development
async def test_rankings_manager():
    """Test the rankings manager with real data"""
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    if not username or not league_id:
        print("❌ Please set SLEEPER_USERNAME and SLEEPER_LEAGUE_ID in .env file")
        return
    
    async with SleeperClient(username=username, league_id=league_id) as client:
        # Create rankings manager for SUPERFLEX league
        manager = RankingsManager(scoring_format="half_ppr", league_type="superflex")
        
        # Update rankings
        await manager.update_rankings(client)
        
        # Test getting top QBs
        all_player_ids = list(manager.merged_rankings['players'].keys())
        top_qbs = manager.get_top_available_by_rank(all_player_ids[:100], position="QB", limit=5)
        
        print("\n🏈 Top 5 QBs in SUPERFLEX rankings:")
        for qb in top_qbs:
            print(f"  {qb['overall_rank']}. {qb['name']} - {qb['team']}")
            if qb.get('position_rank', {}).get('QB'):
                print(f"     QB#{qb['position_rank']['QB']}")


if __name__ == "__main__":
    # Run test when script is executed directly
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    load_dotenv()
    
    asyncio.run(test_rankings_manager())