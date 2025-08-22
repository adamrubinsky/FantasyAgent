"""
High-performance caching system for auction draft
Optimized for <3 second response times
"""

import time
import hashlib
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import asyncio
from concurrent.futures import ThreadPoolExecutor

@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    key: str
    value: Any
    timestamp: float
    hits: int = 0
    computation_time_ms: float = 0
    
    def is_fresh(self, ttl_seconds: int = 30) -> bool:
        """Check if cache entry is still fresh"""
        age = time.time() - self.timestamp
        return age < ttl_seconds
    
    def touch(self):
        """Mark entry as accessed"""
        self.hits += 1


class AuctionCache:
    """
    Multi-tier caching system for auction draft
    
    Features:
    - L1: In-memory cache for instant access
    - L2: Precomputed values for common scenarios
    - Smart eviction based on usage patterns
    - Async preloading of likely needed data
    """
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.l1_cache: Dict[str, CacheEntry] = {}
        self.l2_precomputed: Dict[str, Any] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "avg_response_ms": 0
        }
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Preload common values
        self._init_precomputed_values()
    
    def _init_precomputed_values(self):
        """Precompute common auction scenarios"""
        # Position value matrices
        self.l2_precomputed["position_values"] = {
            "RB": {
                "tier1": range(45, 65),  # Elite RB value range
                "tier2": range(25, 45),
                "tier3": range(10, 25),
                "tier4": range(3, 10),
                "tier5": range(1, 3)
            },
            "WR": {
                "tier1": range(40, 60),
                "tier2": range(22, 40),
                "tier3": range(8, 22),
                "tier4": range(3, 8),
                "tier5": range(1, 3)
            },
            "QB": {
                "tier1": range(15, 22),  # 4PT passing TD cap
                "tier2": range(8, 15),
                "tier3": range(3, 8),
                "tier4": range(1, 3)
            },
            "TE": {
                "tier1": range(25, 40),  # Elite TE premium
                "tier2": range(8, 25),
                "tier3": range(3, 8),
                "tier4": range(1, 3)
            },
            "DEF": {
                "all": range(1, 3)  # Never pay for defense
            }
        }
        
        # Strategy phase thresholds
        self.l2_precomputed["strategy_phases"] = {
            "STARS": {
                "budget_threshold": 140,  # Need 140+ for stars
                "target_positions": ["RB", "WR"],
                "min_value": 35
            },
            "VALUE": {
                "budget_threshold": 60,
                "target_positions": ["RB", "WR", "QB", "TE"],
                "min_value": 8,
                "max_value": 25
            },
            "SCRUBS": {
                "budget_threshold": 30,
                "target_positions": ["ALL"],
                "max_value": 5
            }
        }
        
        # Quick decision rules
        self.l2_precomputed["quick_rules"] = {
            "never_pay": {
                "DEF": 3,
                "K": 2,
                "QB2": 5,
                "TE2": 5
            },
            "always_pass": {
                "low_budget": 5,  # Pass if bid > budget - 5
                "position_filled": {
                    "QB": 2,
                    "DEF": 1,
                    "K": 1
                }
            }
        }
    
    def make_key(self, player_id: str, context: Dict[str, Any]) -> str:
        """Generate cache key from player and context"""
        key_parts = [
            player_id,
            str(context.get("current_bid", 0)),
            str(context.get("my_budget", 0)),
            str(context.get("roster_spots_left", 0)),
            str(context.get("picks_complete", 0))
        ]
        key_str = "_".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()[:16]
    
    def get(self, key: str, ttl: int = 30) -> Optional[Any]:
        """Get value from cache if fresh"""
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if entry.is_fresh(ttl):
                entry.touch()
                self.stats["hits"] += 1
                return entry.value
            else:
                # Stale entry - remove it
                del self.l1_cache[key]
        
        self.stats["misses"] += 1
        return None
    
    def put(self, key: str, value: Any, computation_time_ms: float = 0):
        """Store value in cache with LRU eviction"""
        # Check if we need to evict
        if len(self.l1_cache) >= self.max_size:
            self._evict_lru()
        
        # Store new entry
        self.l1_cache[key] = CacheEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            computation_time_ms=computation_time_ms
        )
    
    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self.l1_cache:
            return
        
        # Find LRU entry (oldest timestamp with fewest hits)
        lru_key = min(
            self.l1_cache.keys(),
            key=lambda k: (
                self.l1_cache[k].timestamp - self.l1_cache[k].hits * 10
            )
        )
        
        del self.l1_cache[lru_key]
        self.stats["evictions"] += 1
    
    def get_quick_decision(self, player: Dict, context: Dict) -> Optional[str]:
        """
        Get instant decision from precomputed rules
        Returns pass reason or None if should analyze
        """
        position = player.get("position")
        current_bid = context.get("current_bid", 1)
        my_budget = context.get("my_budget", 200)
        my_roster = context.get("my_roster", {})
        
        # Check never pay thresholds
        never_pay = self.l2_precomputed["quick_rules"]["never_pay"]
        if position in never_pay and current_bid > never_pay[position]:
            return f"{position} not worth more than ${never_pay[position]}"
        
        # Check budget constraint
        min_budget = self.l2_precomputed["quick_rules"]["always_pass"]["low_budget"]
        if current_bid > my_budget - min_budget:
            return "Bid exceeds safe budget threshold"
        
        # Check position filled
        position_limits = self.l2_precomputed["quick_rules"]["always_pass"]["position_filled"]
        if position in position_limits:
            current_count = len(my_roster.get(position, []))
            if current_count >= position_limits[position]:
                return f"Already have {current_count} {position}s"
        
        return None  # Should analyze
    
    def get_position_value_tier(self, position: str, value: int) -> str:
        """Get value tier for position"""
        if position not in self.l2_precomputed["position_values"]:
            return "tier5"
        
        pos_values = self.l2_precomputed["position_values"][position]
        
        if position == "DEF":
            return "all"
        
        for tier in ["tier1", "tier2", "tier3", "tier4", "tier5"]:
            if tier in pos_values:
                tier_range = pos_values[tier]
                if value >= tier_range.start and value < tier_range.stop:
                    return tier
        
        return "tier5"
    
    def get_strategy_phase(self, context: Dict) -> str:
        """Determine current strategy phase"""
        my_budget = context.get("my_budget", 200)
        stars_acquired = context.get("stars_acquired", 0)
        
        phases = self.l2_precomputed["strategy_phases"]
        
        if stars_acquired < 3 and my_budget >= phases["STARS"]["budget_threshold"]:
            return "STARS"
        elif my_budget >= phases["VALUE"]["budget_threshold"]:
            return "VALUE"
        else:
            return "SCRUBS"
    
    async def preload_likely_players(self, players: List[Dict], context: Dict):
        """Async preload cache for likely nominations"""
        def compute_value(player):
            # This would call the value calculator
            # For now, just estimate based on rank
            rank = player.get("rank", 200)
            if rank <= 10:
                return 50
            elif rank <= 30:
                return 25
            elif rank <= 60:
                return 12
            elif rank <= 100:
                return 5
            else:
                return 1
        
        # Preload top 10 players in background
        loop = asyncio.get_event_loop()
        tasks = []
        
        for player in players[:10]:
            key = self.make_key(
                player.get("id", "unknown"),
                context
            )
            if key not in self.l1_cache:
                tasks.append(
                    loop.run_in_executor(
                        self.executor,
                        compute_value,
                        player
                    )
                )
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "hit_rate": f"{hit_rate:.1%}",
            "total_hits": self.stats["hits"],
            "total_misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "cache_size": len(self.l1_cache),
            "avg_computation_ms": sum(
                e.computation_time_ms for e in self.l1_cache.values()
            ) / len(self.l1_cache) if self.l1_cache else 0
        }
    
    def clear(self):
        """Clear all cache entries"""
        self.l1_cache.clear()
        self.stats["evictions"] += len(self.l1_cache)


# Global cache instance
_auction_cache = None

def get_auction_cache() -> AuctionCache:
    """Get or create global auction cache"""
    global _auction_cache
    if _auction_cache is None:
        _auction_cache = AuctionCache()
    return _auction_cache