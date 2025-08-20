"""
Manual Draft Tracker for when APIs fail
Tracks picks manually and provides real data to agents
"""

import json
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ManualDraftTracker:
    """
    Singleton tracker for manual draft management
    Used when Yahoo API returns 403 or other errors
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if not self.initialized:
            self.drafts = {}  # platform -> draft data
            self.initialized = True
    
    def init_draft(self, platform: str, draft_slot: int, total_teams: int = 10):
        """Initialize a draft for manual tracking"""
        self.drafts[platform] = {
            "draft_slot": draft_slot,
            "total_teams": total_teams,
            "current_pick": 1,
            "all_picks": [],
            "drafted_players": set(),
            "my_roster": [],
            "platform": platform
        }
        logger.info(f"Initialized manual tracking for {platform}, slot {draft_slot}")
    
    def record_pick(self, platform: str, player_name: str, position: str = None, 
                   team_slot: int = None, pick_number: int = None):
        """Record a pick manually"""
        if platform not in self.drafts:
            logger.error(f"No draft initialized for {platform}")
            return None
        
        draft = self.drafts[platform]
        
        # Use current pick if not specified
        if pick_number is None:
            pick_number = draft["current_pick"]
        
        # Calculate team slot if not specified (snake draft)
        if team_slot is None:
            round_num = ((pick_number - 1) // draft["total_teams"]) + 1
            if round_num % 2 == 1:  # Odd round
                team_slot = ((pick_number - 1) % draft["total_teams"]) + 1
            else:  # Even round
                team_slot = draft["total_teams"] - ((pick_number - 1) % draft["total_teams"])
        
        # Create pick record
        pick = {
            "pick": pick_number,
            "round": ((pick_number - 1) // draft["total_teams"]) + 1,
            "team": team_slot,
            "player": player_name,
            "position": position,
            "timestamp": datetime.now().isoformat()
        }
        
        # Update tracking
        draft["all_picks"].append(pick)
        draft["drafted_players"].add(player_name.lower())
        
        # Track user's picks
        if team_slot == draft["draft_slot"]:
            draft["my_roster"].append(pick)
            logger.info(f"YOUR PICK: {player_name} at pick #{pick_number}")
        
        # Update current pick
        draft["current_pick"] = pick_number + 1
        
        logger.info(f"Recorded: Pick #{pick_number} - {player_name} ({position}) to Team {team_slot}")
        return pick
    
    def get_draft_status(self, platform: str) -> Dict:
        """Get current draft status with all the data agents need"""
        if platform not in self.drafts:
            return {"status": "error", "message": "No draft initialized"}
        
        draft = self.drafts[platform]
        current_pick = draft["current_pick"]
        current_round = ((current_pick - 1) // draft["total_teams"]) + 1
        
        # Check if it's user's turn (snake draft logic)
        my_turn = False
        if current_round % 2 == 1:  # Odd round
            current_drafter = ((current_pick - 1) % draft["total_teams"]) + 1
        else:  # Even round
            current_drafter = draft["total_teams"] - ((current_pick - 1) % draft["total_teams"])
        
        my_turn = (current_drafter == draft["draft_slot"])
        
        return {
            "status": "success",
            "mode": "manual",
            "draftStatus": {
                "currentPick": current_pick,
                "round": current_round,
                "totalPicks": draft["total_teams"] * 16,
                "teams": draft["total_teams"],
                "myTurn": my_turn,
                "userSlot": draft["draft_slot"]
            },
            "allPicks": draft["all_picks"],
            "myRoster": draft["my_roster"],
            "draftedPlayers": list(draft["drafted_players"]),
            "recentPicks": draft["all_picks"][-5:] if draft["all_picks"] else [],
            "message": "Manual tracking active - API failed"
        }
    
    def is_player_drafted(self, platform: str, player_name: str) -> bool:
        """Check if a player has been drafted"""
        if platform not in self.drafts:
            return False
        return player_name.lower() in self.drafts[platform]["drafted_players"]
    
    def get_my_roster(self, platform: str) -> List[Dict]:
        """Get user's current roster"""
        if platform not in self.drafts:
            return []
        return self.drafts[platform]["my_roster"]
    
    def get_drafted_players(self, platform: str) -> List[str]:
        """Get all drafted players"""
        if platform not in self.drafts:
            return []
        return list(self.drafts[platform]["drafted_players"])
    
    def undo_last_pick(self, platform: str) -> bool:
        """Undo the last pick"""
        if platform not in self.drafts:
            return False
        
        draft = self.drafts[platform]
        if not draft["all_picks"]:
            return False
        
        # Remove last pick
        last_pick = draft["all_picks"].pop()
        draft["drafted_players"].discard(last_pick["player"].lower())
        
        # Remove from my roster if it was mine
        if last_pick["team"] == draft["draft_slot"] and draft["my_roster"]:
            if draft["my_roster"][-1]["pick"] == last_pick["pick"]:
                draft["my_roster"].pop()
        
        # Decrement current pick
        draft["current_pick"] -= 1
        
        logger.info(f"Undid pick: {last_pick['player']}")
        return True
    
    def bulk_import_picks(self, platform: str, picks_text: str):
        """Import multiple picks from text (for catching up)"""
        if platform not in self.drafts:
            return {"status": "error", "message": "No draft initialized"}
        
        lines = picks_text.strip().split('\n')
        imported = 0
        
        for line in lines:
            # Try to parse: "1. Christian McCaffrey RB"
            parts = line.strip().split()
            if len(parts) >= 2:
                # Extract player name and position
                if parts[0].endswith('.'):
                    # Format: "1. Player Name POS"
                    player_name = ' '.join(parts[1:-1]) if len(parts) > 2 else parts[1]
                    position = parts[-1] if len(parts) > 2 else None
                else:
                    # Format: "Player Name POS"
                    player_name = ' '.join(parts[:-1]) if len(parts) > 1 else parts[0]
                    position = parts[-1] if len(parts) > 1 else None
                
                # Only record if not already drafted
                if not self.is_player_drafted(platform, player_name):
                    self.record_pick(platform, player_name, position)
                    imported += 1
        
        return {"status": "success", "imported": imported}


# Global instance
manual_tracker = ManualDraftTracker()