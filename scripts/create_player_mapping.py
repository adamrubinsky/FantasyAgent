#!/usr/bin/env python3
"""
Player ID Mapping Generator

This script creates a unified mapping file that cross-references player IDs 
from different fantasy football platforms (Sleeper, FantasyPros, Yahoo, ESPN).

Purpose: Solve the core issue where different platforms use different ID systems,
causing player filtering to fail when trying to exclude already-drafted players.
"""

import json
import requests
import asyncio
from pathlib import Path

class PlayerMappingGenerator:
    """
    Generates a comprehensive player mapping file by fetching data from multiple APIs
    and creating cross-references between different platform ID systems.
    """
    
    def __init__(self):
        # File paths for storing the mapping data
        self.output_file = Path("../data/player_id_mapping.json")
        self.backup_file = Path("../data/player_id_mapping_backup.json")
        
        # API endpoints for different platforms
        self.sleeper_players_url = "https://api.sleeper.app/v1/players/nfl"
        
    def fetch_sleeper_players(self):
        """
        Fetch all NFL players from Sleeper API
        Returns: Dictionary with player_id as key and player info as value
        """
        print("🔄 Fetching player data from Sleeper API...")
        try:
            response = requests.get(self.sleeper_players_url, timeout=30)
            response.raise_for_status()
            players = response.json()
            print(f"✅ Retrieved {len(players)} players from Sleeper")
            return players
        except Exception as e:
            print(f"❌ Error fetching Sleeper players: {e}")
            return {}
    
    def load_fantasypros_data(self):
        """
        Load FantasyPros ranking data from local cache files
        Returns: List of player dictionaries with FantasyPros IDs
        """
        print("🔄 Loading FantasyPros data from local files...")
        fantasypros_players = []
        
        # Look for FantasyPros ranking files in the data directory
        data_dir = Path("../data")
        fp_files = list(data_dir.glob("fantasypros_rankings_*.json"))
        
        for file_path in fp_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        fantasypros_players.extend(data)
                        print(f"✅ Loaded {len(data)} players from {file_path.name}")
            except Exception as e:
                print(f"❌ Error loading {file_path}: {e}")
        
        # Remove duplicates based on player_id
        unique_players = {}
        for player in fantasypros_players:
            player_id = player.get('player_id')
            if player_id and player_id not in unique_players:
                unique_players[player_id] = player
        
        print(f"✅ Total unique FantasyPros players: {len(unique_players)}")
        return list(unique_players.values())
    
    def normalize_name(self, name):
        """
        Normalize player names for consistent matching across platforms
        Handles common variations like Jr., III, punctuation, etc.
        """
        if not name:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = name.lower().strip()
        
        # Remove common suffixes and punctuation
        suffixes_to_remove = [' jr.', ' jr', ' sr.', ' sr', ' iii', ' ii', ' iv']
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        # Remove periods, apostrophes, and extra spaces
        normalized = normalized.replace('.', '').replace("'", '').replace('-', ' ')
        normalized = ' '.join(normalized.split())  # Normalize spaces
        
        return normalized
    
    def create_unified_mapping(self):
        """
        Main function that creates the unified player mapping by cross-referencing
        Sleeper and FantasyPros data using normalized name matching.
        """
        print("🚀 Starting unified player mapping creation...")
        
        # Step 1: Fetch data from all sources
        sleeper_players = self.fetch_sleeper_players()
        fantasypros_players = self.load_fantasypros_data()
        
        if not sleeper_players or not fantasypros_players:
            print("❌ Missing required data sources. Cannot create mapping.")
            return False
        
        # Step 2: Create mapping structure
        unified_mapping = {}
        matched_count = 0
        
        print("🔄 Cross-referencing players between platforms...")
        
        # Step 3: For each Sleeper player, try to find matching FantasyPros player
        for sleeper_id, sleeper_data in sleeper_players.items():
            # Extract player name from Sleeper data
            sleeper_name = f"{sleeper_data.get('first_name', '')} {sleeper_data.get('last_name', '')}".strip()
            sleeper_normalized = self.normalize_name(sleeper_name)
            
            # Skip if no valid name
            if not sleeper_normalized:
                continue
            
            # Look for matching FantasyPros player
            fp_match = None
            for fp_player in fantasypros_players:
                fp_name = fp_player.get('player_name', '')
                fp_normalized = self.normalize_name(fp_name)
                
                if sleeper_normalized == fp_normalized:
                    fp_match = fp_player
                    break
            
            # Create comprehensive mapping entry with all available platform IDs
            mapping_entry = {
                # Core player identification
                "name": sleeper_name,
                "normalized_name": sleeper_normalized,
                "position": sleeper_data.get('position'),
                "team": sleeper_data.get('team'),
                
                # Platform-specific player IDs (the main purpose of this mapping)
                "sleeper_id": sleeper_id,
                "fantasypros_id": fp_match.get('player_id') if fp_match else None,
                "yahoo_id": sleeper_data.get('yahoo_id'),  # Yahoo Fantasy ID
                "espn_id": sleeper_data.get('espn_id'),    # ESPN Fantasy ID
                
                # Additional cross-platform IDs that might be useful
                "gsis_id": sleeper_data.get('gsis_id'),           # NFL GSIS ID
                "rotowire_id": sleeper_data.get('rotowire_id'),   # RotoWire ID
                "rotoworld_id": sleeper_data.get('rotoworld_id'), # RotoWorld ID
                "fantasy_data_id": sleeper_data.get('fantasy_data_id'), # FantasyData ID
                
                # Player status and metadata
                "active": sleeper_data.get('active', True),
                "injury_status": sleeper_data.get('injury_status', ''),
                "years_exp": sleeper_data.get('years_exp'),
                "age": sleeper_data.get('age'),
                
                # FantasyPros specific data (if successfully matched)
                "fantasypros_rank": fp_match.get('rank_ecr') if fp_match else None,
                "fantasypros_adp": fp_match.get('player_owned_avg') if fp_match else None,
                "fantasypros_tier": fp_match.get('tier') if fp_match else None,
            }
            
            # Add to unified mapping
            unified_mapping[sleeper_id] = mapping_entry
            
            if fp_match:
                matched_count += 1
        
        print(f"✅ Created mapping for {len(unified_mapping)} players")
        print(f"✅ Successfully matched {matched_count} players between platforms")
        
        # Step 4: Save the mapping to file
        try:
            # Create backup if file exists
            if self.output_file.exists():
                import shutil
                shutil.copy2(self.output_file, self.backup_file)
                print(f"✅ Created backup: {self.backup_file}")
            
            # Save new mapping
            self.output_file.parent.mkdir(exist_ok=True)
            with open(self.output_file, 'w') as f:
                json.dump(unified_mapping, f, indent=2, sort_keys=True)
            
            print(f"✅ Saved unified mapping to: {self.output_file}")
            print(f"📊 File size: {self.output_file.stat().st_size / 1024:.1f} KB")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving mapping file: {e}")
            return False

def main():
    """
    Main execution function - creates the player mapping when script is run directly
    """
    print("🎯 Fantasy Football Player ID Mapping Generator")
    print("=" * 50)
    
    generator = PlayerMappingGenerator()
    success = generator.create_unified_mapping()
    
    if success:
        print("\n🎉 Player mapping creation completed successfully!")
        print("💡 This will now enable robust player filtering across all platforms.")
    else:
        print("\n❌ Player mapping creation failed!")
        print("🔧 Check the errors above and try again.")

if __name__ == "__main__":
    main()