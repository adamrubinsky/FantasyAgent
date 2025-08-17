"""
Fantasy Football Draft Assistant - League Context Manager
Day 3 Enhancement: Proper league-specific settings management

This module manages league-specific settings to ensure rankings, projections,
and analysis are tailored to each league's unique scoring and roster rules.
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.sleeper_client import SleeperClient


@dataclass
class LeagueSettings:
    """
    Comprehensive league settings that affect rankings and strategy
    """
    # Basic info
    league_id: str
    platform: str  # 'sleeper', 'yahoo', 'espn'
    league_name: str
    total_teams: int
    
    # Scoring settings
    scoring_format: str  # 'standard', 'half_ppr', 'ppr'
    passing_tds: float = 4.0
    rushing_tds: float = 6.0
    receiving_tds: float = 6.0
    receptions: float = 0.0  # PPR value (0, 0.5, or 1.0)
    passing_yards_per_point: float = 25.0  # yards per 1 point
    rushing_yards_per_point: float = 10.0
    receiving_yards_per_point: float = 10.0
    
    # Roster settings (affects positional value)
    roster_positions: List[str] = None  # e.g., ['QB', 'RB', 'RB', 'WR', 'WR', 'TE', 'FLEX', 'SUPER_FLEX']
    starting_qbs: int = 1
    starting_rbs: int = 2
    starting_wrs: int = 2
    starting_tes: int = 1
    flex_spots: int = 1
    superflex_spots: int = 0
    
    # Draft settings
    draft_rounds: int = 16
    draft_type: str = 'snake'  # 'snake', 'linear'
    keeper_count: int = 0
    
    # League-specific rules
    trade_deadline_week: int = 10
    playoff_teams: int = 6
    playoff_weeks: List[int] = None  # e.g., [14, 15, 16] for weeks 14-16
    
    # Custom scoring rules
    bonus_40_yd_pass: float = 0.0
    bonus_40_yd_rush: float = 0.0
    bonus_40_yd_rec: float = 0.0
    fumble_lost: float = -2.0
    interception: float = -2.0
    
    def __post_init__(self):
        """Set defaults after initialization"""
        if self.roster_positions is None:
            self.roster_positions = []
        if self.playoff_weeks is None:
            self.playoff_weeks = [14, 15, 16]
        
        # Auto-detect SUPERFLEX
        if 'SUPER_FLEX' in self.roster_positions:
            self.superflex_spots = self.roster_positions.count('SUPER_FLEX')
        
        # Calculate starting positions
        self.starting_qbs = self.roster_positions.count('QB')
        self.starting_rbs = self.roster_positions.count('RB')
        self.starting_wrs = self.roster_positions.count('WR')
        self.starting_tes = self.roster_positions.count('TE')
        self.flex_spots = self.roster_positions.count('FLEX')
    
    @property
    def is_superflex(self) -> bool:
        """Check if this is a SUPERFLEX league"""
        return self.superflex_spots > 0
    
    @property
    def is_ppr(self) -> bool:
        """Check if this is a PPR league"""
        return self.receptions > 0
    
    @property
    def total_qb_spots(self) -> int:
        """Total QB spots including SUPERFLEX"""
        return self.starting_qbs + self.superflex_spots
    
    def get_position_scarcity(self) -> Dict[str, float]:
        """
        Calculate position scarcity based on roster requirements
        Higher values = more scarce = more valuable
        """
        return {
            'QB': self.total_qb_spots / self.total_teams,
            'RB': (self.starting_rbs + self.flex_spots * 0.4) / self.total_teams,
            'WR': (self.starting_wrs + self.flex_spots * 0.4) / self.total_teams,
            'TE': (self.starting_tes + self.flex_spots * 0.2) / self.total_teams
        }
    
    def to_ranking_key(self) -> str:
        """Generate a unique key for ranking cache based on settings"""
        key_parts = [
            self.platform,
            self.scoring_format,
            'superflex' if self.is_superflex else 'standard',
            f'qb{self.total_qb_spots}',
            f'teams{self.total_teams}'
        ]
        return '_'.join(key_parts)


class LeagueContextManager:
    """
    Manages league contexts and provides settings-aware data fetching
    """
    
    def __init__(self):
        self.cache_dir = Path(__file__).parent.parent / "data"
        self.cache_dir.mkdir(exist_ok=True)
        self.contexts_file = self.cache_dir / "league_contexts.json"
        
        # Load existing contexts
        self.contexts: Dict[str, LeagueSettings] = self.load_contexts()
        self.current_context: Optional[LeagueSettings] = None
    
    def load_contexts(self) -> Dict[str, LeagueSettings]:
        """Load saved league contexts from disk"""
        if not self.contexts_file.exists():
            return {}
        
        try:
            with open(self.contexts_file, 'r') as f:
                data = json.load(f)
                contexts = {}
                for league_id, context_dict in data.items():
                    contexts[league_id] = LeagueSettings(**context_dict)
                return contexts
        except Exception as e:
            print(f"⚠️ Error loading league contexts: {e}")
            return {}
    
    def save_contexts(self):
        """Save league contexts to disk"""
        try:
            data = {}
            for league_id, context in self.contexts.items():
                data[league_id] = asdict(context)
            
            with open(self.contexts_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving league contexts: {e}")
    
    async def analyze_sleeper_league(self, client: SleeperClient, league_id: str) -> LeagueSettings:
        """
        Analyze a Sleeper league to extract all relevant settings
        """
        print(f"🔍 Analyzing Sleeper league settings for {league_id}...")
        
        # Get league info
        league_info = await client.get_league_info(league_id)
        
        # Extract basic info
        league_name = league_info.get('name', 'Unknown League')
        total_teams = league_info.get('total_rosters', 12)
        roster_positions = league_info.get('roster_positions', [])
        
        # Extract scoring settings
        scoring = league_info.get('scoring_settings', {})
        
        # Determine PPR format
        receptions = scoring.get('rec', 0)
        if receptions == 1.0:
            scoring_format = 'ppr'
        elif receptions == 0.5:
            scoring_format = 'half_ppr'
        else:
            scoring_format = 'standard'
        
        # Create league settings
        settings = LeagueSettings(
            league_id=league_id,
            platform='sleeper',
            league_name=league_name,
            total_teams=total_teams,
            scoring_format=scoring_format,
            
            # Scoring details
            passing_tds=scoring.get('pass_td', 4.0),
            rushing_tds=scoring.get('rush_td', 6.0),
            receiving_tds=scoring.get('rec_td', 6.0),
            receptions=receptions,
            passing_yards_per_point=25.0 / scoring.get('pass_yd', 0.04),  # Convert from points per yard
            rushing_yards_per_point=10.0 / scoring.get('rush_yd', 0.1),
            receiving_yards_per_point=10.0 / scoring.get('rec_yd', 0.1),
            
            # Roster settings
            roster_positions=roster_positions,
            draft_rounds=league_info.get('settings', {}).get('draft_rounds', 16),
            draft_type=league_info.get('settings', {}).get('type', 'snake'),
            
            # Penalties
            fumble_lost=scoring.get('fum_lost', -2.0),
            interception=scoring.get('pass_int', -2.0),
            
            # Bonuses
            bonus_40_yd_pass=scoring.get('bonus_pass_yd_40', 0.0),
            bonus_40_yd_rush=scoring.get('bonus_rush_yd_40', 0.0),
            bonus_40_yd_rec=scoring.get('bonus_rec_yd_40', 0.0)
        )
        
        print(f"✅ League analysis complete:")
        print(f"   Name: {settings.league_name}")
        print(f"   Format: {settings.scoring_format.upper()}")
        print(f"   Teams: {settings.total_teams}")
        print(f"   SUPERFLEX: {'YES' if settings.is_superflex else 'NO'}")
        print(f"   QB spots: {settings.total_qb_spots}")
        
        return settings
    
    async def set_current_league(self, league_id: str, platform: str = 'sleeper') -> LeagueSettings:
        """
        Load and set a league as the current context
        """
        # Check if we already have this league cached
        if league_id in self.contexts:
            self.current_context = self.contexts[league_id]
            print(f"📋 Loaded cached settings for {self.current_context.league_name}")
            return self.current_context
        
        # Need to analyze the league
        if platform == 'sleeper':
            username = os.getenv('SLEEPER_USERNAME')
            async with SleeperClient(username=username, league_id=league_id) as client:
                settings = await self.analyze_sleeper_league(client, league_id)
        else:
            raise ValueError(f"Platform {platform} not yet supported")
        
        # Cache and set as current
        self.contexts[league_id] = settings
        self.current_context = settings
        self.save_contexts()
        
        return settings
    
    def get_current_context(self) -> Optional[LeagueSettings]:
        """Get the current league context"""
        return self.current_context
    
    def get_rankings_parameters(self) -> Dict[str, Any]:
        """
        Get parameters for fetching rankings based on current league context
        """
        if not self.current_context:
            # Fallback defaults
            return {
                'scoring_format': 'half_ppr',
                'league_type': 'superflex',
                'total_teams': 12,
                'position_scarcity': {'QB': 2.0, 'RB': 2.4, 'WR': 2.4, 'TE': 1.2}
            }
        
        settings = self.current_context
        return {
            'scoring_format': settings.scoring_format,
            'league_type': 'superflex' if settings.is_superflex else 'standard',
            'total_teams': settings.total_teams,
            'roster_positions': settings.roster_positions,
            'position_scarcity': settings.get_position_scarcity(),
            'playoff_weeks': settings.playoff_weeks,
            'custom_scoring': {
                'passing_tds': settings.passing_tds,
                'rushing_tds': settings.rushing_tds,
                'receiving_tds': settings.receiving_tds,
                'receptions': settings.receptions,
                'bonuses': {
                    'pass_40': settings.bonus_40_yd_pass,
                    'rush_40': settings.bonus_40_yd_rush,
                    'rec_40': settings.bonus_40_yd_rec
                }
            }
        }
    
    def list_contexts(self) -> Dict[str, str]:
        """List all available league contexts"""
        return {
            league_id: f"{context.league_name} ({context.platform.title()}, {context.scoring_format.upper()})"
            for league_id, context in self.contexts.items()
        }


# Global instance
league_manager = LeagueContextManager()


# Test function
async def test_league_context():
    """Test league context analysis"""
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    if not username or not league_id:
        print("❌ Please set SLEEPER_USERNAME and SLEEPER_LEAGUE_ID")
        return
    
    # Analyze current league
    settings = await league_manager.set_current_league(league_id)
    
    # Show analysis
    print(f"\n📊 League Analysis Results:")
    print(f"League: {settings.league_name}")
    print(f"Platform: {settings.platform}")
    print(f"Scoring: {settings.scoring_format}")
    print(f"Teams: {settings.total_teams}")
    print(f"SUPERFLEX: {settings.is_superflex}")
    print(f"Total QB spots: {settings.total_qb_spots}")
    print(f"Roster positions: {settings.roster_positions}")
    
    # Show position scarcity
    scarcity = settings.get_position_scarcity()
    print(f"\n🎯 Position Scarcity (higher = more valuable):")
    for pos, value in scarcity.items():
        print(f"  {pos}: {value:.2f}")
    
    # Show ranking parameters
    params = league_manager.get_rankings_parameters()
    print(f"\n📈 Rankings Parameters:")
    print(f"  Format: {params['scoring_format']}")
    print(f"  Type: {params['league_type']}")
    print(f"  Teams: {params['total_teams']}")


if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    load_dotenv('.env.local')
    load_dotenv()
    
    asyncio.run(test_league_context())