#!/usr/bin/env python3
"""
Fantasy Football Draft Assistant - Main Entry Point
Day 1 (Aug 5): Basic setup and Sleeper API testing
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.sleeper_client import SleeperClient, test_sleeper_connection
from core.draft_monitor import DraftMonitor
from core.mcp_integration import MCPClient, EnhancedRankingsManager
from core.league_context import league_manager

# Load environment variables - try local first, then default
load_dotenv('.env.local')  # For local development with real credentials
load_dotenv()              # Fallback to .env (with placeholders)

# Initialize league context on startup
def initialize_league_context():
    """Try to load the default league context"""
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    if league_id and league_id in league_manager.contexts:
        league_manager.current_context = league_manager.contexts[league_id]

initialize_league_context()

console = Console()


@click.group()
def cli():
    """Fantasy Football Draft Assistant - AI-powered draft recommendations"""
    pass


@cli.command()
def test():
    """Test connection to Sleeper API with your league data"""
    console.print("🏈 Fantasy Football Draft Assistant - Connection Test", style="bold blue")
    console.print("=" * 60)
    
    success = asyncio.run(test_sleeper_connection())
    
    if success:
        console.print("\n✅ All tests passed! Sleeper API connection working.", style="bold green")
    else:
        console.print("\n❌ Tests failed. Check your configuration.", style="bold red")


@cli.command()
@click.option('--position', '-p', help='Filter by position (QB, RB, WR, TE)')
@click.option('--limit', '-l', default=10, help='Number of players to show')
def available(position, limit):
    """Show available players in your draft"""
    asyncio.run(show_available_players(position, limit))


async def show_available_players(position: str = None, limit: int = 10):
    """Display available players in a nice table"""
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    if not username or not league_id:
        console.print("❌ Please set SLEEPER_USERNAME and SLEEPER_LEAGUE_ID in .env file", style="red")
        return
    
    async with SleeperClient(username=username, league_id=league_id) as client:
        try:
            # Get league info and draft ID
            league = await client.get_league_info()
            draft_id = league.get('draft_id')
            
            if not draft_id:
                console.print("❌ No draft found for this league", style="red")
                return
            
            # Get available players
            console.print(f"🔍 Getting available players for draft {draft_id}...")
            if position:
                console.print(f"   Filtering by position: {position}")
            
            available_players = await client.get_available_players(draft_id, position)
            
            if not available_players:
                console.print("No available players found", style="yellow")
                return
            
            # Create table
            table = Table(title=f"Available Players{f' ({position})' if position else ''}")
            table.add_column("Rank", style="cyan", width=5)
            table.add_column("Player", style="bold white", width=20)
            table.add_column("Pos", style="green", width=6)
            table.add_column("Team", style="blue", width=5)
            table.add_column("Experience", style="yellow", width=10)
            
            # Add rows (limit results)
            for i, player in enumerate(available_players[:limit]):
                rank = str(player['rank']) if player['rank'] < 999 else "N/A"
                positions = "/".join(player['positions'])
                team = player['team'] or "FA"
                exp = f"{player['years_exp']}y" if player.get('years_exp') else "R"
                
                table.add_row(rank, player['name'], positions, team, exp)
            
            console.print(table)
            console.print(f"\nShowing {min(len(available_players), limit)} of {len(available_players)} available players")
            
        except Exception as e:
            console.print(f"❌ Error: {e}", style="red")


@cli.command()
def league():
    """Show your league information"""
    asyncio.run(show_league_info())


@cli.command()
@click.option('--position', '-p', help='Filter available players by position (QB, RB, WR, TE)')
@click.option('--no-available', is_flag=True, help='Hide available players table')
def monitor(position, no_available):
    """🚨 Start real-time draft monitoring (polls every 5 seconds)"""
    asyncio.run(start_draft_monitoring(position, not no_available))


@cli.command()
def status():
    """Show current draft status without monitoring"""
    asyncio.run(show_draft_status())


async def start_draft_monitoring(position_filter: str = None, show_available: bool = True):
    """Start the real-time draft monitor"""
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    if not username or not league_id:
        console.print("❌ Please set SLEEPER_USERNAME and SLEEPER_LEAGUE_ID in .env file", style="red")
        return
    
    async with DraftMonitor(username, league_id) as monitor:
        await monitor.start_monitoring(show_available, position_filter)


async def show_draft_status():
    """Show draft status without live monitoring"""
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    if not username or not league_id:
        console.print("❌ Please set SLEEPER_USERNAME and SLEEPER_LEAGUE_ID in .env file", style="red")
        return
    
    async with DraftMonitor(username, league_id) as monitor:
        if await monitor.initialize_draft():
            # Show draft status
            status_panel = monitor.create_draft_status_display()
            recent_picks = await monitor.create_recent_picks_display()
            
            console.print(status_panel)
            console.print(recent_picks)
        else:
            console.print("❌ Could not initialize draft", style="red")


@cli.command()
@click.option('--position', '-p', help='Filter by position (QB, RB, WR, TE)')
@click.option('--limit', '-l', default=20, help='Number of players to show')
def rankings(position, limit):
    """Show FantasyPros consensus rankings with ADP and tiers"""
    asyncio.run(show_rankings(position, limit))


@cli.command()
def strategy():
    """Get SUPERFLEX draft strategy advice"""
    asyncio.run(show_strategy())


@cli.command()
@click.option('--league-id', '-l', help='Specific league ID to analyze')
def setup(league_id):
    """Analyze and setup league-specific settings"""
    asyncio.run(setup_league_context(league_id))


@cli.command()
@click.option('--pick', '-p', required=True, type=int, help='Current draft pick number')
@click.option('--limit', '-l', default=10, help='Number of available players to analyze')
def value(pick, limit):
    """Find value picks based on ADP analysis"""
    asyncio.run(show_value_picks(pick, limit))


async def setup_league_context(league_id: str = None):
    """Setup league-specific context and settings"""
    # Use provided league ID or fall back to environment
    league_id = league_id or os.getenv('SLEEPER_LEAGUE_ID')
    
    if not league_id:
        console.print("❌ Please provide league ID with -l or set SLEEPER_LEAGUE_ID", style="red")
        return
    
    console.print(f"🔍 Analyzing league settings for {league_id}...", style="yellow")
    
    try:
        # Analyze and set current league context
        settings = await league_manager.set_current_league(league_id)
        
        # Display results
        console.print(f"\n✅ League Context Configured", style="bold green")
        console.print(f"📋 League: {settings.league_name}")
        console.print(f"🏆 Platform: {settings.platform.title()}")
        console.print(f"📊 Scoring: {settings.scoring_format.upper()}")
        console.print(f"👥 Teams: {settings.total_teams}")
        console.print(f"🎯 SUPERFLEX: {'YES' if settings.is_superflex else 'NO'}")
        console.print(f"🏈 QB spots: {settings.total_qb_spots}")
        
        # Show position scarcity
        scarcity = settings.get_position_scarcity()
        console.print(f"\n🎯 Position Values (higher = more scarce):", style="bold cyan")
        for pos, value in sorted(scarcity.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  {pos}: {value:.2f}")
        
        console.print(f"\n💡 Rankings will now be tailored to your league settings!", style="bold blue")
        
    except Exception as e:
        console.print(f"❌ Error analyzing league: {e}", style="red")


async def show_rankings(position: str = None, limit: int = 20):
    """Display FantasyPros rankings tailored to your league"""
    # Ensure we have league context
    context = league_manager.get_current_context()
    if not context:
        console.print("⚠️ No league context set. Run 'python3 main.py setup' first.", style="yellow")
        console.print("📊 Using default settings (SUPERFLEX, Half-PPR)...", style="dim")
    else:
        console.print(f"📊 Fetching rankings for {context.league_name} ({context.scoring_format.upper()})...", style="yellow")
    
    async with MCPClient() as mcp:
        rankings = await mcp.get_rankings(
            position=position,
            limit=limit
        )
        
        if 'error' in rankings:
            console.print(f"❌ Error: {rankings['error']}", style="red")
            return
        
        # Create table with context info
        context = league_manager.get_current_context()
        if context:
            title = f"{context.league_name} Rankings{f' ({position})' if position else ''}"
        else:
            title = f"FantasyPros Rankings{f' ({position})' if position else ''}"
        table = Table(title=title)
        table.add_column("Rank", style="cyan", width=4)
        table.add_column("Player", style="bold white", width=20)
        table.add_column("Pos", style="green", width=4)
        table.add_column("Team", style="blue", width=4)
        table.add_column("ADP", style="yellow", width=6)
        table.add_column("Tier", style="magenta", width=4)
        
        # Add rows
        for player in rankings.get('players', []):
            table.add_row(
                str(player['rank']),
                player['name'],
                player['position'],
                player['team'],
                f"{player['adp']:.1f}",
                str(player['tier'])
            )
        
        console.print(table)
        
        # Show metadata
        console.print(f"\n📈 Format: {rankings.get('format', 'N/A')} {rankings.get('scoring', 'N/A')}")
        console.print(f"🕐 Last updated: {rankings.get('last_updated', 'N/A')}")


async def show_strategy():
    """Display SUPERFLEX strategy advice"""
    console.print("🏈 Getting SUPERFLEX draft strategy...", style="yellow")
    
    async with MCPClient() as mcp:
        strategy = await mcp.get_superflex_strategy()
        
        # Strategy overview
        console.print(f"\n🎯 {strategy['strategy']}", style="bold green")
        
        # Key points
        console.print("\n📝 Key Strategy Points:", style="bold cyan")
        for i, point in enumerate(strategy.get('key_points', []), 1):
            console.print(f"  {i}. {point}")
        
        # Position targets
        console.print("\n🎯 Position Targets:", style="bold cyan")
        for pos, target in strategy.get('position_targets', {}).items():
            console.print(f"  {pos}: {target}")
        
        # Round-by-round guide
        console.print("\n📊 Round-by-Round Guide:", style="bold cyan")
        for rounds, advice in strategy.get('round_by_round', {}).items():
            console.print(f"  Rounds {rounds}: {advice}")


async def show_value_picks(current_pick: int, limit: int = 10):
    """Show value picks based on ADP analysis"""
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    if not username or not league_id:
        console.print("❌ Please set SLEEPER_USERNAME and SLEEPER_LEAGUE_ID in .env file", style="red")
        return
    
    console.print(f"💰 Finding value picks at pick #{current_pick}...", style="yellow")
    
    async with SleeperClient(username=username, league_id=league_id) as sleeper_client:
        async with MCPClient() as mcp:
            # Get available players from current draft
            league = await sleeper_client.get_league_info()
            draft_id = league.get('draft_id')
            
            if not draft_id:
                console.print("❌ No draft found for this league", style="red")
                return
            
            available_players = await sleeper_client.get_available_players(draft_id)
            
            # Get player names for top available players
            player_names = [p['name'] for p in available_players[:50]]  # Top 50 available
            
            # Get ADP analysis
            adp_analysis = await mcp.get_adp_analysis(
                current_pick=current_pick,
                available_players=player_names,
                scoring_format="half_ppr"
            )
            
            if 'error' in adp_analysis:
                console.print(f"❌ Error: {adp_analysis['error']}", style="red")
                return
            
            # Show results
            console.print(f"\n📊 ADP Analysis for Pick #{current_pick}", style="bold")
            
            # Value picks
            value_picks = adp_analysis.get('value_picks', [])
            if value_picks:
                console.print("\n💰 VALUE PICKS (Available later than ADP):", style="bold green")
                table = Table()
                table.add_column("Player", style="bold white")
                table.add_column("Pos", style="green")
                table.add_column("ADP", style="yellow")
                table.add_column("Value", style="cyan")
                table.add_column("Rec", style="bold green")
                
                for pick in value_picks[:limit]:
                    table.add_row(
                        pick['name'],
                        pick['position'],
                        f"{pick['adp']:.1f}",
                        f"+{pick['value_differential']:.0f}",
                        pick['recommendation']
                    )
                console.print(table)
            else:
                console.print("💰 No clear value picks available at current pick", style="yellow")
            
            # Best overall recommendation
            best_value = adp_analysis.get('best_value')
            if best_value:
                console.print(f"\n⭐ BEST VALUE: {best_value['name']} ({best_value['position']}) - {best_value['recommendation']}", style="bold green")


async def show_league_info():
    """Display league information in a nice format"""
    username = os.getenv('SLEEPER_USERNAME')
    league_id = os.getenv('SLEEPER_LEAGUE_ID')
    
    async with SleeperClient(username=username, league_id=league_id) as client:
        try:
            league = await client.get_league_info()
            rosters = await client.get_league_rosters()
            
            # League info table
            table = Table(title="League Information")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("League Name", league.get('name', 'Unknown'))
            table.add_row("Total Teams", str(league.get('total_rosters', 0)))
            table.add_row("League Status", league.get('status', 'Unknown'))
            table.add_row("Season", str(league.get('season', 2025)))
            
            # Scoring settings
            scoring = league.get('scoring_settings', {})
            ppr = scoring.get('rec', 0)
            if ppr == 1:
                scoring_type = "Full PPR"
            elif ppr == 0.5:
                scoring_type = "Half PPR" 
            else:
                scoring_type = "Standard"
            table.add_row("Scoring", scoring_type)
            
            # Draft info
            draft_id = league.get('draft_id')
            if draft_id:
                table.add_row("Draft ID", draft_id)
                
                # Get draft info
                draft_info = await client.get_draft_info(draft_id)
                table.add_row("Draft Type", draft_info.get('type', 'Unknown'))
                table.add_row("Draft Status", draft_info.get('status', 'Unknown'))
                
                # Check for SUPERFLEX
                roster_positions = league.get('roster_positions', [])
                has_superflex = 'SUPER_FLEX' in roster_positions
                table.add_row("SUPERFLEX League", "YES" if has_superflex else "NO")
                
                if has_superflex:
                    table.add_row("⚠️ Important", "QBs are MORE valuable in SUPERFLEX!")
            
            console.print(table)
            
        except Exception as e:
            console.print(f"❌ Error: {e}", style="red")


if __name__ == "__main__":
    # Add some startup info
    console.print("🏈 Fantasy Football Draft Assistant", style="bold blue")
    console.print("Day 3 (Aug 7) - FantasyPros Rankings Integration\n", style="dim")
    
    cli()