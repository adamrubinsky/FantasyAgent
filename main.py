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

# Load environment variables - try local first, then default
load_dotenv('.env.local')  # For local development with real credentials
load_dotenv()              # Fallback to .env (with placeholders)

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
    console.print("Day 1 (Aug 5) - Basic Setup & Sleeper Connection\n", style="dim")
    
    cli()