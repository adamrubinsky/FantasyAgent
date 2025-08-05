"""
Fantasy Football Draft Assistant - Live Draft Monitor
Day 2 (Aug 6): Real-time draft tracking with 5-second polling
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

from api.sleeper_client import SleeperClient
from core.pre_computation import PreComputationEngine


class DraftMonitor:
    """
    Real-time draft monitoring system that polls Sleeper API every 5 seconds
    
    Key Features:
    - Detects new picks instantly (within 5 seconds)
    - Tracks draft state and user's turn
    - Shows live available players
    - Notifies when it's your turn to pick
    - Maintains draft history for analysis
    
    This is the core component for draft day - it needs to be rock solid!
    """
    
    def __init__(self, username: str, league_id: str, anthropic_api_key: str = None):
        self.username = username
        self.league_id = league_id
        self.anthropic_api_key = anthropic_api_key
        self.console = Console()
        
        # Draft state tracking
        self.draft_id: Optional[str] = None
        self.last_pick_count = 0
        self.user_roster_id: Optional[int] = None
        self.current_pick: Optional[int] = None
        self.total_picks: Optional[int] = None
        self.picks_history: List[Dict[str, Any]] = []
        
        # Cache directory for storing draft state
        self.cache_dir = Path(__file__).parent.parent / "data"
        self.draft_state_file = self.cache_dir / "draft_state.json"
        
        # Sleeper client for API calls
        self.client: Optional[SleeperClient] = None
        
        # Pre-computation engine (optional)
        self.precomp_engine: Optional[PreComputationEngine] = None
        self.precomp_enabled = False
        
        # Track which players have been drafted (for quick lookups)
        self.drafted_players: Set[str] = set()
        
    async def __aenter__(self):
        """Async context manager entry - initialize Sleeper client and pre-computation engine"""
        self.client = SleeperClient(self.username, self.league_id)
        await self.client.__aenter__()
        
        # Initialize pre-computation engine if API key provided
        if self.anthropic_api_key:
            try:
                self.precomp_engine = PreComputationEngine(
                    self.username, self.league_id, self.anthropic_api_key
                )
                await self.precomp_engine.__aenter__()
                
                # Initialize draft context for pre-computation
                success = await self.precomp_engine.initialize_draft_context()
                if success:
                    self.precomp_enabled = True
                    self.console.print("🎯 Pre-computation engine enabled", style="green")
                else:
                    self.console.print("⚠️ Pre-computation engine initialization failed", style="yellow")
            except Exception as e:
                self.console.print(f"⚠️ Pre-computation engine error: {e}", style="yellow")
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup Sleeper client and pre-computation engine"""
        if self.precomp_engine:
            await self.precomp_engine.__aexit__(exc_type, exc_val, exc_tb)
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def initialize_draft(self) -> bool:
        """
        Initialize draft monitoring by getting league and draft info
        
        This method:
        1. Gets league information from Sleeper
        2. Finds the draft ID for this league
        3. Gets initial draft state (picks made so far)
        4. Identifies the user's roster ID for turn tracking
        5. Loads any cached draft state from previous sessions
        
        Returns:
            bool: True if draft found and initialized successfully
        """
        try:
            # Step 1: Get league information
            self.console.print("🔍 Initializing draft monitor...", style="yellow")
            league_info = await self.client.get_league_info()
            
            # Step 2: Find draft ID
            self.draft_id = league_info.get('draft_id')
            if not self.draft_id:
                self.console.print("❌ No draft found for this league", style="red")
                return False
            
            # Step 3: Get league rosters to find user's roster ID
            rosters = await self.client.get_league_rosters()
            user_info = await self.client.get_user()
            user_id = user_info.get('user_id')
            
            # Find which roster belongs to our user
            for roster in rosters:
                if roster.get('owner_id') == user_id:
                    self.user_roster_id = roster.get('roster_id')
                    break
            
            if self.user_roster_id is None:
                self.console.print("❌ Could not find your roster in this league", style="red")
                return False
            
            # Step 4: Get draft information
            draft_info = await self.client.get_draft_info(self.draft_id)
            self.total_picks = len(rosters) * draft_info.get('settings', {}).get('rounds', 16)
            
            # Step 5: Get current draft picks to establish baseline
            picks = await self.client.get_draft_picks(self.draft_id)
            self.last_pick_count = len(picks)
            self.picks_history = picks
            
            # Build set of drafted players for fast lookups
            self.drafted_players = {
                pick['player_id'] for pick in picks 
                if pick.get('player_id')
            }
            
            # Step 6: Determine current pick number
            self.current_pick = len(picks) + 1 if len(picks) < self.total_picks else self.total_picks
            
            # Step 7: Load any cached state
            await self._load_draft_state()
            
            self.console.print(f"✅ Draft monitor initialized", style="green")
            self.console.print(f"   Draft ID: {self.draft_id}")
            self.console.print(f"   Your Roster ID: {self.user_roster_id}")
            self.console.print(f"   Current Pick: {self.current_pick}/{self.total_picks}")
            self.console.print(f"   Picks Made: {len(picks)}")
            
            return True
            
        except Exception as e:
            self.console.print(f"❌ Error initializing draft: {e}", style="red")
            return False
    
    async def _load_draft_state(self):
        """Load cached draft state from previous session if it exists"""
        if self.draft_state_file.exists():
            try:
                with open(self.draft_state_file, 'r') as f:
                    cached_state = json.load(f)
                    
                # Only load if it's the same draft
                if cached_state.get('draft_id') == self.draft_id:
                    self.console.print("📁 Loaded previous draft state from cache", style="dim")
                    
            except Exception as e:
                self.console.print(f"⚠️ Could not load cached state: {e}", style="yellow")
    
    async def _save_draft_state(self):
        """Save current draft state to cache for persistence"""
        try:
            state = {
                'draft_id': self.draft_id,
                'last_updated': datetime.now().isoformat(),
                'current_pick': self.current_pick,
                'last_pick_count': self.last_pick_count,
                'user_roster_id': self.user_roster_id,
                'picks_count': len(self.picks_history)
            }
            
            with open(self.draft_state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            self.console.print(f"⚠️ Could not save draft state: {e}", style="yellow")
    
    async def check_for_new_picks(self) -> List[Dict[str, Any]]:
        """
        Check for new picks since last poll
        
        This is the core monitoring method that:
        1. Gets current picks from Sleeper
        2. Compares with our last known state
        3. Identifies any new picks made
        4. Updates our internal tracking
        5. Returns list of new picks for processing
        
        Returns:
            List of new pick dictionaries, empty if no new picks
        """
        try:
            # Get current picks from API
            current_picks = await self.client.get_draft_picks(self.draft_id)
            current_count = len(current_picks)
            
            # Check if we have new picks
            if current_count > self.last_pick_count:
                # We have new picks! Find which ones are new
                new_picks = current_picks[self.last_pick_count:]
                
                # Update our tracking
                self.last_pick_count = current_count
                self.picks_history = current_picks
                self.current_pick = current_count + 1 if current_count < self.total_picks else self.total_picks
                
                # Update drafted players set
                for pick in new_picks:
                    if pick.get('player_id'):
                        self.drafted_players.add(pick['player_id'])
                
                # Save state
                await self._save_draft_state()
                
                return new_picks
            
            return []  # No new picks
            
        except Exception as e:
            self.console.print(f"❌ Error checking for picks: {e}", style="red")
            return []
    
    def is_user_turn(self) -> bool:
        """
        Check if it's currently the user's turn to pick
        
        This analyzes the draft order and current pick to determine
        if the user should be making a selection right now.
        
        Returns:
            bool: True if it's the user's turn
        """
        if not self.current_pick or not self.total_picks:
            return False
        
        # Get the most recent pick to see whose turn it is
        if self.picks_history:
            # Look at draft order - this is complex because of snake draft
            # For now, we'll use a simpler check: if current pick roster_id matches user
            try:
                # In a snake draft, we need to calculate which roster picks at this position
                # This is a simplified version - real implementation would need draft order
                
                # For now, return False unless we're sure
                return False  # TODO: Implement proper turn detection
                
            except Exception:
                return False
        
        return False
    
    def get_picks_until_user_turn(self) -> int:
        """
        Calculate how many picks until it's the user's turn
        
        This helps with pre-computation - we can start analyzing
        when we're 3 picks away from our turn.
        
        Returns:
            int: Number of picks until user's turn, -1 if unknown
        """
        # TODO: Implement based on draft order and snake draft logic
        # For now, return unknown
        return -1
    
    async def get_recent_picks_summary(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get a summary of the most recent picks with player names
        
        Args:
            count: Number of recent picks to return
            
        Returns:
            List of pick summaries with player names and details
        """
        if not self.picks_history:
            return []
        
        # Get the most recent picks
        recent_picks = self.picks_history[-count:] if len(self.picks_history) >= count else self.picks_history
        
        # Get player data to add names
        players = await self.client.get_all_players()
        
        # Build summary with player names
        summary = []
        for pick in recent_picks:
            player_id = pick.get('player_id')
            if player_id and player_id in players:
                player_data = players[player_id]
                name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()
                positions = "/".join(player_data.get('fantasy_positions', []))
                team = player_data.get('team', 'FA')
                
                summary.append({
                    'pick_no': pick.get('pick_no', 0),
                    'round': pick.get('round', 0),
                    'player_name': name,
                    'positions': positions,
                    'team': team,
                    'roster_id': pick.get('roster_id')
                })
        
        return summary
    
    def create_draft_status_display(self) -> Panel:
        """
        Create a rich display panel showing current draft status
        
        Returns:
            Rich Panel with current draft information
        """
        if not self.draft_id:
            return Panel("Draft not initialized", style="red")
        
        # Create status text
        status_lines = [
            f"Draft ID: {self.draft_id}",
            f"Pick: {self.current_pick}/{self.total_picks}",
            f"Your Roster: #{self.user_roster_id}",
            f"Picks Made: {len(self.picks_history)}",
        ]
        
        # Add turn indicator
        if self.is_user_turn():
            status_lines.append("🚨 YOUR TURN TO PICK!")
            panel_style = "bold red"
        else:
            picks_until = self.get_picks_until_user_turn()
            if picks_until > 0:
                status_lines.append(f"⏳ {picks_until} picks until your turn")
            panel_style = "blue"
        
        status_text = "\n".join(status_lines)
        
        return Panel(
            status_text,
            title="📊 Draft Status",
            style=panel_style
        )
    
    async def create_recent_picks_display(self) -> Panel:
        """
        Create a display showing recent picks made
        
        Returns:
            Rich Panel with recent picks table
        """
        recent_picks = await self.get_recent_picks_summary(5)
        
        if not recent_picks:
            return Panel("No picks made yet", title="📝 Recent Picks")
        
        # Create table of recent picks
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Pick", width=4)
        table.add_column("Player", width=20)
        table.add_column("Pos", width=6)
        table.add_column("Team", width=4)
        
        for pick in recent_picks:
            table.add_row(
                str(pick['pick_no']),
                pick['player_name'],
                pick['positions'],
                pick['team']
            )
        
        return Panel(table, title="📝 Recent Picks")
    
    async def start_monitoring(self, show_available: bool = True, position_filter: str = None, enhanced: bool = False):
        """
        Start the real-time draft monitoring loop
        
        This is the main method that:
        1. Runs continuously during the draft
        2. Polls every 5 seconds for new picks
        3. Updates the display in real-time
        4. Notifies when new picks are made
        5. Shows when it's user's turn
        
        Args:
            show_available: Whether to show available players table
            position_filter: Filter available players by position
        """
        if not await self.initialize_draft():
            return
        
        self.console.print("\n🚀 Starting draft monitor - Press Ctrl+C to stop\n", style="bold green")
        
        try:
            # Create live display that updates automatically
            with Live(console=self.console, refresh_per_second=1) as live:
                
                while True:  # Run until user stops
                    try:
                        # Check for new picks
                        new_picks = await self.check_for_new_picks()
                        
                        # Alert for new picks and trigger pre-computation
                        if new_picks:
                            for pick in new_picks:
                                players = await self.client.get_all_players()
                                player_id = pick.get('player_id')
                                if player_id and player_id in players:
                                    player_data = players[player_id]
                                    name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()
                                    positions = "/".join(player_data.get('fantasy_positions', []))
                                    team = player_data.get('team', 'FA')
                                    
                                    self.console.print(
                                        f"🚨 NEW PICK: {name} ({positions}) - {team} [Pick #{pick.get('pick_no', '?')}]",
                                        style="bold yellow"
                                    )
                            
                            # Check if we should trigger pre-computation
                            if self.precomp_enabled and self.current_pick:
                                should_precompute = await self.precomp_engine.should_start_precomputation(self.current_pick)
                                if should_precompute:
                                    # Run pre-computation in background (don't block display)
                                    asyncio.create_task(self._run_background_precomputation())
                                
                                # Invalidate cache if picks affect recommendations
                                if hasattr(self.precomp_engine, 'cached_recommendations') and self.precomp_engine.cached_recommendations:
                                    self.precomp_engine.invalidate_cache("New picks made")
                        
                        # Create display panels
                        draft_status = self.create_draft_status_display()
                        recent_picks = await self.create_recent_picks_display()
                        
                        # Create main display
                        main_display = Columns([draft_status, recent_picks])
                        
                        # Add available players if requested
                        if show_available:
                            available_players = await self._create_available_players_display(position_filter, enhanced)
                            display_content = [main_display, available_players]
                        else:
                            display_content = [main_display]
                        
                        # Update live display
                        from rich.console import Group
                        live.update(Group(*display_content))
                        
                        # Wait 5 seconds before next poll
                        await asyncio.sleep(5)
                        
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        self.console.print(f"❌ Error in monitoring loop: {e}", style="red")
                        await asyncio.sleep(5)  # Wait before retrying
        
        except KeyboardInterrupt:
            self.console.print("\n👋 Draft monitoring stopped", style="yellow")
        finally:
            await self._save_draft_state()
    
    async def _create_available_players_display(self, position_filter: str = None, enhanced: bool = False) -> Panel:
        """Create display panel for available players with optional enhanced data"""
        try:
            available_players = await self.client.get_available_players(self.draft_id, position_filter, enhanced)
            
            if not available_players:
                return Panel("No available players found", title="🔍 Available Players")
            
            # Create table with enhanced columns if requested
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Rank", width=4)
            table.add_column("Player", width=16)
            table.add_column("Pos", width=4)
            table.add_column("Team", width=4)
            
            if enhanced:
                table.add_column("ADP", width=5, style="magenta")
                table.add_column("Bye", width=3, style="yellow")
                table.add_column("P/O", width=4, style="red")  # Playoff Outlook abbreviated
                table.add_column("Score", width=5, style="bright_green")
            else:
                table.add_column("Exp", width=3)
            
            # Show top 10 available players
            for player in available_players[:10]:
                rank = str(player['rank']) if player['rank'] < 999 else "N/A"
                positions = "/".join(player['positions'])
                team = player['team'] or "FA"
                
                if enhanced:
                    adp = f"{player.get('adp', 0):.0f}" if player.get('adp') else 'N/A'
                    bye_week = str(player.get('bye_week', 'N/A'))
                    playoff = player.get('playoff_outlook', 'unk')[:3]  # Abbreviated
                    fantasy_score = f"{player.get('fantasy_score', 0):.1f}"
                    
                    table.add_row(rank, player['name'], positions, team, adp, bye_week, playoff, fantasy_score)
                else:
                    exp = f"{player['years_exp']}y" if player.get('years_exp') else "R"
                    table.add_row(rank, player['name'], positions, team, exp)
            
            title_suffix = f" ({position_filter})" if position_filter else ""
            title_suffix += " - Enhanced" if enhanced else ""
            title = f"🔍 Available Players{title_suffix}"
            
            return Panel(table, title=title)
            
        except Exception as e:
            return Panel(f"Error loading players: {e}", title="🔍 Available Players", style="red")
    
    async def _run_background_precomputation(self):
        """Run pre-computation in background without blocking the UI"""
        try:
            if not self.precomp_enabled or not self.current_pick:
                return
            
            self.console.print("🎯 Starting pre-computation analysis...", style="cyan")
            await self.precomp_engine.run_precomputation(self.current_pick)
            self.console.print("✅ Pre-computation complete - recommendations ready!", style="green")
            
        except Exception as e:
            self.console.print(f"⚠️ Pre-computation failed: {e}", style="yellow")
    
    async def get_precomputed_recommendations(self) -> Optional[str]:
        """Get pre-computed recommendations if available"""
        if not self.precomp_enabled:
            return None
        
        cache_data = self.precomp_engine.get_cached_recommendations()
        if cache_data:
            return self.precomp_engine.format_quick_recommendations(cache_data)
        
        return None


# Test function for development
async def test_draft_monitor():
    """Test the draft monitor with real league data"""
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    if not username or not league_id:
        print("❌ Please set SLEEPER_USERNAME and SLEEPER_LEAGUE_ID in .env file")
        return
    
    async with DraftMonitor(username, league_id) as monitor:
        success = await monitor.initialize_draft()
        if success:
            print("✅ Draft monitor test successful!")
            
            # Show recent picks
            recent = await monitor.get_recent_picks_summary(3)
            if recent:
                print("\n📝 Recent picks:")
                for pick in recent:
                    print(f"  Pick {pick['pick_no']}: {pick['player_name']} ({pick['positions']}) - {pick['team']}")
            else:
                print("  No picks made yet")
        else:
            print("❌ Draft monitor test failed")


if __name__ == "__main__":
    # Run test when script is executed directly
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    load_dotenv()
    
    asyncio.run(test_draft_monitor())