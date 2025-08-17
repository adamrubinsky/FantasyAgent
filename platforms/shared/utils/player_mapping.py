"""
Player Mapping Utility

This module provides utilities for cross-referencing players between different
fantasy football platforms using the unified player mapping file.

Key Benefits:
- Solves ID mismatch issues between Sleeper, FantasyPros, Yahoo, ESPN
- Enables robust player filtering for draft recommendations
- Provides fast lookups for player identification
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set

class PlayerMapper:
    """
    Utility class for managing player ID mappings across multiple fantasy platforms.
    
    This class loads the unified player mapping file and provides methods to:
    1. Convert between different platform IDs
    2. Get comprehensive player information
    3. Filter players based on drafted status
    4. Normalize player names for consistent matching
    """
    
    def __init__(self):
        """Initialize the player mapper by loading the unified mapping file."""
        self.mapping_file = Path(__file__).parent.parent / "data" / "player_id_mapping.json"
        self.player_mapping = {}
        self.name_to_sleeper_id = {}  # Quick lookup by normalized name
        self.fantasypros_to_sleeper = {}  # Quick lookup by FantasyPros ID
        
        self._load_mapping()
    
    def _load_mapping(self):
        """
        Load the unified player mapping from JSON file into memory.
        Creates lookup dictionaries for fast access by different identifiers.
        """
        try:
            if not self.mapping_file.exists():
                print(f"❌ Player mapping file not found: {self.mapping_file}")
                print("💡 Run scripts/create_player_mapping.py to generate it")
                return
            
            with open(self.mapping_file, 'r') as f:
                self.player_mapping = json.load(f)
            
            # Create reverse lookup dictionaries for fast access
            # Handle duplicate names by prioritizing active players and fantasy-relevant positions
            for sleeper_id, player_data in self.player_mapping.items():
                normalized_name = player_data.get('normalized_name', '').lower()
                if normalized_name:
                    # Check if this name already exists in our lookup
                    existing_id = self.name_to_sleeper_id.get(normalized_name)
                    
                    if existing_id:
                        # Handle duplicate names by choosing the better player
                        existing_player = self.player_mapping[existing_id]
                        current_player = player_data
                        
                        # Priority rules for duplicate names:
                        # 1. Active players over inactive
                        # 2. Fantasy-relevant positions (QB, RB, WR, TE) over others
                        # 3. Players with FantasyPros data (more fantasy-relevant)
                        
                        should_replace = False
                        
                        # Rule 1: Prefer active players
                        if current_player.get('active') and not existing_player.get('active'):
                            should_replace = True
                        elif not current_player.get('active') and existing_player.get('active'):
                            should_replace = False
                        else:
                            # Both have same active status, check other criteria
                            current_pos = current_player.get('position', '')
                            existing_pos = existing_player.get('position', '')
                            fantasy_positions = {'QB', 'RB', 'WR', 'TE'}
                            
                            # Rule 2: Prefer fantasy-relevant positions
                            if current_pos in fantasy_positions and existing_pos not in fantasy_positions:
                                should_replace = True
                            elif current_pos not in fantasy_positions and existing_pos in fantasy_positions:
                                should_replace = False
                            else:
                                # Rule 3: Prefer players with FantasyPros data
                                if current_player.get('fantasypros_id') and not existing_player.get('fantasypros_id'):
                                    should_replace = True
                        
                        if should_replace:
                            self.name_to_sleeper_id[normalized_name] = sleeper_id
                    else:
                        # First time seeing this name, just add it
                        self.name_to_sleeper_id[normalized_name] = sleeper_id
                
                # Map FantasyPros ID to Sleeper ID
                fp_id = player_data.get('fantasypros_id')
                if fp_id:
                    self.fantasypros_to_sleeper[str(fp_id)] = sleeper_id
            
            print(f"✅ Loaded player mapping: {len(self.player_mapping)} players")
            
        except Exception as e:
            print(f"❌ Error loading player mapping: {e}")
            self.player_mapping = {}
    
    def get_player_by_sleeper_id(self, sleeper_id: str) -> Optional[Dict]:
        """
        Get complete player information using Sleeper player ID.
        
        Args:
            sleeper_id: Sleeper platform player ID (e.g., '4984' for Josh Allen)
        
        Returns:
            Dictionary with all player information, or None if not found
        """
        return self.player_mapping.get(str(sleeper_id))
    
    def get_player_by_name(self, name: str) -> Optional[Dict]:
        """
        Get complete player information using player name.
        Uses normalized name matching for better accuracy.
        
        Args:
            name: Player name (e.g., "Josh Allen" or "patrick mahomes ii")
        
        Returns:
            Dictionary with all player information, or None if not found
        """
        normalized_name = self._normalize_name(name)
        sleeper_id = self.name_to_sleeper_id.get(normalized_name)
        if sleeper_id:
            return self.player_mapping[sleeper_id]
        return None
    
    def get_player_by_fantasypros_id(self, fp_id: int) -> Optional[Dict]:
        """
        Get complete player information using FantasyPros player ID.
        
        Args:
            fp_id: FantasyPros platform player ID (e.g., 17298 for Josh Allen)
        
        Returns:
            Dictionary with all player information, or None if not found
        """
        sleeper_id = self.fantasypros_to_sleeper.get(str(fp_id))
        if sleeper_id:
            return self.player_mapping[sleeper_id]
        return None
    
    def get_sleeper_ids_from_names(self, player_names: List[str]) -> Set[str]:
        """
        Convert a list of player names to Sleeper player IDs.
        Useful for filtering operations where we need to exclude drafted players.
        
        Args:
            player_names: List of player names to convert
        
        Returns:
            Set of Sleeper player IDs corresponding to the input names
        """
        sleeper_ids = set()
        for name in player_names:
            normalized_name = self._normalize_name(name)
            sleeper_id = self.name_to_sleeper_id.get(normalized_name)
            if sleeper_id:
                sleeper_ids.add(sleeper_id)
        return sleeper_ids
    
    def filter_available_players(self, all_players: List[Dict], drafted_sleeper_ids: Set[str]) -> List[Dict]:
        """
        Filter a list of players to exclude those that have been drafted.
        This is the core function that solves our original filtering problem.
        
        Args:
            all_players: List of player dictionaries (from FantasyPros rankings)
            drafted_sleeper_ids: Set of Sleeper IDs for players that have been drafted
        
        Returns:
            List of players excluding those that have been drafted
        """
        available_players = []
        
        for player in all_players:
            # Try to find this player's Sleeper ID using FantasyPros ID first
            fp_id = player.get('player_id')
            sleeper_id = None
            
            if fp_id:
                sleeper_id = self.fantasypros_to_sleeper.get(str(fp_id))
            
            # If no match by ID, try by name
            if not sleeper_id:
                player_name = player.get('player_name', '') or player.get('name', '')
                if player_name:
                    normalized_name = self._normalize_name(player_name)
                    sleeper_id = self.name_to_sleeper_id.get(normalized_name)
            
            # Include player if they haven't been drafted
            if sleeper_id not in drafted_sleeper_ids:
                available_players.append(player)
        
        return available_players
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize player names for consistent matching.
        Handles variations like Jr., III, punctuation, and case differences.
        
        Args:
            name: Raw player name
        
        Returns:
            Normalized name for consistent matching
        """
        if not name:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = name.lower().strip()
        
        # Remove common suffixes
        suffixes_to_remove = [' jr.', ' jr', ' sr.', ' sr', ' iii', ' ii', ' iv', ' v']
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        # Remove punctuation and normalize spaces
        normalized = normalized.replace('.', '').replace("'", '').replace('-', ' ')
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about the player mapping for debugging/monitoring.
        
        Returns:
            Dictionary with mapping statistics
        """
        total_players = len(self.player_mapping)
        matched_fp = len([p for p in self.player_mapping.values() if p.get('fantasypros_id')])
        with_yahoo = len([p for p in self.player_mapping.values() if p.get('yahoo_id')])
        with_espn = len([p for p in self.player_mapping.values() if p.get('espn_id')])
        
        return {
            "total_players": total_players,
            "fantasypros_matched": matched_fp,
            "yahoo_ids_available": with_yahoo,
            "espn_ids_available": with_espn,
            "match_rate": (matched_fp / total_players * 100) if total_players > 0 else 0
        }

# Create a global instance for easy importing
player_mapper = PlayerMapper()