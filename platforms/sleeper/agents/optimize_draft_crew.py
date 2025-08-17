#!/usr/bin/env python3
"""
Integration module to add advanced optimization to draft_crew.py
This can be imported and called from the main system
"""

from typing import Dict, List, Any, Optional
import json

def enhance_draft_context(session_context: Dict, available_players: List[Dict], 
                         rankings_data: str) -> str:
    """
    Enhance draft context with advanced metrics for AI agents
    
    Args:
        session_context: Current session context from draft_crew
        available_players: List of available players
        rankings_data: Raw rankings text data
        
    Returns:
        Enhanced context string for AI agents
    """
    current_pick = session_context.get('current_pick', 1)
    user_roster = session_context.get('user_roster', [])
    draft_picks = session_context.get('draft_picks', [])
    
    # Calculate round number
    round_num = ((current_pick - 1) // 12) + 1
    
    # Parse rankings to get ADPs
    player_adps = _parse_adps_from_rankings(rankings_data)
    
    # Find value picks (falling 10+ spots)
    value_picks = []
    for player in available_players[:30]:
        player_name = player.get('name', '')
        if player_name in player_adps:
            adp = player_adps[player_name]
            if current_pick - adp >= 10:
                value_picks.append(f"{player_name} (ADP: {adp}, falling {current_pick - adp} spots)")
    
    # Detect positional runs in last 6 picks
    recent_picks = draft_picks[-6:] if len(draft_picks) >= 6 else draft_picks
    position_counts = {}
    for pick in recent_picks:
        pos = pick.get('metadata', {}).get('position', '')
        if pos:
            position_counts[pos] = position_counts.get(pos, 0) + 1
    
    run_detected = None
    for pos, count in position_counts.items():
        if count >= 3:
            run_detected = pos
            break
    
    # Check for stacking opportunities
    stack_opportunities = []
    roster_qbs = [p for p in user_roster if p.get('metadata', {}).get('position') == 'QB']
    for qb in roster_qbs:
        qb_team = qb.get('metadata', {}).get('team', '')
        qb_name = f"{qb.get('metadata', {}).get('first_name', '')} {qb.get('metadata', {}).get('last_name', '')}"
        
        # Find available teammates
        for player in available_players[:20]:
            if player.get('team') == qb_team and any(pos in ['WR', 'TE'] for pos in player.get('positions', [])):
                stack_opportunities.append(f"{player.get('name')} stacks with your QB {qb_name}")
    
    # Build enhanced context
    enhanced_context = f"""
ROUND {round_num}, PICK #{current_pick} CONTEXT:

🎯 SUPERFLEX DECISION TREE:
{_get_round_strategy(round_num, user_roster)}

📊 VALUE DETECTION:
{f"FALLING PLAYERS: {', '.join(value_picks[:3])}" if value_picks else "No significant values detected"}

🏃 POSITIONAL RUN:
{f"RUN DETECTED: {run_detected} run happening (fade it for value)" if run_detected else "No runs detected"}

🔗 STACKING OPPORTUNITIES:
{chr(10).join(stack_opportunities[:3]) if stack_opportunities else "No stacking opportunities"}

⚡ TIER BREAKS:
{_detect_tier_breaks(available_players, player_adps)}

🎰 KEEPER VALUE (Rounds 8+):
{_get_keeper_targets(round_num, available_players) if round_num >= 8 else "Not applicable yet"}

📋 YOUR ROSTER NEEDS:
{_get_roster_needs(user_roster, round_num)}
"""
    
    return enhanced_context

def _get_round_strategy(round_num: int, user_roster: List[Dict]) -> str:
    """Get SUPERFLEX-specific round strategy"""
    qb_count = sum(1 for p in user_roster if p.get('metadata', {}).get('position') == 'QB')
    
    strategies = {
        1: "MUST DRAFT: Top 4 QB (Allen/Hurts/Lamar/Mahomes) if available, else elite RB/WR",
        2: f"{'MUST GET QB (Tier 1-2)' if qb_count == 0 else 'Elite QB or top RB/WR'}",
        3: f"{'MUST SECURE QB2' if qb_count < 2 else 'Best RB/WR by tier'}",
        4: f"{'CRITICAL: Get ANY QB (reach if needed)' if qb_count < 2 else 'Bell-cow RB or target-hog WR'}",
        5: "High-upside RB/WR, consider QB3 if injury-prone starters",
        6: "Continue RB/WR depth, QB3 only for value",
        7: "RB/WR depth, top-8 TE if available",
        8: "Depth and upside picks",
        9: "Last chance for starter-quality players",
        10: "Handcuffs and breakout candidates",
        11: "High-upside rookies and backups",
        12: "Keeper targets and lottery tickets",
        13: "Final skill position depth",
        14: "Last upside swings before DST/K",
        15: "DST with easy Weeks 1-3 schedule",
        16: "Kicker in high-scoring offense"
    }
    
    return strategies.get(round_num, "Best player available")

def _parse_adps_from_rankings(rankings_data: str) -> Dict[str, float]:
    """Parse ADPs from rankings text"""
    adps = {}
    lines = rankings_data.split('\n')
    
    for line in lines:
        if 'ADP:' in line:
            # Extract name and ADP from line like "Player Name (POS) - Rank: X, ADP: Y"
            try:
                name_part = line.split(' (')[0].strip()
                adp_part = line.split('ADP:')[1].split(',')[0].strip()
                adps[name_part] = float(adp_part)
            except:
                continue
                
    return adps

def _detect_tier_breaks(available_players: List[Dict], player_adps: Dict) -> str:
    """Detect tier breaks in available players"""
    # Group by position and check for gaps
    tier_breaks = []
    
    positions = ['QB', 'RB', 'WR', 'TE']
    for pos in positions:
        pos_players = [p for p in available_players[:20] 
                      if pos in p.get('positions', [])]
        
        if len(pos_players) >= 2:
            # Check ADP gap between first and second
            first = pos_players[0].get('name', '')
            second = pos_players[1].get('name', '')
            
            if first in player_adps and second in player_adps:
                gap = player_adps[second] - player_adps[first]
                if gap >= 15:  # Significant tier gap
                    tier_breaks.append(f"{first} is last {pos} before tier drop")
    
    return ', '.join(tier_breaks[:2]) if tier_breaks else "No immediate tier breaks"

def _get_keeper_targets(round_num: int, available_players: List[Dict]) -> str:
    """Identify keeper value targets in late rounds"""
    if round_num < 8:
        return ""
        
    keeper_targets = []
    
    for player in available_players[:15]:
        # Look for rookies and young players
        player_name = player.get('name', '')
        
        # Simple heuristic - would need real data
        if any(keyword in player_name.lower() for keyword in ['jr', 'iii', 'ii']):
            keeper_targets.append(f"{player_name} (potential keeper)")
            
    return ', '.join(keeper_targets[:3]) if keeper_targets else "No obvious keeper values"

def _get_roster_needs(user_roster: List[Dict], round_num: int) -> str:
    """Analyze roster needs based on SUPERFLEX requirements"""
    position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
    
    for player in user_roster:
        pos = player.get('metadata', {}).get('position', '')
        if pos in position_counts:
            position_counts[pos] += 1
    
    needs = []
    
    # QB needs (SUPERFLEX priority)
    if position_counts['QB'] == 0:
        needs.append("🚨 CRITICAL: Need QB immediately")
    elif position_counts['QB'] == 1:
        needs.append("⚠️ HIGH: Need QB2 for SUPERFLEX")
    elif position_counts['QB'] == 2:
        needs.append("✓ QB depth (QB3) valuable but not urgent")
        
    # RB needs
    if position_counts['RB'] < 2:
        needs.append("🚨 Need starting RBs")
    elif position_counts['RB'] < 4:
        needs.append("Need RB depth")
        
    # WR needs (3 starters + flex)
    if position_counts['WR'] < 3:
        needs.append("🚨 Need starting WRs")
    elif position_counts['WR'] < 5:
        needs.append("Need WR depth for flex")
        
    # TE needs
    if position_counts['TE'] == 0 and round_num >= 5:
        needs.append("Consider TE if top-8 available")
        
    return ' | '.join(needs)

def create_optimized_prompt(question: str, enhanced_context: str, 
                           rankings_data: str, session_context: Dict) -> str:
    """
    Create an optimized prompt for AI agents with all enhancements
    
    Args:
        question: User's question
        enhanced_context: Enhanced context from above
        rankings_data: Live rankings data
        session_context: Current session context
        
    Returns:
        Optimized prompt for AI agents
    """
    current_pick = session_context.get('current_pick', 1)
    round_num = ((current_pick - 1) // 12) + 1
    
    prompt = f"""
You are an expert SUPERFLEX fantasy football advisor using advanced analytics.

USER QUESTION: {question}

{enhanced_context}

LIVE RANKINGS DATA:
{rankings_data[:2000]}  # Truncated for performance

CRITICAL SUPERFLEX RULES:
1. QBs are PREMIUM - target 2 minimum, 3 ideal
2. Never draft K/DST before Round 15
3. Exploit tier breaks aggressively
4. Fade positional runs for value
5. Rounds 10+ = ceiling over floor

For pick #{current_pick} (Round {round_num}), provide:
1. PRIMARY recommendation with ADP value analysis
2. TWO alternatives with different strategies
3. Specific reasoning using the enhanced context

Be decisive and specific. Reference actual player names and values.
"""
    
    return prompt