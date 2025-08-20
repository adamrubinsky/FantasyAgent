"""
Yahoo Manual Draft Tracker
Fallback solution for tracking draft picks manually
"""

import json
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class YahooManualDraftTracker:
    """
    Manual draft tracking system for Yahoo Snake drafts
    User can input picks as they happen and get real-time recommendations
    """
    
    def __init__(self, draft_slot: int = 5, total_teams: int = 10):
        """
        Initialize manual tracker
        
        Args:
            draft_slot: User's draft position (1-10)
            total_teams: Number of teams in the league
        """
        self.draft_slot = draft_slot
        self.total_teams = total_teams
        self.current_pick = 1
        self.all_picks = []
        self.my_picks = []
        self.drafted_players = set()  # Track drafted player names
        
        # Initialize draft board
        self.draft_board = {i: [] for i in range(1, total_teams + 1)}
        
        logger.info(f"Manual tracker initialized: Slot {draft_slot} of {total_teams} teams")
    
    def record_pick(self, player_name: str, position: str = None, 
                   team_slot: int = None, pick_number: int = None) -> Dict:
        """
        Record a draft pick
        
        Args:
            player_name: Name of the player drafted
            position: Player's position (optional)
            team_slot: Which team made the pick (optional, will calculate)
            pick_number: Overall pick number (optional, will use current)
        """
        
        # Use current pick if not specified
        if pick_number is None:
            pick_number = self.current_pick
        
        # Calculate team slot if not specified (snake draft logic)
        if team_slot is None:
            team_slot = self._calculate_team_slot(pick_number)
        
        # Create pick record
        pick = {
            'pick': pick_number,
            'round': self._get_round(pick_number),
            'team': team_slot,
            'player': player_name,
            'position': position,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add to tracking
        self.all_picks.append(pick)
        self.draft_board[team_slot].append(pick)
        self.drafted_players.add(player_name.lower())
        
        # Track user's picks
        if team_slot == self.draft_slot:
            self.my_picks.append(pick)
            logger.info(f"Your pick #{pick_number}: {player_name}")
        
        # Increment current pick
        self.current_pick = pick_number + 1
        
        logger.info(f"Recorded: Pick #{pick_number} - {player_name} to Team {team_slot}")
        
        return pick
    
    def _calculate_team_slot(self, pick_number: int) -> int:
        """Calculate which team is picking based on snake draft logic"""
        round_num = self._get_round(pick_number)
        
        if round_num % 2 == 1:  # Odd round (1, 3, 5, etc.)
            # Normal order: 1, 2, 3, ..., 10
            return ((pick_number - 1) % self.total_teams) + 1
        else:  # Even round (2, 4, 6, etc.)
            # Reverse order: 10, 9, 8, ..., 1
            return self.total_teams - ((pick_number - 1) % self.total_teams)
    
    def _get_round(self, pick_number: int) -> int:
        """Get round number from pick number"""
        return ((pick_number - 1) // self.total_teams) + 1
    
    def is_my_turn(self) -> bool:
        """Check if it's user's turn to pick"""
        next_team = self._calculate_team_slot(self.current_pick)
        return next_team == self.draft_slot
    
    def get_next_pick(self) -> int:
        """Get user's next pick number"""
        current_round = self._get_round(self.current_pick)
        
        # Find next pick for user's slot
        for future_pick in range(self.current_pick, self.current_pick + (2 * self.total_teams)):
            if self._calculate_team_slot(future_pick) == self.draft_slot:
                return future_pick
        
        return -1  # Draft over
    
    def get_draft_status(self) -> Dict:
        """Get current draft status for UI"""
        
        current_round = self._get_round(self.current_pick)
        my_turn = self.is_my_turn()
        next_pick = self.get_next_pick()
        picks_until_mine = next_pick - self.current_pick if next_pick > 0 else None
        
        return {
            'status': 'success',
            'mode': 'manual',
            'draftStatus': {
                'currentPick': self.current_pick,
                'round': current_round,
                'totalPicks': self.total_teams * 16,  # 16 rounds typical
                'teams': self.total_teams,
                'myTurn': my_turn,
                'userSlot': self.draft_slot,
                'nextUserPick': next_pick,
                'picksUntilMine': picks_until_mine
            },
            'myRoster': self.my_picks,
            'recentPicks': self.all_picks[-5:] if self.all_picks else [],
            'draftedPlayers': list(self.drafted_players),
            'message': 'Manual tracking mode - Enter picks as they happen'
        }
    
    def is_player_drafted(self, player_name: str) -> bool:
        """Check if a player has been drafted"""
        return player_name.lower() in self.drafted_players
    
    def get_my_roster(self) -> Dict[str, List]:
        """Get user's roster organized by position"""
        roster = {
            'QB': [],
            'RB': [],
            'WR': [],
            'TE': [],
            'FLEX': [],
            'DST': [],
            'K': [],
            'BENCH': []
        }
        
        for pick in self.my_picks:
            pos = pick.get('position', 'BENCH')
            if pos in roster:
                roster[pos].append(pick['player'])
            else:
                roster['BENCH'].append(pick['player'])
        
        return roster
    
    def undo_last_pick(self) -> bool:
        """Undo the last recorded pick"""
        if not self.all_picks:
            return False
        
        # Remove last pick
        last_pick = self.all_picks.pop()
        
        # Remove from draft board
        team_slot = last_pick['team']
        if self.draft_board[team_slot]:
            self.draft_board[team_slot].pop()
        
        # Remove from drafted players
        self.drafted_players.discard(last_pick['player'].lower())
        
        # Remove from my picks if it was mine
        if team_slot == self.draft_slot and self.my_picks:
            self.my_picks.pop()
        
        # Decrement current pick
        self.current_pick -= 1
        
        logger.info(f"Undid pick: {last_pick['player']}")
        return True
    
    def save_draft(self, filename: str = 'draft_tracker.json'):
        """Save draft state to file"""
        state = {
            'draft_slot': self.draft_slot,
            'total_teams': self.total_teams,
            'current_pick': self.current_pick,
            'all_picks': self.all_picks,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Draft saved to {filename}")
    
    def load_draft(self, filename: str = 'draft_tracker.json'):
        """Load draft state from file"""
        try:
            with open(filename, 'r') as f:
                state = json.load(f)
            
            self.draft_slot = state['draft_slot']
            self.total_teams = state['total_teams']
            self.current_pick = state['current_pick']
            self.all_picks = state['all_picks']
            
            # Rebuild derived data
            self.my_picks = [p for p in self.all_picks if p['team'] == self.draft_slot]
            self.drafted_players = {p['player'].lower() for p in self.all_picks}
            
            # Rebuild draft board
            self.draft_board = {i: [] for i in range(1, self.total_teams + 1)}
            for pick in self.all_picks:
                self.draft_board[pick['team']].append(pick)
            
            logger.info(f"Draft loaded from {filename}")
            return True
            
        except FileNotFoundError:
            logger.warning(f"No saved draft found at {filename}")
            return False


# Quick test
if __name__ == "__main__":
    # Initialize tracker for slot 5 in 10-team league
    tracker = YahooManualDraftTracker(draft_slot=5, total_teams=10)
    
    # Simulate some picks
    print("\n=== MANUAL DRAFT TRACKER TEST ===\n")
    
    # Round 1 picks
    tracker.record_pick("Christian McCaffrey", "RB")
    tracker.record_pick("Tyreek Hill", "WR")
    tracker.record_pick("CeeDee Lamb", "WR") 
    tracker.record_pick("Ja'Marr Chase", "WR")
    tracker.record_pick("Justin Jefferson", "WR")  # User's pick
    
    # Check status
    status = tracker.get_draft_status()
    print(f"\nCurrent Pick: {status['draftStatus']['currentPick']}")
    print(f"Round: {status['draftStatus']['round']}")
    print(f"My Turn: {status['draftStatus']['myTurn']}")
    print(f"My Picks: {[p['player'] for p in tracker.my_picks]}")
    print(f"Next User Pick: {status['draftStatus']['nextUserPick']}")
    
    # Test is_player_drafted
    print(f"\nIs CMC drafted? {tracker.is_player_drafted('Christian McCaffrey')}")
    print(f"Is Bijan drafted? {tracker.is_player_drafted('Bijan Robinson')}")