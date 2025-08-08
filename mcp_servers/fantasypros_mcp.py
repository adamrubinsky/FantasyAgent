#!/usr/bin/env python3
"""
FantasyPros MCP Server for AWS Bedrock AgentCore
Day 3: MCP-compatible server for FantasyPros rankings integration

This server can be deployed to AgentCore Runtime and provides
MCP tools for accessing FantasyPros rankings, projections, and ADP data.

For local development, this just provides regular Python functions.
When deployed to AgentCore, these functions become MCP tools.
"""

from typing import Dict, List, Optional, Any
import os
import json
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup
import asyncio
import aiohttp

# Try to import MCP, but don't fail if not available (for local development)
try:
    from mcp import FastMCP
    mcp = FastMCP("FantasyPros Fantasy Football Server")
    HAS_MCP = True
except ImportError:
    # Local development mode - no MCP decorators
    HAS_MCP = False
    def tool_decorator(func):
        """Dummy decorator for local development"""
        return func

# Data directory for caching (will be mounted in AgentCore)
DATA_DIR = Path("/tmp/fantasypros_data")
DATA_DIR.mkdir(exist_ok=True)

# Cache configuration
CACHE_DURATION_HOURS = 1  # Refresh cache every hour
POSITION_LIMITS = {
    "QB": 100,    # Top 100 QBs (32 starters + backups + rookies)
    "RB": 150,    # Top 150 RBs (position scarcity)
    "WR": 200,    # Top 200 WRs (most positions needed)
    "TE": 100,    # Top 100 TEs
    "K": 32,      # Top 32 Kickers (one per team)
    "DST": 32,    # Top 32 Defenses (one per team)
    "OVERALL": 500  # Top 500 overall for comprehensive rankings
}

# For local development, we'll use mock data
# In production, this would connect to FantasyPros API or use cached exports
MOCK_RANKINGS = {
    "superflex_half_ppr": {
        "last_updated": "2025-08-07T10:00:00",
        "format": "superflex",
        "scoring": "half_ppr",
        "players": [
            {"rank": 1, "name": "Saquon Barkley", "team": "PHI", "position": "RB", "adp": 1.2, "tier": 1},
            {"rank": 2, "name": "Josh Allen", "team": "BUF", "position": "QB", "adp": 2.1, "tier": 1},
            {"rank": 3, "name": "Lamar Jackson", "team": "BAL", "position": "QB", "adp": 3.5, "tier": 1},
            {"rank": 4, "name": "CeeDee Lamb", "team": "DAL", "position": "WR", "adp": 2.8, "tier": 1},
            {"rank": 5, "name": "Justin Jefferson", "team": "MIN", "position": "WR", "adp": 3.2, "tier": 1},
            {"rank": 6, "name": "Patrick Mahomes", "team": "KC", "position": "QB", "adp": 6.1, "tier": 1},
            {"rank": 7, "name": "Tyreek Hill", "team": "MIA", "position": "WR", "adp": 4.5, "tier": 1},
            {"rank": 8, "name": "Jahmyr Gibbs", "team": "DET", "position": "RB", "adp": 7.8, "tier": 1},
            {"rank": 9, "name": "Bijan Robinson", "team": "ATL", "position": "RB", "adp": 8.2, "tier": 1},
            {"rank": 10, "name": "Dak Prescott", "team": "DAL", "position": "QB", "adp": 10.5, "tier": 1},
            {"rank": 11, "name": "Ja'Marr Chase", "team": "CIN", "position": "WR", "adp": 11.3, "tier": 1},
            {"rank": 12, "name": "Amon-Ra St. Brown", "team": "DET", "position": "WR", "adp": 12.1, "tier": 1},
            {"rank": 13, "name": "Puka Nacua", "team": "LAR", "position": "WR", "adp": 13.7, "tier": 2},
            {"rank": 14, "name": "Breece Hall", "team": "NYJ", "position": "RB", "adp": 14.2, "tier": 2},
            {"rank": 15, "name": "Jonathan Taylor", "team": "IND", "position": "RB", "adp": 15.8, "tier": 2},
            {"rank": 16, "name": "Christian McCaffrey", "team": "SF", "position": "RB", "adp": 16.4, "tier": 2},
            {"rank": 17, "name": "Travis Kelce", "team": "KC", "position": "TE", "adp": 17.1, "tier": 2},
            {"rank": 18, "name": "Anthony Richardson", "team": "IND", "position": "QB", "adp": 18.3, "tier": 2},
            {"rank": 19, "name": "Cooper Kupp", "team": "LAR", "position": "WR", "adp": 19.2, "tier": 2},
            {"rank": 20, "name": "Stefon Diggs", "team": "HOU", "position": "WR", "adp": 20.1, "tier": 2},
            {"rank": 21, "name": "Derrick Henry", "team": "BAL", "position": "RB", "adp": 21.5, "tier": 2},
            {"rank": 22, "name": "Kyler Murray", "team": "ARI", "position": "QB", "adp": 22.3, "tier": 2},
            {"rank": 23, "name": "A.J. Brown", "team": "PHI", "position": "WR", "adp": 23.1, "tier": 2},
            {"rank": 24, "name": "Mike Evans", "team": "TB", "position": "WR", "adp": 24.2, "tier": 2},
            {"rank": 25, "name": "Tee Higgins", "team": "CIN", "position": "WR", "adp": 25.4, "tier": 2},
            {"rank": 26, "name": "DK Metcalf", "team": "SEA", "position": "WR", "adp": 26.1, "tier": 2},
            {"rank": 27, "name": "DeVonta Smith", "team": "PHI", "position": "WR", "adp": 27.3, "tier": 2},
            {"rank": 28, "name": "Keenan Allen", "team": "CHI", "position": "WR", "adp": 28.7, "tier": 2},
            {"rank": 29, "name": "Joe Burrow", "team": "CIN", "position": "QB", "adp": 29.2, "tier": 2},
            {"rank": 30, "name": "Amari Cooper", "team": "CLE", "position": "WR", "adp": 30.1, "tier": 2},
            {"rank": 31, "name": "Josh Jacobs", "team": "GB", "position": "RB", "adp": 31.4, "tier": 2},
            {"rank": 32, "name": "Isiah Pacheco", "team": "KC", "position": "RB", "adp": 32.2, "tier": 2},
            {"rank": 33, "name": "Jalen Hurts", "team": "PHI", "position": "QB", "adp": 33.1, "tier": 2},
            {"rank": 34, "name": "Mark Andrews", "team": "BAL", "position": "TE", "adp": 34.3, "tier": 2},
            {"rank": 35, "name": "Kenneth Walker III", "team": "SEA", "position": "RB", "adp": 35.2, "tier": 2},
            {"rank": 36, "name": "Davante Adams", "team": "LV", "position": "WR", "adp": 36.1, "tier": 2},
            {"rank": 37, "name": "Chris Olave", "team": "NO", "position": "WR", "adp": 37.4, "tier": 3},
            {"rank": 38, "name": "Drake London", "team": "ATL", "position": "WR", "adp": 38.2, "tier": 3},
            {"rank": 39, "name": "Garrett Wilson", "team": "NYJ", "position": "WR", "adp": 39.1, "tier": 3},
            {"rank": 40, "name": "DJ Moore", "team": "CHI", "position": "WR", "adp": 40.2, "tier": 3},
            {"rank": 41, "name": "Rhamondre Stevenson", "team": "NE", "position": "RB", "adp": 41.3, "tier": 3},
            {"rank": 42, "name": "Caleb Williams", "team": "CHI", "position": "QB", "adp": 42.1, "tier": 3},
            {"rank": 43, "name": "Malik Nabers", "team": "NYG", "position": "WR", "adp": 43.4, "tier": 3},
            {"rank": 44, "name": "Tony Pollard", "team": "TEN", "position": "RB", "adp": 44.2, "tier": 3},
            {"rank": 45, "name": "Sam LaPorta", "team": "DET", "position": "TE", "adp": 45.1, "tier": 3},
            {"rank": 46, "name": "Marvin Harrison Jr.", "team": "ARI", "position": "WR", "adp": 46.3, "tier": 3},
            {"rank": 47, "name": "Aaron Jones", "team": "MIN", "position": "RB", "adp": 47.2, "tier": 3},
            {"rank": 48, "name": "Tua Tagovailoa", "team": "MIA", "position": "QB", "adp": 48.1, "tier": 3},
            {"rank": 49, "name": "Terry McLaurin", "team": "WAS", "position": "WR", "adp": 49.4, "tier": 3},
            {"rank": 50, "name": "Calvin Ridley", "team": "TEN", "position": "WR", "adp": 50.5, "tier": 3},
            {"rank": 51, "name": "Rachaad White", "team": "TB", "position": "RB", "adp": 51.2, "tier": 3},
            {"rank": 52, "name": "Rome Odunze", "team": "CHI", "position": "WR", "adp": 52.3, "tier": 3},
            {"rank": 53, "name": "Jayden Daniels", "team": "WAS", "position": "QB", "adp": 53.1, "tier": 3},
            {"rank": 54, "name": "George Pickens", "team": "PIT", "position": "WR", "adp": 54.4, "tier": 3},
            {"rank": 55, "name": "Brock Purdy", "team": "SF", "position": "QB", "adp": 55.2, "tier": 3},
            {"rank": 56, "name": "Courtland Sutton", "team": "DEN", "position": "WR", "adp": 56.1, "tier": 3},
            {"rank": 57, "name": "De'Von Achane", "team": "MIA", "position": "RB", "adp": 57.3, "tier": 3},
            {"rank": 58, "name": "Brandon Aiyuk", "team": "SF", "position": "WR", "adp": 58.2, "tier": 3},
            {"rank": 59, "name": "Evan Engram", "team": "JAX", "position": "TE", "adp": 59.1, "tier": 3},
            {"rank": 60, "name": "Jordan Love", "team": "GB", "position": "QB", "adp": 60.3, "tier": 3},
            {"rank": 61, "name": "Tank Dell", "team": "HOU", "position": "WR", "adp": 61.2, "tier": 4},
            {"rank": 62, "name": "Diontae Johnson", "team": "CAR", "position": "WR", "adp": 62.4, "tier": 4},
            {"rank": 63, "name": "James Cook", "team": "BUF", "position": "RB", "adp": 63.1, "tier": 4},
            {"rank": 64, "name": "Zay Flowers", "team": "BAL", "position": "WR", "adp": 64.3, "tier": 4},
            {"rank": 65, "name": "David Montgomery", "team": "DET", "position": "RB", "adp": 65.2, "tier": 4},
            {"rank": 66, "name": "Trey McBride", "team": "ARI", "position": "TE", "adp": 66.1, "tier": 4},
            {"rank": 67, "name": "Zamir White", "team": "LV", "position": "RB", "adp": 67.4, "tier": 4},
            {"rank": 68, "name": "Hollywood Brown", "team": "KC", "position": "WR", "adp": 68.2, "tier": 4},
            {"rank": 69, "name": "C.J. Stroud", "team": "HOU", "position": "QB", "adp": 69.1, "tier": 4},
            {"rank": 70, "name": "Christian Watson", "team": "GB", "position": "WR", "adp": 70.1, "tier": 4},
            {"rank": 71, "name": "Najee Harris", "team": "PIT", "position": "RB", "adp": 71.3, "tier": 4},
            {"rank": 72, "name": "Jordan Addison", "team": "MIN", "position": "WR", "adp": 72.2, "tier": 4},
            {"rank": 73, "name": "Alvin Kamara", "team": "NO", "position": "RB", "adp": 73.4, "tier": 4},
            {"rank": 74, "name": "Michael Pittman Jr.", "team": "IND", "position": "WR", "adp": 74.1, "tier": 4},
            {"rank": 75, "name": "Ladd McConkey", "team": "LAC", "position": "WR", "adp": 75.3, "tier": 4},
            {"rank": 76, "name": "Kyle Pitts", "team": "ATL", "position": "TE", "adp": 76.2, "tier": 4},
            {"rank": 77, "name": "Javonte Williams", "team": "DEN", "position": "RB", "adp": 77.1, "tier": 4},
            {"rank": 78, "name": "Brian Thomas Jr.", "team": "JAX", "position": "WR", "adp": 78.4, "tier": 4},
            {"rank": 79, "name": "Joe Mixon", "team": "HOU", "position": "RB", "adp": 79.2, "tier": 4},
            {"rank": 80, "name": "Xavier Worthy", "team": "KC", "position": "WR", "adp": 80.3, "tier": 4},
            {"rank": 81, "name": "Jerome Ford", "team": "CLE", "position": "RB", "adp": 81.1, "tier": 4},
            {"rank": 82, "name": "Deebo Samuel", "team": "SF", "position": "WR", "adp": 82.4, "tier": 4},
            {"rank": 83, "name": "Dallas Goedert", "team": "PHI", "position": "TE", "adp": 83.2, "tier": 4},
            {"rank": 84, "name": "Deon Jackson", "team": "IND", "position": "RB", "adp": 84.3, "tier": 4},
            {"rank": 85, "name": "Jaxon Smith-Njigba", "team": "SEA", "position": "WR", "adp": 85.1, "tier": 4},
            {"rank": 86, "name": "Trevor Lawrence", "team": "JAX", "position": "QB", "adp": 86.4, "tier": 4},
            {"rank": 87, "name": "Tyler Lockett", "team": "SEA", "position": "WR", "adp": 87.2, "tier": 4},
            {"rank": 88, "name": "Gus Edwards", "team": "LAC", "position": "RB", "adp": 88.1, "tier": 4},
            {"rank": 89, "name": "Rashee Rice", "team": "KC", "position": "WR", "adp": 89.3, "tier": 4},
            {"rank": 90, "name": "Kendre Miller", "team": "NO", "position": "RB", "adp": 90.2, "tier": 4},
            {"rank": 91, "name": "Wandale Robinson", "team": "NYG", "position": "WR", "adp": 91.4, "tier": 4},
            {"rank": 92, "name": "Jake Ferguson", "team": "DAL", "position": "TE", "adp": 92.1, "tier": 4},
            {"rank": 93, "name": "Khalil Shakir", "team": "BUF", "position": "WR", "adp": 93.3, "tier": 4},
            {"rank": 94, "name": "Bo Nix", "team": "DEN", "position": "QB", "adp": 94.2, "tier": 4},
            {"rank": 95, "name": "Jakobi Meyers", "team": "LV", "position": "WR", "adp": 95.1, "tier": 4},
            {"rank": 96, "name": "Antonio Gibson", "team": "NE", "position": "RB", "adp": 96.4, "tier": 4},
            {"rank": 97, "name": "DeAndre Hopkins", "team": "TEN", "position": "WR", "adp": 97.2, "tier": 4},
            {"rank": 98, "name": "Isaiah Likely", "team": "BAL", "position": "TE", "adp": 98.3, "tier": 4},
            {"rank": 99, "name": "Tyjae Spears", "team": "TEN", "position": "RB", "adp": 99.1, "tier": 4},
            {"rank": 100, "name": "Geno Smith", "team": "SEA", "position": "QB", "adp": 100.2, "tier": 4},
            {"rank": 101, "name": "Jaylen Waddle", "team": "MIA", "position": "WR", "adp": 101.3, "tier": 5},
            {"rank": 102, "name": "Tyler Allgeier", "team": "ATL", "position": "RB", "adp": 102.1, "tier": 5},
            {"rank": 103, "name": "Jameson Williams", "team": "DET", "position": "WR", "adp": 103.4, "tier": 5},
            {"rank": 104, "name": "Raheem Mostert", "team": "MIA", "position": "RB", "adp": 104.2, "tier": 5},
            {"rank": 105, "name": "Pat Freiermuth", "team": "PIT", "position": "TE", "adp": 105.1, "tier": 5},
            {"rank": 106, "name": "Ameer Abdullah", "team": "LV", "position": "RB", "adp": 106.3, "tier": 5},
            {"rank": 107, "name": "Jayden Reed", "team": "GB", "position": "WR", "adp": 107.2, "tier": 5},
            {"rank": 108, "name": "J.K. Dobbins", "team": "LAC", "position": "RB", "adp": 108.4, "tier": 5},
            {"rank": 109, "name": "Daniel Jones", "team": "NYG", "position": "QB", "adp": 109.1, "tier": 5},
            {"rank": 110, "name": "Adam Thielen", "team": "CAR", "position": "WR", "adp": 110.3, "tier": 5},
            {"rank": 111, "name": "Chuba Hubbard", "team": "CAR", "position": "RB", "adp": 111.2, "tier": 5},
            {"rank": 112, "name": "Tyler Higbee", "team": "LAR", "position": "TE", "adp": 112.1, "tier": 5},
            {"rank": 113, "name": "Brandin Cooks", "team": "DAL", "position": "WR", "adp": 113.4, "tier": 5},
            {"rank": 114, "name": "Aaron Rodgers", "team": "NYJ", "position": "QB", "adp": 114.2, "tier": 5},
            {"rank": 115, "name": "Miles Sanders", "team": "CAR", "position": "RB", "adp": 115.3, "tier": 5},
            {"rank": 116, "name": "Curtis Samuel", "team": "BUF", "position": "WR", "adp": 116.1, "tier": 5},
            {"rank": 117, "name": "D'Andre Swift", "team": "CHI", "position": "RB", "adp": 117.4, "tier": 5},
            {"rank": 118, "name": "Cole Kmet", "team": "CHI", "position": "TE", "adp": 118.2, "tier": 5},
            {"rank": 119, "name": "Jerry Jeudy", "team": "CLE", "position": "WR", "adp": 119.3, "tier": 5},
            {"rank": 120, "name": "Kareem Hunt", "team": "KC", "position": "RB", "adp": 120.1, "tier": 5},
            {"rank": 121, "name": "Elijah Moore", "team": "CLE", "position": "WR", "adp": 121.4, "tier": 5},
            {"rank": 122, "name": "Darren Waller", "team": "NYG", "position": "TE", "adp": 122.2, "tier": 5},
            {"rank": 123, "name": "Russell Wilson", "team": "PIT", "position": "QB", "adp": 123.3, "tier": 5},
            {"rank": 124, "name": "Dandre Swift", "team": "CHI", "position": "RB", "adp": 124.1, "tier": 5},
            {"rank": 125, "name": "Mike Williams", "team": "NYJ", "position": "WR", "adp": 125.4, "tier": 5},
            {"rank": 126, "name": "Hunter Henry", "team": "NE", "position": "TE", "adp": 126.2, "tier": 5},
            {"rank": 127, "name": "Jalen Tolbert", "team": "DAL", "position": "WR", "adp": 127.3, "tier": 5},
            {"rank": 128, "name": "Kirk Cousins", "team": "ATL", "position": "QB", "adp": 128.1, "tier": 5},
            {"rank": 129, "name": "Roschon Johnson", "team": "CHI", "position": "RB", "adp": 129.4, "tier": 5},
            {"rank": 130, "name": "Darnell Mooney", "team": "ATL", "position": "WR", "adp": 130.2, "tier": 5},
            {"rank": 131, "name": "Rico Dowdle", "team": "DAL", "position": "RB", "adp": 131.3, "tier": 5},
            {"rank": 132, "name": "Noah Brown", "team": "WAS", "position": "WR", "adp": 132.1, "tier": 5},
            {"rank": 133, "name": "Cade Otton", "team": "TB", "position": "TE", "adp": 133.4, "tier": 5},
            {"rank": 134, "name": "Ezekiel Elliott", "team": "DAL", "position": "RB", "adp": 134.2, "tier": 5},
            {"rank": 135, "name": "Derek Carr", "team": "NO", "position": "QB", "adp": 135.3, "tier": 5},
            {"rank": 136, "name": "Josh Palmer", "team": "LAC", "position": "WR", "adp": 136.1, "tier": 5},
            {"rank": 137, "name": "Cam Akers", "team": "HOU", "position": "RB", "adp": 137.4, "tier": 5},
            {"rank": 138, "name": "Tutu Atwell", "team": "LAR", "position": "WR", "adp": 138.2, "tier": 5},
            {"rank": 139, "name": "Juwan Johnson", "team": "NO", "position": "TE", "adp": 139.3, "tier": 5},
            {"rank": 140, "name": "Trey Sermon", "team": "IND", "position": "RB", "adp": 140.1, "tier": 5},
            {"rank": 141, "name": "Cedrick Wilson Jr.", "team": "NO", "position": "WR", "adp": 141.4, "tier": 5},
            {"rank": 142, "name": "Anthony Desir", "team": "TB", "position": "RB", "adp": 142.2, "tier": 5},
            {"rank": 143, "name": "Will Dissly", "team": "LAC", "position": "TE", "adp": 143.3, "tier": 5},
            {"rank": 144, "name": "Mack Hollins", "team": "BUF", "position": "WR", "adp": 144.1, "tier": 5},
            {"rank": 145, "name": "Justin Fields", "team": "PIT", "position": "QB", "adp": 145.4, "tier": 5},
            {"rank": 146, "name": "Kenneth Gainwell", "team": "PHI", "position": "RB", "adp": 146.2, "tier": 5},
            {"rank": 147, "name": "Parris Campbell", "team": "NYG", "position": "WR", "adp": 147.3, "tier": 5},
            {"rank": 148, "name": "Tyler Conklin", "team": "NYJ", "position": "TE", "adp": 148.1, "tier": 5},
            {"rank": 149, "name": "Samaje Perine", "team": "KC", "position": "RB", "adp": 149.4, "tier": 5},
            {"rank": 150, "name": "DeVante Parker", "team": "NE", "position": "WR", "adp": 150.2, "tier": 5},
            {"rank": 151, "name": "Jaylen Warren", "team": "PIT", "position": "RB", "adp": 151.3, "tier": 6},
            {"rank": 152, "name": "Michael Wilson", "team": "ARI", "position": "WR", "adp": 152.1, "tier": 6},
            {"rank": 153, "name": "Brock Bowers", "team": "LV", "position": "TE", "adp": 153.4, "tier": 6},
            {"rank": 154, "name": "Clyde Edwards-Helaire", "team": "KC", "position": "RB", "adp": 154.2, "tier": 6},
            {"rank": 155, "name": "Gardner Minshew", "team": "LV", "position": "QB", "adp": 155.3, "tier": 6},
            {"rank": 156, "name": "Romeo Doubs", "team": "GB", "position": "WR", "adp": 156.1, "tier": 6},
            {"rank": 157, "name": "Ty Chandler", "team": "MIN", "position": "RB", "adp": 157.4, "tier": 6},
            {"rank": 158, "name": "Jalen McMillan", "team": "TB", "position": "WR", "adp": 158.2, "tier": 6},
            {"rank": 159, "name": "Jayden Higgins", "team": "HOU", "position": "WR", "adp": 159.2, "tier": 8},
            {"rank": 160, "name": "Romeo Doubs", "team": "GB", "position": "WR", "adp": 160.1, "tier": 6},
            {"rank": 161, "name": "Dontayvion Wicks", "team": "GB", "position": "WR", "adp": 161.4, "tier": 6},
            {"rank": 162, "name": "Tyler Boyd", "team": "TEN", "position": "WR", "adp": 162.3, "tier": 6},
            {"rank": 163, "name": "Wan'Dale Robinson", "team": "NYG", "position": "WR", "adp": 163.1, "tier": 6},
            {"rank": 164, "name": "Dameon Pierce", "team": "HOU", "position": "RB", "adp": 164.4, "tier": 6},
            {"rank": 165, "name": "Aidan O'Connell", "team": "LV", "position": "QB", "adp": 165.2, "tier": 6},
            {"rank": 166, "name": "Quentin Johnston", "team": "LAC", "position": "WR", "adp": 166.3, "tier": 6},
            {"rank": 167, "name": "Ray Davis", "team": "BUF", "position": "RB", "adp": 167.1, "tier": 6},
            {"rank": 168, "name": "Luke Musgrave", "team": "GB", "position": "TE", "adp": 168.4, "tier": 6},
            {"rank": 169, "name": "Tre Tucker", "team": "LV", "position": "WR", "adp": 169.2, "tier": 6},
            {"rank": 170, "name": "Jordan Mason", "team": "SF", "position": "RB", "adp": 170.3, "tier": 6},
            {"rank": 171, "name": "Keon Coleman", "team": "BUF", "position": "WR", "adp": 171.1, "tier": 6},
            {"rank": 172, "name": "Hayden Hurst", "team": "LAC", "position": "TE", "adp": 172.4, "tier": 6},
            {"rank": 173, "name": "Jaleel McLaughlin", "team": "DEN", "position": "RB", "adp": 173.2, "tier": 6},
            {"rank": 174, "name": "Bryce Young", "team": "CAR", "position": "QB", "adp": 174.3, "tier": 6},
            {"rank": 175, "name": "Adonai Mitchell", "team": "IND", "position": "WR", "adp": 175.1, "tier": 6},
            {"rank": 176, "name": "Craig Reynolds", "team": "DET", "position": "RB", "adp": 176.4, "tier": 6},
            {"rank": 177, "name": "Tucker Kraft", "team": "GB", "position": "TE", "adp": 177.2, "tier": 6},
            {"rank": 178, "name": "Zach Charbonnet", "team": "SEA", "position": "RB", "adp": 178.3, "tier": 6},
            {"rank": 179, "name": "Jonnu Smith", "team": "MIA", "position": "TE", "adp": 179.1, "tier": 6},
            {"rank": 180, "name": "Jahan Dotson", "team": "WAS", "position": "WR", "adp": 180.4, "tier": 6},
            {"rank": 181, "name": "Justice Hill", "team": "BAL", "position": "RB", "adp": 181.2, "tier": 6},
            {"rank": 182, "name": "Mac Jones", "team": "JAX", "position": "QB", "adp": 182.3, "tier": 6},
            {"rank": 183, "name": "Darius Slayton", "team": "NYG", "position": "WR", "adp": 183.1, "tier": 6},
            {"rank": 184, "name": "Blake Corum", "team": "LAR", "position": "RB", "adp": 184.4, "tier": 6},
            {"rank": 185, "name": "Marquez Valdes-Scantling", "team": "BUF", "position": "WR", "adp": 185.2, "tier": 6},
            {"rank": 186, "name": "Mike Gesicki", "team": "CIN", "position": "TE", "adp": 186.3, "tier": 6},
            {"rank": 187, "name": "Tank Bigsby", "team": "JAX", "position": "RB", "adp": 187.1, "tier": 6},
            {"rank": 188, "name": "Sam Howell", "team": "SEA", "position": "QB", "adp": 188.4, "tier": 6},
            {"rank": 189, "name": "KJ Osborn", "team": "NE", "position": "WR", "adp": 189.2, "tier": 6},
            {"rank": 190, "name": "MarShawn Lloyd", "team": "GB", "position": "RB", "adp": 190.3, "tier": 6},
            {"rank": 191, "name": "Demarcus Robinson", "team": "LAR", "position": "WR", "adp": 191.1, "tier": 6},
            {"rank": 192, "name": "Chigoziem Okonkwo", "team": "TEN", "position": "TE", "adp": 192.4, "tier": 6},
            {"rank": 193, "name": "Keaton Mitchell", "team": "BAL", "position": "RB", "adp": 193.2, "tier": 6},
            {"rank": 194, "name": "Skyy Moore", "team": "KC", "position": "WR", "adp": 194.3, "tier": 6},
            {"rank": 195, "name": "Austin Hooper", "team": "NE", "position": "TE", "adp": 195.1, "tier": 6},
            {"rank": 196, "name": "AJ Dillon", "team": "GB", "position": "RB", "adp": 196.4, "tier": 6},
            {"rank": 197, "name": "Anthony Miller", "team": "BAL", "position": "WR", "adp": 197.2, "tier": 6},
            {"rank": 198, "name": "Malik Washington", "team": "MIA", "position": "WR", "adp": 198.3, "tier": 6},
            {"rank": 199, "name": "Drew Lock", "team": "NYG", "position": "QB", "adp": 199.1, "tier": 6},
            {"rank": 200, "name": "Audric Estime", "team": "DEN", "position": "RB", "adp": 200.4, "tier": 6},
            {"rank": 201, "name": "Jermaine Burton", "team": "CIN", "position": "WR", "adp": 201.2, "tier": 7},
            {"rank": 202, "name": "Kimani Vidal", "team": "LAC", "position": "RB", "adp": 202.3, "tier": 7},
            {"rank": 203, "name": "Ricky Pearsall", "team": "SF", "position": "WR", "adp": 203.1, "tier": 7},
            {"rank": 204, "name": "Braelon Allen", "team": "NYJ", "position": "RB", "adp": 204.4, "tier": 7},
            {"rank": 205, "name": "Erick All", "team": "CIN", "position": "TE", "adp": 205.2, "tier": 7},
            {"rank": 206, "name": "Xavier Legette", "team": "CAR", "position": "WR", "adp": 206.3, "tier": 7},
            {"rank": 207, "name": "Isaiah Davis", "team": "NYJ", "position": "RB", "adp": 207.1, "tier": 7},
            {"rank": 208, "name": "Ben Skowronek", "team": "PIT", "position": "WR", "adp": 208.4, "tier": 7},
            {"rank": 209, "name": "Tylan Wallace", "team": "BAL", "position": "WR", "adp": 209.2, "tier": 7},
            {"rank": 210, "name": "Sean Tucker", "team": "TB", "position": "RB", "adp": 210.3, "tier": 7},
            {"rank": 211, "name": "Clayton Tune", "team": "ARI", "position": "QB", "adp": 211.1, "tier": 7},
            {"rank": 212, "name": "Devaughn Vele", "team": "DEN", "position": "WR", "adp": 212.4, "tier": 7},
            {"rank": 213, "name": "Bucky Irving", "team": "TB", "position": "RB", "adp": 213.2, "tier": 7},
            {"rank": 214, "name": "Ja'Lynn Polk", "team": "NE", "position": "WR", "adp": 214.3, "tier": 7},
            {"rank": 215, "name": "Dylan Laube", "team": "LV", "position": "RB", "adp": 215.1, "tier": 7},
            {"rank": 216, "name": "Jalen Coker", "team": "CAR", "position": "WR", "adp": 216.4, "tier": 7},
            {"rank": 217, "name": "Devin Culp", "team": "TB", "position": "TE", "adp": 217.2, "tier": 7},
            {"rank": 218, "name": "Troy Franklin", "team": "DEN", "position": "WR", "adp": 218.3, "tier": 7},
            {"rank": 219, "name": "Keilan Robinson", "team": "JAX", "position": "RB", "adp": 219.1, "tier": 7},
            {"rank": 220, "name": "Johnny Wilson", "team": "PHI", "position": "WR", "adp": 220.4, "tier": 7},
            {"rank": 221, "name": "Emari Demercado", "team": "ARI", "position": "RB", "adp": 221.2, "tier": 7},
            {"rank": 222, "name": "Ainias Smith", "team": "PHI", "position": "WR", "adp": 222.3, "tier": 7},
            {"rank": 223, "name": "Dalton Kincaid", "team": "BUF", "position": "TE", "adp": 223.1, "tier": 7},
            {"rank": 224, "name": "Devontez Walker", "team": "BAL", "position": "WR", "adp": 224.4, "tier": 7},
            {"rank": 225, "name": "Trey Benson", "team": "ARI", "position": "RB", "adp": 225.2, "tier": 7},
            {"rank": 226, "name": "Desmond Ridder", "team": "ARI", "position": "QB", "adp": 226.3, "tier": 7},
            {"rank": 227, "name": "Jacob Cowing", "team": "SF", "position": "WR", "adp": 227.1, "tier": 7},
            {"rank": 228, "name": "Jaylen Wright", "team": "MIA", "position": "RB", "adp": 228.4, "tier": 7},
            {"rank": 229, "name": "Luke McCaffrey", "team": "WAS", "position": "WR", "adp": 229.2, "tier": 7},
            {"rank": 230, "name": "Will Shipley", "team": "PHI", "position": "RB", "adp": 230.3, "tier": 7},
            {"rank": 231, "name": "Trey Palmer", "team": "TB", "position": "WR", "adp": 231.1, "tier": 7},
            {"rank": 232, "name": "Jordan Whittington", "team": "LAR", "position": "WR", "adp": 232.4, "tier": 7},
            {"rank": 233, "name": "Chris Rodriguez Jr.", "team": "WAS", "position": "RB", "adp": 233.2, "tier": 7},
            {"rank": 234, "name": "Malik Nabers", "team": "NYG", "position": "WR", "adp": 234.3, "tier": 7},
            {"rank": 235, "name": "Jake Browning", "team": "CIN", "position": "QB", "adp": 235.1, "tier": 7},
            {"rank": 236, "name": "Kendall Fuller", "team": "MIA", "position": "WR", "adp": 236.4, "tier": 7},
            {"rank": 237, "name": "Hassan Haskins", "team": "TEN", "position": "RB", "adp": 237.2, "tier": 7},
            {"rank": 238, "name": "Dionte Johnson", "team": "CAR", "position": "WR", "adp": 238.3, "tier": 7},
            {"rank": 239, "name": "C.J. Beathard", "team": "MIA", "position": "QB", "adp": 239.1, "tier": 7},
            {"rank": 240, "name": "Mason Tipton", "team": "NO", "position": "WR", "adp": 240.4, "tier": 7},
            {"rank": 241, "name": "Frank Gore Jr.", "team": "BUF", "position": "RB", "adp": 241.2, "tier": 7},
            {"rank": 242, "name": "Jalen Reagor", "team": "LAC", "position": "WR", "adp": 242.3, "tier": 7},
            {"rank": 243, "name": "Michael Mayer", "team": "LV", "position": "TE", "adp": 243.1, "tier": 7},
            {"rank": 244, "name": "Charlie Jones", "team": "CIN", "position": "WR", "adp": 244.4, "tier": 7},
            {"rank": 245, "name": "Dare Ogunbowale", "team": "HOU", "position": "RB", "adp": 245.2, "tier": 7},
            {"rank": 246, "name": "Malik Cunningham", "team": "NE", "position": "QB", "adp": 246.3, "tier": 7},
            {"rank": 247, "name": "Ty Johnson", "team": "BUF", "position": "RB", "adp": 247.1, "tier": 7},
            {"rank": 248, "name": "Kendrick Bourne", "team": "NE", "position": "WR", "adp": 248.4, "tier": 7},
            {"rank": 249, "name": "Donald Parham Jr.", "team": "LAC", "position": "TE", "adp": 249.2, "tier": 7},
            {"rank": 250, "name": "Brandon Johnson", "team": "DEN", "position": "WR", "adp": 250.3, "tier": 7},
            {"rank": 251, "name": "Ameer Abdullah", "team": "LV", "position": "RB", "adp": 251.1, "tier": 7},
            {"rank": 252, "name": "Trent Sherfield", "team": "MIN", "position": "WR", "adp": 252.4, "tier": 7},
            {"rank": 253, "name": "Tanner Hudson", "team": "CIN", "position": "TE", "adp": 253.2, "tier": 7},
            {"rank": 254, "name": "Noah Gray", "team": "KC", "position": "TE", "adp": 254.3, "tier": 7},
            {"rank": 255, "name": "Anthony Firkser", "team": "DET", "position": "TE", "adp": 255.1, "tier": 7},
            {"rank": 256, "name": "Nathan Rourke", "team": "NYG", "position": "QB", "adp": 256.4, "tier": 7},
            {"rank": 257, "name": "Malachi Corley", "team": "NYJ", "position": "WR", "adp": 257.2, "tier": 7},
            {"rank": 258, "name": "Tommy DeVito", "team": "NYG", "position": "QB", "adp": 258.3, "tier": 7},
            {"rank": 259, "name": "Velus Jones Jr.", "team": "CHI", "position": "WR", "adp": 259.1, "tier": 7},
            {"rank": 260, "name": "Durham Smythe", "team": "MIA", "position": "TE", "adp": 260.4, "tier": 7},
            {"rank": 261, "name": "Rashod Bateman", "team": "BAL", "position": "WR", "adp": 261.2, "tier": 7},
            {"rank": 262, "name": "Tyler Badie", "team": "DEN", "position": "RB", "adp": 262.3, "tier": 7},
            {"rank": 263, "name": "Mike White", "team": "MIA", "position": "QB", "adp": 263.1, "tier": 7},
            {"rank": 264, "name": "Irv Smith Jr.", "team": "KC", "position": "TE", "adp": 264.4, "tier": 7},
            {"rank": 265, "name": "JaQuan Hardy", "team": "BUF", "position": "RB", "adp": 265.2, "tier": 7},
            {"rank": 266, "name": "Tyler Scott", "team": "CHI", "position": "WR", "adp": 266.3, "tier": 7},
            {"rank": 267, "name": "Anthony Richardson", "team": "IND", "position": "QB", "adp": 267.1, "tier": 7},
            {"rank": 268, "name": "Parker Washington", "team": "JAX", "position": "WR", "adp": 268.4, "tier": 7},
            {"rank": 269, "name": "Zach Evans", "team": "LAR", "position": "RB", "adp": 269.2, "tier": 7},
            {"rank": 270, "name": "Robert Woods", "team": "HOU", "position": "WR", "adp": 270.3, "tier": 7},
            {"rank": 271, "name": "Kyahva Tezino", "team": "NO", "position": "RB", "adp": 271.1, "tier": 7},
            {"rank": 272, "name": "Taysom Hill", "team": "NO", "position": "TE", "adp": 272.4, "tier": 7},
            {"rank": 273, "name": "Taiwan Jones", "team": "BUF", "position": "RB", "adp": 273.2, "tier": 7},
            {"rank": 274, "name": "Kendall Milton", "team": "PHI", "position": "RB", "adp": 274.3, "tier": 7},
            {"rank": 275, "name": "Jarrett Stidham", "team": "DEN", "position": "QB", "adp": 275.1, "tier": 7},
            {"rank": 276, "name": "Quez Watkins", "team": "PIT", "position": "WR", "adp": 276.4, "tier": 7},
            {"rank": 277, "name": "Miller Forristall", "team": "TEN", "position": "TE", "adp": 277.2, "tier": 7},
            {"rank": 278, "name": "Alec Pierce", "team": "IND", "position": "WR", "adp": 278.3, "tier": 7},
            {"rank": 279, "name": "Kyle Juszczyk", "team": "SF", "position": "RB", "adp": 279.1, "tier": 7},
            {"rank": 280, "name": "Stone Smartt", "team": "LAC", "position": "TE", "adp": 280.4, "tier": 7},
            {"rank": 281, "name": "Daijun Edwards", "team": "GB", "position": "RB", "adp": 281.2, "tier": 7},
            {"rank": 282, "name": "Bailey Zappe", "team": "NE", "position": "QB", "adp": 282.3, "tier": 7},
            {"rank": 283, "name": "KJ Hamler", "team": "BUF", "position": "WR", "adp": 283.1, "tier": 7},
            {"rank": 284, "name": "Cam Rising", "team": "JAX", "position": "QB", "adp": 284.4, "tier": 7},
            {"rank": 285, "name": "Greg Dulcich", "team": "DEN", "position": "TE", "adp": 285.2, "tier": 7},
            {"rank": 286, "name": "Deuce Vaughn", "team": "DAL", "position": "RB", "adp": 286.3, "tier": 7},
            {"rank": 287, "name": "Mason Rudolph", "team": "TEN", "position": "QB", "adp": 287.1, "tier": 7},
            {"rank": 288, "name": "DJ Turner", "team": "LV", "position": "WR", "adp": 288.4, "tier": 7},
            {"rank": 289, "name": "Keaontay Ingram", "team": "KC", "position": "RB", "adp": 289.2, "tier": 7},
            {"rank": 290, "name": "Tanner McKee", "team": "PHI", "position": "QB", "adp": 290.3, "tier": 7},
            {"rank": 291, "name": "Reggie Roberson Jr.", "team": "ATL", "position": "WR", "adp": 291.1, "tier": 7},
            {"rank": 292, "name": "Charlie Kolar", "team": "BAL", "position": "TE", "adp": 292.4, "tier": 7},
            {"rank": 293, "name": "D'Onta Foreman", "team": "CLE", "position": "RB", "adp": 293.2, "tier": 7},
            {"rank": 294, "name": "Will Mallory", "team": "IND", "position": "TE", "adp": 294.3, "tier": 7},
            {"rank": 295, "name": "Jordan Travis", "team": "NYJ", "position": "QB", "adp": 295.1, "tier": 7},
            {"rank": 296, "name": "Chris Evans", "team": "CIN", "position": "RB", "adp": 296.4, "tier": 7},
            {"rank": 297, "name": "Malik Heath", "team": "GB", "position": "WR", "adp": 297.2, "tier": 7},
            {"rank": 298, "name": "Ben Skowronek", "team": "HOU", "position": "WR", "adp": 298.3, "tier": 7},
            {"rank": 299, "name": "Jake Haener", "team": "NO", "position": "QB", "adp": 299.1, "tier": 7},
            {"rank": 300, "name": "Jalen Guyton", "team": "DAL", "position": "WR", "adp": 300.4, "tier": 7},
            {"rank": 301, "name": "Justin Tucker", "team": "BAL", "position": "K", "adp": 301.1, "tier": 8},
            {"rank": 302, "name": "Harrison Butker", "team": "KC", "position": "K", "adp": 302.2, "tier": 8},
            {"rank": 303, "name": "Tyler Bass", "team": "BUF", "position": "K", "adp": 303.3, "tier": 8},
            {"rank": 304, "name": "Jake Elliott", "team": "PHI", "position": "K", "adp": 304.1, "tier": 8},
            {"rank": 305, "name": "Daniel Carlson", "team": "LV", "position": "K", "adp": 305.2, "tier": 8},
            {"rank": 306, "name": "Younghoe Koo", "team": "ATL", "position": "K", "adp": 306.3, "tier": 8},
            {"rank": 307, "name": "Cameron Dicker", "team": "LAC", "position": "K", "adp": 307.1, "tier": 8},
            {"rank": 308, "name": "Chris Boswell", "team": "PIT", "position": "K", "adp": 308.2, "tier": 8},
            {"rank": 309, "name": "Jason Sanders", "team": "MIA", "position": "K", "adp": 309.3, "tier": 8},
            {"rank": 310, "name": "Brandon McManus", "team": "GB", "position": "K", "adp": 310.1, "tier": 8},
            {"rank": 311, "name": "Wil Lutz", "team": "DEN", "position": "K", "adp": 311.2, "tier": 8},
            {"rank": 312, "name": "Jake Moody", "team": "SF", "position": "K", "adp": 312.3, "tier": 8},
            {"rank": 313, "name": "Nick Folk", "team": "TEN", "position": "K", "adp": 313.1, "tier": 8},
            {"rank": 314, "name": "Cairo Santos", "team": "CHI", "position": "K", "adp": 314.2, "tier": 8},
            {"rank": 315, "name": "Jason Myers", "team": "SEA", "position": "K", "adp": 315.3, "tier": 8},
            {"rank": 316, "name": "Greg Zuerlein", "team": "NYJ", "position": "K", "adp": 316.1, "tier": 8},
            {"rank": 317, "name": "Evan McPherson", "team": "CIN", "position": "K", "adp": 317.2, "tier": 8},
            {"rank": 318, "name": "Matt Gay", "team": "IND", "position": "K", "adp": 318.3, "tier": 8},
            {"rank": 319, "name": "Dustin Hopkins", "team": "CLE", "position": "K", "adp": 319.1, "tier": 8},
            {"rank": 320, "name": "Graham Gano", "team": "NYG", "position": "K", "adp": 320.2, "tier": 8},
            {"rank": 321, "name": "Ka'imi Fairbairn", "team": "HOU", "position": "K", "adp": 321.3, "tier": 8},
            {"rank": 322, "name": "Blake Grupe", "team": "NO", "position": "K", "adp": 322.1, "tier": 8},
            {"rank": 323, "name": "Brandon Aubrey", "team": "DAL", "position": "K", "adp": 323.2, "tier": 8},
            {"rank": 324, "name": "Chase McLaughlin", "team": "TB", "position": "K", "adp": 324.3, "tier": 8},
            {"rank": 325, "name": "Matt Prater", "team": "ARI", "position": "K", "adp": 325.1, "tier": 8},
            {"rank": 326, "name": "Joshua Karty", "team": "LAR", "position": "K", "adp": 326.2, "tier": 8},
            {"rank": 327, "name": "Cade York", "team": "WAS", "position": "K", "adp": 327.3, "tier": 8},
            {"rank": 328, "name": "Anders Carlson", "team": "SF", "position": "K", "adp": 328.1, "tier": 8},
            {"rank": 329, "name": "Riley Patterson", "team": "DET", "position": "K", "adp": 329.2, "tier": 8},
            {"rank": 330, "name": "Eddy Pineiro", "team": "CAR", "position": "K", "adp": 330.3, "tier": 8},
            {"rank": 331, "name": "Joey Slye", "team": "NE", "position": "K", "adp": 331.1, "tier": 8},
            {"rank": 332, "name": "Spencer Shrader", "team": "JAX", "position": "K", "adp": 332.2, "tier": 8},
            {"rank": 333, "name": "Ravens", "team": "BAL", "position": "DST", "adp": 333.1, "tier": 8},
            {"rank": 334, "name": "49ers", "team": "SF", "position": "DST", "adp": 334.2, "tier": 8},
            {"rank": 335, "name": "Bills", "team": "BUF", "position": "DST", "adp": 335.3, "tier": 8},
            {"rank": 336, "name": "Cowboys", "team": "DAL", "position": "DST", "adp": 336.1, "tier": 8},
            {"rank": 337, "name": "Eagles", "team": "PHI", "position": "DST", "adp": 337.2, "tier": 8},
            {"rank": 338, "name": "Chiefs", "team": "KC", "position": "DST", "adp": 338.3, "tier": 8},
            {"rank": 339, "name": "Jets", "team": "NYJ", "position": "DST", "adp": 339.1, "tier": 8},
            {"rank": 340, "name": "Steelers", "team": "PIT", "position": "DST", "adp": 340.2, "tier": 8},
            {"rank": 341, "name": "Dolphins", "team": "MIA", "position": "DST", "adp": 341.3, "tier": 8},
            {"rank": 342, "name": "Browns", "team": "CLE", "position": "DST", "adp": 342.1, "tier": 8},
            {"rank": 343, "name": "Lions", "team": "DET", "position": "DST", "adp": 343.2, "tier": 8},
            {"rank": 344, "name": "Packers", "team": "GB", "position": "DST", "adp": 344.3, "tier": 8},
            {"rank": 345, "name": "Chargers", "team": "LAC", "position": "DST", "adp": 345.1, "tier": 8},
            {"rank": 346, "name": "Saints", "team": "NO", "position": "DST", "adp": 346.2, "tier": 8},
            {"rank": 347, "name": "Seahawks", "team": "SEA", "position": "DST", "adp": 347.3, "tier": 8},
            {"rank": 348, "name": "Vikings", "team": "MIN", "position": "DST", "adp": 348.1, "tier": 8},
            {"rank": 349, "name": "Broncos", "team": "DEN", "position": "DST", "adp": 349.2, "tier": 8},
            {"rank": 350, "name": "Texans", "team": "HOU", "position": "DST", "adp": 350.3, "tier": 8},
            {"rank": 351, "name": "Raiders", "team": "LV", "position": "DST", "adp": 351.1, "tier": 8},
            {"rank": 352, "name": "Bengals", "team": "CIN", "position": "DST", "adp": 352.2, "tier": 8},
            {"rank": 353, "name": "Rams", "team": "LAR", "position": "DST", "adp": 353.3, "tier": 8},
            {"rank": 354, "name": "Colts", "team": "IND", "position": "DST", "adp": 354.1, "tier": 8},
            {"rank": 355, "name": "Cardinals", "team": "ARI", "position": "DST", "adp": 355.2, "tier": 8},
            {"rank": 356, "name": "Bears", "team": "CHI", "position": "DST", "adp": 356.3, "tier": 8},
            {"rank": 357, "name": "Falcons", "team": "ATL", "position": "DST", "adp": 357.1, "tier": 8},
            {"rank": 358, "name": "Buccaneers", "team": "TB", "position": "DST", "adp": 358.2, "tier": 8},
            {"rank": 359, "name": "Patriots", "team": "NE", "position": "DST", "adp": 359.3, "tier": 8},
            {"rank": 360, "name": "Titans", "team": "TEN", "position": "DST", "adp": 360.1, "tier": 8},
            {"rank": 361, "name": "Commanders", "team": "WAS", "position": "DST", "adp": 361.2, "tier": 8},
            {"rank": 362, "name": "Giants", "team": "NYG", "position": "DST", "adp": 362.3, "tier": 8},
            {"rank": 363, "name": "Jaguars", "team": "JAX", "position": "DST", "adp": 363.1, "tier": 8},
            {"rank": 364, "name": "Panthers", "team": "CAR", "position": "DST", "adp": 364.2, "tier": 8},
            {"rank": 365, "name": "Jacoby Brissett", "team": "NE", "position": "QB", "adp": 365.3, "tier": 8},
            {"rank": 366, "name": "Tyler Huntley", "team": "MIA", "position": "QB", "adp": 366.1, "tier": 8},
            {"rank": 367, "name": "Jameis Winston", "team": "CLE", "position": "QB", "adp": 367.2, "tier": 8},
            {"rank": 368, "name": "Andy Dalton", "team": "CAR", "position": "QB", "adp": 368.3, "tier": 8},
            {"rank": 369, "name": "Cooper Rush", "team": "DAL", "position": "QB", "adp": 369.1, "tier": 8},
            {"rank": 370, "name": "Mitch Trubisky", "team": "BUF", "position": "QB", "adp": 370.2, "tier": 8},
            {"rank": 371, "name": "Tyrod Taylor", "team": "NYG", "position": "QB", "adp": 371.3, "tier": 8},
            {"rank": 372, "name": "Ryan Tannehill", "team": "TEN", "position": "QB", "adp": 372.1, "tier": 8},
            {"rank": 373, "name": "Joshua Dobbs", "team": "SF", "position": "QB", "adp": 373.2, "tier": 8},
            {"rank": 374, "name": "Case Keenum", "team": "HOU", "position": "QB", "adp": 374.3, "tier": 8},
            {"rank": 375, "name": "Nick Foles", "team": "IND", "position": "QB", "adp": 375.1, "tier": 8},
            {"rank": 376, "name": "Blaine Gabbert", "team": "KC", "position": "QB", "adp": 376.2, "tier": 8},
            {"rank": 377, "name": "Joe Flacco", "team": "IND", "position": "QB", "adp": 377.3, "tier": 8},
            {"rank": 378, "name": "Matt Ryan", "team": "ATL", "position": "QB", "adp": 378.1, "tier": 8},
            {"rank": 379, "name": "Carson Wentz", "team": "WAS", "position": "QB", "adp": 379.2, "tier": 8},
            {"rank": 380, "name": "Mitchell Trubisky", "team": "PIT", "position": "QB", "adp": 380.3, "tier": 8},
            {"rank": 381, "name": "Teddy Bridgewater", "team": "MIA", "position": "QB", "adp": 381.1, "tier": 8},
            {"rank": 382, "name": "Ryan Fitzpatrick", "team": "NYJ", "position": "QB", "adp": 382.2, "tier": 8},
            {"rank": 383, "name": "Blake Bortles", "team": "GB", "position": "QB", "adp": 383.3, "tier": 8},
            {"rank": 384, "name": "Chad Henne", "team": "KC", "position": "QB", "adp": 384.1, "tier": 8},
            {"rank": 385, "name": "Boston Scott", "team": "PHI", "position": "RB", "adp": 385.2, "tier": 8},
            {"rank": 386, "name": "Jerick McKinnon", "team": "KC", "position": "RB", "adp": 386.3, "tier": 8},
            {"rank": 387, "name": "La'Rod Stephens-Howling", "team": "PIT", "position": "RB", "adp": 387.1, "tier": 8},
            {"rank": 388, "name": "Cordarrelle Patterson", "team": "PIT", "position": "RB", "adp": 388.2, "tier": 8},
            {"rank": 389, "name": "Latavius Murray", "team": "BUF", "position": "RB", "adp": 389.3, "tier": 8},
            {"rank": 390, "name": "Alex Collins", "team": "SEA", "position": "RB", "adp": 390.1, "tier": 8},
            {"rank": 391, "name": "Devonta Freeman", "team": "NO", "position": "RB", "adp": 391.2, "tier": 8},
            {"rank": 392, "name": "Jordan Howard", "team": "HOU", "position": "RB", "adp": 392.3, "tier": 8},
            {"rank": 393, "name": "Matt Breida", "team": "NYG", "position": "RB", "adp": 393.1, "tier": 8},
            {"rank": 394, "name": "Duke Johnson", "team": "BUF", "position": "RB", "adp": 394.2, "tier": 8},
            {"rank": 395, "name": "Nyheim Hines", "team": "CLE", "position": "RB", "adp": 395.3, "tier": 8},
            {"rank": 396, "name": "Phillip Lindsay", "team": "IND", "position": "RB", "adp": 396.1, "tier": 8},
            {"rank": 397, "name": "Dare Ogunbowale", "team": "WIS", "position": "RB", "adp": 397.2, "tier": 8},
            {"rank": 398, "name": "Deon Jackson", "team": "CLE", "position": "RB", "adp": 398.3, "tier": 8},
            {"rank": 399, "name": "Jeff Wilson Jr.", "team": "MIA", "position": "RB", "adp": 399.1, "tier": 8},
            {"rank": 400, "name": "Hassan Haskins", "team": "LAC", "position": "RB", "adp": 400.2, "tier": 8},
            {"rank": 401, "name": "Golden Tate", "team": "NYG", "position": "WR", "adp": 401.3, "tier": 8},
            {"rank": 402, "name": "Emmanuel Sanders", "team": "BUF", "position": "WR", "adp": 402.1, "tier": 8},
            {"rank": 403, "name": "Sterling Shepard", "team": "TB", "position": "WR", "adp": 403.2, "tier": 8},
            {"rank": 404, "name": "John Brown", "team": "LV", "position": "WR", "adp": 404.3, "tier": 8},
            {"rank": 405, "name": "Cole Beasley", "team": "TB", "position": "WR", "adp": 405.1, "tier": 8},
            {"rank": 406, "name": "Sammy Watkins", "team": "KC", "position": "WR", "adp": 406.2, "tier": 8},
            {"rank": 407, "name": "Preston Williams", "team": "MIA", "position": "WR", "adp": 407.3, "tier": 8},
            {"rank": 408, "name": "Allen Lazard", "team": "NYJ", "position": "WR", "adp": 408.1, "tier": 8},
            {"rank": 409, "name": "Mecole Hardman", "team": "KC", "position": "WR", "adp": 409.2, "tier": 8},
            {"rank": 410, "name": "Dante Pettis", "team": "CHI", "position": "WR", "adp": 410.3, "tier": 8},
            {"rank": 411, "name": "Isaiah Ford", "team": "MIA", "position": "WR", "adp": 411.1, "tier": 8},
            {"rank": 412, "name": "Chris Conley", "team": "HOU", "position": "WR", "adp": 412.2, "tier": 8},
            {"rank": 413, "name": "Robby Anderson", "team": "ARI", "position": "WR", "adp": 413.3, "tier": 8},
            {"rank": 414, "name": "Russell Gage", "team": "TB", "position": "WR", "adp": 414.1, "tier": 8},
            {"rank": 415, "name": "Olamide Zaccheaus", "team": "WAS", "position": "WR", "adp": 415.2, "tier": 8},
            {"rank": 416, "name": "Kalif Raymond", "team": "DET", "position": "WR", "adp": 416.3, "tier": 8},
            {"rank": 417, "name": "Nico Collins", "team": "HOU", "position": "WR", "adp": 417.1, "tier": 8},
            {"rank": 418, "name": "Tim Patrick", "team": "DEN", "position": "WR", "adp": 418.2, "tier": 8},
            {"rank": 419, "name": "N'Keal Harry", "team": "CHI", "position": "WR", "adp": 419.3, "tier": 8},
            {"rank": 420, "name": "Gabriel Davis", "team": "JAX", "position": "WR", "adp": 420.1, "tier": 8},
            {"rank": 421, "name": "Allen Robinson", "team": "PIT", "position": "WR", "adp": 421.2, "tier": 8},
            {"rank": 422, "name": "Marquise Goodwin", "team": "KC", "position": "WR", "adp": 422.3, "tier": 8},
            {"rank": 423, "name": "Jalen Guyton", "team": "LAC", "position": "WR", "adp": 423.1, "tier": 8},
            {"rank": 424, "name": "Donovan Peoples-Jones", "team": "DET", "position": "WR", "adp": 424.2, "tier": 8},
            {"rank": 425, "name": "Laviska Shenault Jr.", "team": "SEA", "position": "WR", "adp": 425.3, "tier": 8},
            {"rank": 426, "name": "Byron Pringle", "team": "WAS", "position": "WR", "adp": 426.1, "tier": 8},
            {"rank": 427, "name": "Terrace Marshall Jr.", "team": "CAR", "position": "WR", "adp": 427.2, "tier": 8},
            {"rank": 428, "name": "Collin Johnson", "team": "NYG", "position": "WR", "adp": 428.3, "tier": 8},
            {"rank": 429, "name": "Anthony Schwartz", "team": "CLE", "position": "WR", "adp": 429.1, "tier": 8},
            {"rank": 430, "name": "Dezmon Patmon", "team": "IND", "position": "WR", "adp": 430.2, "tier": 8},
            {"rank": 431, "name": "Isaiah McKenzie", "team": "IND", "position": "WR", "adp": 431.3, "tier": 8},
            {"rank": 432, "name": "Braxton Berrios", "team": "MIA", "position": "WR", "adp": 432.1, "tier": 8},
            {"rank": 433, "name": "Ray-Ray McCloud", "team": "ATL", "position": "WR", "adp": 433.2, "tier": 8},
            {"rank": 434, "name": "Gunner Olszewski", "team": "PIT", "position": "WR", "adp": 434.3, "tier": 8},
            {"rank": 435, "name": "Alex Erickson", "team": "CAR", "position": "WR", "adp": 435.1, "tier": 8},
            {"rank": 436, "name": "River Cracraft", "team": "MIA", "position": "WR", "adp": 436.2, "tier": 8},
            {"rank": 437, "name": "Marcus Johnson", "team": "SF", "position": "WR", "adp": 437.3, "tier": 8},
            {"rank": 438, "name": "Keeelan Doss", "team": "LV", "position": "WR", "adp": 438.1, "tier": 8},
            {"rank": 439, "name": "Devin Gray", "team": "ATL", "position": "WR", "adp": 439.2, "tier": 8},
            {"rank": 440, "name": "Kyle Phillips", "team": "TEN", "position": "WR", "adp": 440.3, "tier": 8},
            {"rank": 441, "name": "Noah Fant", "team": "SEA", "position": "TE", "adp": 441.1, "tier": 8},
            {"rank": 442, "name": "Albert Okwuegbunam", "team": "DEN", "position": "TE", "adp": 442.2, "tier": 8},
            {"rank": 443, "name": "Logan Thomas", "team": "WAS", "position": "TE", "adp": 443.3, "tier": 8},
            {"rank": 444, "name": "Robert Tonyan", "team": "CHI", "position": "TE", "adp": 444.1, "tier": 8},
            {"rank": 445, "name": "Brevin Jordan", "team": "HOU", "position": "TE", "adp": 445.2, "tier": 8},
            {"rank": 446, "name": "Tyler Kroft", "team": "SF", "position": "TE", "adp": 446.3, "tier": 8},
            {"rank": 447, "name": "Mo Alie-Cox", "team": "IND", "position": "TE", "adp": 447.1, "tier": 8},
            {"rank": 448, "name": "Jimmy Graham", "team": "NO", "position": "TE", "adp": 448.2, "tier": 8},
            {"rank": 449, "name": "Zach Ertz", "team": "WAS", "position": "TE", "adp": 449.3, "tier": 8},
            {"rank": 450, "name": "Cameron Brate", "team": "TB", "position": "TE", "adp": 450.1, "tier": 8},
            {"rank": 451, "name": "Gerald Everett", "team": "CHI", "position": "TE", "adp": 451.2, "tier": 8},
            {"rank": 452, "name": "Foster Moreau", "team": "NO", "position": "TE", "adp": 452.3, "tier": 8},
            {"rank": 453, "name": "Pharaoh Brown", "team": "SEA", "position": "TE", "adp": 453.1, "tier": 8},
            {"rank": 454, "name": "Jeremy Ruckert", "team": "NYJ", "position": "TE", "adp": 454.2, "tier": 8},
            {"rank": 455, "name": "Johnny Mundt", "team": "MIN", "position": "TE", "adp": 455.3, "tier": 8},
            {"rank": 456, "name": "Harrison Bryant", "team": "LV", "position": "TE", "adp": 456.1, "tier": 8},
            {"rank": 457, "name": "Jordan Akins", "team": "CLE", "position": "TE", "adp": 457.2, "tier": 8},
            {"rank": 458, "name": "C.J. Uzomah", "team": "NYJ", "position": "TE", "adp": 458.3, "tier": 8},
            {"rank": 459, "name": "Marcedes Lewis", "team": "CHI", "position": "TE", "adp": 459.1, "tier": 8},
            {"rank": 460, "name": "Jack Stoll", "team": "PHI", "position": "TE", "adp": 460.2, "tier": 8},
            {"rank": 461, "name": "Nick Vannett", "team": "NO", "position": "TE", "adp": 461.3, "tier": 8},
            {"rank": 462, "name": "Tyler Higbee", "team": "LAR", "position": "TE", "adp": 462.1, "tier": 8},
            {"rank": 463, "name": "Ian Thomas", "team": "CAR", "position": "TE", "adp": 463.2, "tier": 8},
            {"rank": 464, "name": "Ryan Griffin", "team": "CHI", "position": "TE", "adp": 464.3, "tier": 8},
            {"rank": 465, "name": "Jesse James", "team": "LV", "position": "TE", "adp": 465.1, "tier": 8},
            {"rank": 466, "name": "Deon Yelder", "team": "LV", "position": "TE", "adp": 466.2, "tier": 8},
            {"rank": 467, "name": "Dan Arnold", "team": "JAX", "position": "TE", "adp": 467.3, "tier": 8},
            {"rank": 468, "name": "James O'Shaughnessy", "team": "JAX", "position": "TE", "adp": 468.1, "tier": 8},
            {"rank": 469, "name": "Eric Saubert", "team": "DEN", "position": "TE", "adp": 469.2, "tier": 8},
            {"rank": 470, "name": "Anthony Firkser", "team": "ATL", "position": "TE", "adp": 470.3, "tier": 8},
            {"rank": 471, "name": "Ross Dwelley", "team": "SF", "position": "TE", "adp": 471.1, "tier": 8},
            {"rank": 472, "name": "Adam Shaheen", "team": "HOU", "position": "TE", "adp": 472.2, "tier": 8},
            {"rank": 473, "name": "Matt Orzech", "team": "BAL", "position": "TE", "adp": 473.3, "tier": 8},
            {"rank": 474, "name": "David Wells", "team": "TB", "position": "TE", "adp": 474.1, "tier": 8},
            {"rank": 475, "name": "Josiah Deguara", "team": "GB", "position": "TE", "adp": 475.2, "tier": 8},
            {"rank": 476, "name": "John FitzPatrick", "team": "ATL", "position": "TE", "adp": 476.3, "tier": 8},
            {"rank": 477, "name": "Kendall Blanton", "team": "LAR", "position": "TE", "adp": 477.1, "tier": 8},
            {"rank": 478, "name": "Trevon Wesco", "team": "NYJ", "position": "TE", "adp": 478.2, "tier": 8},
            {"rank": 479, "name": "Johnny Stanton", "team": "LV", "position": "TE", "adp": 479.3, "tier": 8},
            {"rank": 480, "name": "Thaddeus Moss", "team": "CIN", "position": "TE", "adp": 480.1, "tier": 8},
            {"rank": 481, "name": "Cody Thompson", "team": "TB", "position": "WR", "adp": 481.2, "tier": 8},
            {"rank": 482, "name": "Chad Beebe", "team": "HOU", "position": "WR", "adp": 482.3, "tier": 8},
            {"rank": 483, "name": "Taiwan Jones", "team": "BUF", "position": "RB", "adp": 483.1, "tier": 8},
            {"rank": 484, "name": "Tony Jones Jr.", "team": "DEN", "position": "RB", "adp": 484.2, "tier": 8},
            {"rank": 485, "name": "JaMycal Hasty", "team": "JAX", "position": "RB", "adp": 485.3, "tier": 8},
            {"rank": 486, "name": "Godwin Igwebuike", "team": "SEA", "position": "RB", "adp": 486.1, "tier": 8},
            {"rank": 487, "name": "Jordan Wilkins", "team": "IND", "position": "RB", "adp": 487.2, "tier": 8},
            {"rank": 488, "name": "Rodney Smith", "team": "CAR", "position": "RB", "adp": 488.3, "tier": 8},
            {"rank": 489, "name": "Salvon Ahmed", "team": "MIA", "position": "RB", "adp": 489.1, "tier": 8},
            {"rank": 490, "name": "Qadree Ollison", "team": "PIT", "position": "RB", "adp": 490.2, "tier": 8},
            {"rank": 491, "name": "Alex Armah", "team": "NO", "position": "RB", "adp": 491.3, "tier": 8},
            {"rank": 492, "name": "C.J. Ham", "team": "MIN", "position": "RB", "adp": 492.1, "tier": 8},
            {"rank": 493, "name": "Patrick Ricard", "team": "BAL", "position": "RB", "adp": 493.2, "tier": 8},
            {"rank": 494, "name": "Keith Smith", "team": "ATL", "position": "RB", "adp": 494.3, "tier": 8},
            {"rank": 495, "name": "Alec Ingold", "team": "MIA", "position": "RB", "adp": 495.1, "tier": 8},
            {"rank": 496, "name": "Kyle Juszczyk", "team": "SF", "position": "RB", "adp": 496.2, "tier": 8},
            {"rank": 497, "name": "Dan Vitale", "team": "NE", "position": "RB", "adp": 497.3, "tier": 8},
            {"rank": 498, "name": "Nick Bellore", "team": "SEA", "position": "RB", "adp": 498.1, "tier": 8},
            {"rank": 499, "name": "Reggie Gilliam", "team": "BUF", "position": "RB", "adp": 499.2, "tier": 8},
            {"rank": 500, "name": "Jakob Johnson", "team": "LV", "position": "RB", "adp": 500.3, "tier": 8}
        ]
    }
}

MOCK_PROJECTIONS = {
    # Top QBs
    "Josh Allen": {"passing_yards": 4200, "passing_tds": 32, "rushing_yards": 650, "rushing_tds": 8, "fantasy_points": 385.5},
    "Lamar Jackson": {"passing_yards": 3800, "passing_tds": 28, "rushing_yards": 820, "rushing_tds": 6, "fantasy_points": 378.2},
    
    # WRs including our comparison targets
    "Tee Higgins": {"receptions": 65, "receiving_yards": 980, "receiving_tds": 7, "fantasy_points": 168.5},
    "Jayden Higgins": {"receptions": 42, "receiving_yards": 650, "receiving_tds": 4, "fantasy_points": 97.5},
    "Saquon Barkley": {"rushing_yards": 1350, "rushing_tds": 12, "receptions": 55, "receiving_yards": 420, "fantasy_points": 295.5},
}


# Live FantasyPros Data Fetching System
class FantasyProsCacheManager:
    """
    Manages cached FantasyPros data with automatic refresh
    
    This system scrapes FantasyPros rankings and caches them locally
    with configurable TTL (time-to-live) for performance and reliability.
    """
    
    def __init__(self):
        self.cache_file = DATA_DIR / "cached_rankings.json"
        self.last_update_file = DATA_DIR / "last_update.txt"
        
    def is_cache_valid(self) -> bool:
        """Check if cached data is still valid (within TTL)"""
        if not self.last_update_file.exists():
            return False
            
        try:
            with open(self.last_update_file, 'r') as f:
                last_update_str = f.read().strip()
                last_update = datetime.fromisoformat(last_update_str)
                
            # Check if cache has expired
            cache_age = datetime.now() - last_update
            max_age = timedelta(hours=CACHE_DURATION_HOURS)
            
            return cache_age < max_age
        except Exception:
            return False
    
    def load_cached_data(self) -> Optional[Dict[str, Any]]:
        """Load rankings from cache file"""
        if not self.cache_file.exists():
            return None
            
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
            return None
    
    def save_cached_data(self, data: Dict[str, Any]) -> None:
        """Save rankings to cache file with timestamp"""
        try:
            # Save data
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            # Save timestamp
            with open(self.last_update_file, 'w') as f:
                f.write(datetime.now().isoformat())
                
            print(f"✅ Cached {len(data.get('players', []))} players at {datetime.now()}")
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    async def fetch_live_rankings(self, scoring_format: str = "half_ppr", 
                                league_type: str = "superflex") -> Dict[str, Any]:
        """
        Fetch live rankings from FantasyPros website
        
        This method scrapes the actual FantasyPros rankings tables
        to get the most up-to-date data for all positions.
        
        Args:
            scoring_format: 'standard', 'half_ppr', or 'ppr'
            league_type: 'standard' or 'superflex'
            
        Returns:
            Dictionary with comprehensive player rankings
        """
        print(f"🔄 Fetching live {league_type} {scoring_format} rankings from FantasyPros...")
        
        # Build URL based on format
        base_url = "https://www.fantasypros.com/nfl/rankings"
        
        # Map our formats to FantasyPros URLs
        if league_type == "superflex":
            if scoring_format == "half_ppr":
                url = f"{base_url}/sf-half-point-ppr.php"
            elif scoring_format == "ppr":
                url = f"{base_url}/sf-ppr.php" 
            else:  # standard
                url = f"{base_url}/sf.php"
        else:  # standard league
            if scoring_format == "half_ppr":
                url = f"{base_url}/half-point-ppr.php"
            elif scoring_format == "ppr":
                url = f"{base_url}/ppr.php"
            else:  # standard
                url = f"{base_url}/consensus-cheatsheets.php"
        
        try:
            # Fetch the page with SSL context for development
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}")
                    html = await response.text()
            
            # Parse rankings table
            soup = BeautifulSoup(html, 'html.parser')
            players = self._parse_rankings_table(soup, scoring_format, league_type)
            
            return {
                "last_updated": datetime.now().isoformat(),
                "format": league_type,
                "scoring": scoring_format,
                "source": "fantasypros_live",
                "url": url,
                "players": players[:POSITION_LIMITS["OVERALL"]]  # Top 500
            }
            
        except Exception as e:
            print(f"❌ Error fetching live rankings: {e}")
            print("🔄 Falling back to mock data...")
            return self._get_fallback_data(scoring_format, league_type)
    
    def _parse_rankings_table(self, soup: BeautifulSoup, scoring_format: str, 
                             league_type: str) -> List[Dict[str, Any]]:
        """
        Parse FantasyPros rankings table from HTML
        
        Extracts player name, position, team, rank, and other metadata
        from the FantasyPros rankings table structure.
        """
        players = []
        
        # Find the main rankings table - FantasyPros uses different classes
        table_selectors = [
            "table#data",
            "table.players", 
            "table[data-table='rankings']",
            ".rankings-table",
            "table.table"
        ]
        
        rankings_table = None
        for selector in table_selectors:
            rankings_table = soup.select_one(selector)
            if rankings_table:
                break
        
        if not rankings_table:
            print("⚠️  Could not find rankings table - page structure may have changed")
            return []
        
        # Parse table rows
        rows = rankings_table.find_all('tr')[1:]  # Skip header row
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                # Extract player info - structure varies by page
                rank = i + 1
                
                # Find player name (usually in a link or span)
                name_cell = cells[1] if len(cells) > 1 else cells[0]
                name_link = name_cell.find('a')
                name = name_link.text.strip() if name_link else name_cell.text.strip()
                
                # Clean up name (remove extra whitespace, notes)
                name = name.split('(')[0].strip()  # Remove injury notes like "(Q)"
                
                # Extract position and team - usually in format "RB - PHI"
                pos_team_text = ""
                for cell in cells:
                    text = cell.text.strip()
                    if ' - ' in text and len(text) < 15:  # Position format
                        pos_team_text = text
                        break
                
                if pos_team_text and ' - ' in pos_team_text:
                    position, team = pos_team_text.split(' - ', 1)
                    position = position.strip()
                    team = team.strip()
                else:
                    # Fallback: try to extract from other cells
                    position = "UNKNOWN"
                    team = "UNKNOWN"
                
                # Calculate approximate ADP (rank + some variance)
                adp = rank + (rank * 0.1)  # Slight variance from exact rank
                
                # Assign tier based on rank ranges
                if rank <= 12:
                    tier = 1
                elif rank <= 36:
                    tier = 2
                elif rank <= 60:
                    tier = 3
                elif rank <= 100:
                    tier = 4
                elif rank <= 150:
                    tier = 5
                elif rank <= 200:
                    tier = 6
                elif rank <= 300:
                    tier = 7
                else:
                    tier = 8
                
                player_data = {
                    "rank": rank,
                    "name": name,
                    "team": team,
                    "position": position,
                    "adp": round(adp, 1),
                    "tier": tier
                }
                
                players.append(player_data)
                
            except Exception as e:
                print(f"Error parsing row {i}: {e}")
                continue
        
        print(f"✅ Parsed {len(players)} players from FantasyPros")
        return players
    
    def _get_fallback_data(self, scoring_format: str, league_type: str) -> Dict[str, Any]:
        """Return mock data as fallback when live fetch fails"""
        key = f"{league_type}_{scoring_format}".lower()
        if key in MOCK_RANKINGS:
            return MOCK_RANKINGS[key]
        else:
            return MOCK_RANKINGS["superflex_half_ppr"]  # Default fallback

# Global cache manager instance
cache_manager = FantasyProsCacheManager()


@mcp.tool() if HAS_MCP else tool_decorator
def get_rankings(
    scoring_format: str = "half_ppr",
    league_type: str = "superflex",
    position: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get consensus fantasy football rankings with intelligent caching
    
    This function implements a 3-tier data strategy:
    1. First: Try cached live data (if fresh within 1 hour)
    2. Second: Fetch new live data from FantasyPros (if cache expired)
    3. Third: Fall back to mock data (if live fetch fails)
    
    Args:
        scoring_format: Scoring system - 'standard', 'half_ppr', or 'ppr'
        league_type: League format - 'standard' or 'superflex'
        position: Optional position filter - 'QB', 'RB', 'WR', 'TE', 'K', 'DST'
        limit: Maximum number of players to return (default 50, max based on position)
    
    Returns:
        Dictionary containing rankings with player details, ADP, and tiers
        Includes metadata about data source and freshness
    """
    # Check if we have valid cached data first
    if cache_manager.is_cache_valid():
        print("📍 Using cached FantasyPros data (fresh within 1 hour)")
        rankings_data = cache_manager.load_cached_data()
    else:
        print("🔄 Cache expired or missing - fetching fresh data from FantasyPros...")
        try:
            # Try to fetch live data
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            rankings_data = loop.run_until_complete(
                cache_manager.fetch_live_rankings(scoring_format, league_type)
            )
            loop.close()
            
            # Check if live fetch actually got players
            if not rankings_data.get("players"):
                print("⚠️ Live fetch returned no players - using mock data as fallback...")
                rankings_key = f"{league_type}_{scoring_format}".lower()
                if rankings_key in MOCK_RANKINGS:
                    rankings_data = MOCK_RANKINGS[rankings_key].copy()
                else:
                    rankings_data = MOCK_RANKINGS["superflex_half_ppr"].copy()
            else:
                # Cache the fresh data only if it has players
                cache_manager.save_cached_data(rankings_data)
            
        except Exception as e:
            print(f"❌ Failed to fetch live data: {e}")
            print("🔄 Using Sleeper API as fallback...")
            
            # Fall back to Sleeper rankings instead of mock data
            try:
                from agents.draft_crew import get_sleeper_rankings_fallback
                sleeper_result = get_sleeper_rankings_fallback()
                
                if not sleeper_result.startswith("ERROR:"):
                    # Parse Sleeper rankings into our format
                    rankings_data = {"players": [], "data_source": "sleeper_fallback"}
                    lines = sleeper_result.split('\n')[1:]  # Skip header
                    
                    for line in lines:
                        if ' (' in line and ') - Rank:' in line:
                            # Parse: "Player Name (POS) - Rank: X, ADP: Y, Team: Z"
                            parts = line.split(' (')
                            if len(parts) >= 2:
                                name = parts[0].strip()
                                rest = parts[1]
                                pos_end = rest.find(')')
                                if pos_end != -1:
                                    position = rest[:pos_end]
                                    # Extract rank and other info
                                    rank_part = rest[pos_end+1:]
                                    if 'Rank:' in rank_part:
                                        try:
                                            rank = int(rank_part.split('Rank: ')[1].split(',')[0])
                                            rankings_data["players"].append({
                                                "name": name,
                                                "position": position,
                                                "rank": rank,
                                                "source": "sleeper"
                                            })
                                        except (ValueError, IndexError):
                                            continue
                    
                    print(f"✅ Successfully converted {len(rankings_data['players'])} Sleeper rankings")
                else:
                    raise Exception("Sleeper fallback also failed")
                    
            except Exception as sleeper_error:
                print(f"❌ Sleeper fallback also failed: {sleeper_error}")
                print("🔄 Using mock data as last resort...")
                
                # Last resort: Fall back to mock data
                rankings_key = f"{league_type}_{scoring_format}".lower()
                if rankings_key in MOCK_RANKINGS:
                    rankings_data = MOCK_RANKINGS[rankings_key].copy()
                else:
                    rankings_data = MOCK_RANKINGS["superflex_half_ppr"].copy()
                
                rankings_data["data_source"] = "mock_fallback"
                rankings_data["cache_note"] = "Using mock data - both FantasyPros and Sleeper failed"
    
    if not rankings_data:
        return {
            "error": "No rankings data available",
            "source": "error"
        }
    
    # Get all players
    all_players = rankings_data.get("players", [])
    
    # Apply position filter if specified
    if position:
        position_upper = position.upper()
        filtered_players = [p for p in all_players if p.get("position") == position_upper]
        
        # Apply position-specific limits for depth
        if position_upper in POSITION_LIMITS:
            max_for_position = POSITION_LIMITS[position_upper]
            filtered_players = filtered_players[:max_for_position]
    else:
        filtered_players = all_players
    
    # Apply user-requested limit
    final_players = filtered_players[:limit]
    
    # Build response with metadata
    response = rankings_data.copy()
    response["players"] = final_players
    response["count"] = len(final_players)
    response["total_available"] = len(all_players)
    response["filtered_by_position"] = position.upper() if position else None
    response["position_limit_applied"] = POSITION_LIMITS.get(position.upper()) if position else None
    response["user_limit"] = limit
    
    return response


@mcp.tool() if HAS_MCP else tool_decorator
def get_projections(
    player_names: List[str],
    week: str = "season",
    scoring_format: str = "half_ppr"
) -> Dict[str, Any]:
    """
    Get fantasy projections for specific players
    
    Args:
        player_names: List of player names to get projections for
        week: Week number (1-18) or 'season' for full season projections
        scoring_format: Scoring system - 'standard', 'half_ppr', or 'ppr'
    
    Returns:
        Dictionary with player projections including stats and fantasy points
    """
    projections = {
        "week": week,
        "scoring_format": scoring_format,
        "players": {}
    }
    
    for player_name in player_names:
        if player_name in MOCK_PROJECTIONS:
            projections["players"][player_name] = MOCK_PROJECTIONS[player_name]
        else:
            projections["players"][player_name] = {
                "error": "Player not found in projections database",
                "fantasy_points": 0
            }
    
    return projections


@mcp.tool() if HAS_MCP else tool_decorator
def get_adp_analysis(
    current_pick: int,
    available_players: List[str],
    scoring_format: str = "half_ppr"
) -> Dict[str, Any]:
    """
    Analyze available players based on ADP to find value picks
    
    Args:
        current_pick: Current draft pick number
        available_players: List of available player names
        scoring_format: Scoring format for ADP data
    
    Returns:
        Dictionary with value picks, reaches, and recommendations
    """
    # Get rankings data to access ADP
    rankings_key = f"superflex_{scoring_format}"
    if rankings_key not in MOCK_RANKINGS:
        return {"error": "ADP data not available for this format"}
    
    all_players = {p["name"]: p for p in MOCK_RANKINGS[rankings_key]["players"]}
    
    value_picks = []
    on_schedule = []
    reaches = []
    
    for player_name in available_players:
        if player_name in all_players:
            player = all_players[player_name]
            adp = player["adp"]
            
            # Calculate value differential
            value_diff = current_pick - (adp * 12)  # Convert ADP to pick number (12-team league)
            
            if value_diff > 15:
                value_picks.append({
                    "name": player_name,
                    "position": player["position"],
                    "adp": adp,
                    "value_differential": value_diff,
                    "recommendation": "STRONG VALUE"
                })
            elif value_diff > 5:
                on_schedule.append({
                    "name": player_name,
                    "position": player["position"],
                    "adp": adp,
                    "value_differential": value_diff,
                    "recommendation": "FAIR VALUE"
                })
            else:
                reaches.append({
                    "name": player_name,
                    "position": player["position"],
                    "adp": adp,
                    "value_differential": value_diff,
                    "recommendation": "REACH"
                })
    
    return {
        "current_pick": current_pick,
        "analysis_time": datetime.now().isoformat(),
        "value_picks": sorted(value_picks, key=lambda x: x["value_differential"], reverse=True),
        "on_schedule": on_schedule,
        "reaches": reaches,
        "best_value": value_picks[0] if value_picks else None
    }


@mcp.tool() if HAS_MCP else tool_decorator
def get_tier_breaks(
    position: str,
    scoring_format: str = "half_ppr",
    league_type: str = "superflex"
) -> Dict[str, Any]:
    """
    Get tier breakdowns for a specific position to identify value cliffs
    
    Args:
        position: Position to analyze - 'QB', 'RB', 'WR', 'TE'
        scoring_format: Scoring system
        league_type: League format
    
    Returns:
        Dictionary with tier information and players in each tier
    """
    rankings_key = f"{league_type}_{scoring_format}"
    if rankings_key not in MOCK_RANKINGS:
        return {"error": "Rankings not available for this format"}
    
    # Filter players by position
    position_players = [
        p for p in MOCK_RANKINGS[rankings_key]["players"] 
        if p["position"] == position.upper()
    ]
    
    # Group by tiers
    tiers = {}
    for player in position_players:
        tier = player.get("tier", 99)
        if tier not in tiers:
            tiers[tier] = []
        tiers[tier].append(player)
    
    # Convert to sorted list
    tier_list = []
    for tier_num in sorted(tiers.keys()):
        tier_list.append({
            "tier": tier_num,
            "players": tiers[tier_num],
            "count": len(tiers[tier_num]),
            "avg_adp": sum(p["adp"] for p in tiers[tier_num]) / len(tiers[tier_num])
        })
    
    return {
        "position": position.upper(),
        "scoring_format": scoring_format,
        "league_type": league_type,
        "tiers": tier_list,
        "recommendation": f"Try to get at least one player from Tier {tier_list[0]['tier']} if possible"
    }


@mcp.tool() if HAS_MCP else tool_decorator
def get_superflex_strategy() -> Dict[str, Any]:
    """
    Get strategic advice specifically for SUPERFLEX leagues
    
    Returns:
        Dictionary with SUPERFLEX-specific draft strategy and tips
    """
    return {
        "strategy": "SUPERFLEX Draft Strategy",
        "key_points": [
            "QBs are significantly more valuable - treat top QBs like first-round picks",
            "Aim to draft 2-3 starting QBs by round 6-7",
            "Elite QBs (Allen, Jackson, Mahomes) should go in rounds 1-2",
            "Don't wait too long on QB2 - the dropoff is steep",
            "Consider drafting a QB3 as insurance/bye week fill-in"
        ],
        "position_targets": {
            "QB": "2-3 QBs by round 7",
            "RB": "2-3 RBs by round 5", 
            "WR": "2-3 WRs by round 6",
            "TE": "1 TE by round 8 unless elite option available"
        },
        "round_by_round": {
            "1-2": "Elite RB or top 3 QB",
            "3-4": "Best available RB/WR or QB if you don't have one",
            "5-6": "Fill out RB/WR depth or secure QB2",
            "7-8": "Best player available, consider TE",
            "9+": "Depth, upside picks, QB3 if needed"
        }
    }


if __name__ == "__main__":
    # Run the MCP server
    print("🏈 Starting FantasyPros MCP Server...")
    print("Available tools:")
    print("  - get_rankings: Get consensus rankings with ADP and tiers")
    print("  - get_projections: Get player projections")
    print("  - get_adp_analysis: Find value picks based on ADP")
    print("  - get_tier_breaks: Analyze position tiers")
    print("  - get_superflex_strategy: Get SUPERFLEX-specific advice")
    
    if HAS_MCP:
        # In production, this would be deployed to AgentCore
        # For local testing, you can use: python fantasypros_mcp.py
        mcp.run()
    else:
        print("Running in local development mode (no MCP server)")
        # Test the functions directly
        print("\n🧪 Testing functions:")
        rankings = get_rankings(limit=3)
        print(f"✅ Rankings: {len(rankings.get('players', []))} players")
        
        strategy = get_superflex_strategy()
        print(f"✅ Strategy: {len(strategy.get('key_points', []))} tips")