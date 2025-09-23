from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from enum import Enum
import uuid
import asyncio
import os
from datetime import datetime
import random
import math
import json
import logging
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
# Import SQLAlchemy components
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, and_, or_
from database import (
    get_db_session, init_database, 
    Player as DBPlayer, Category as DBCategory, 
    Match as DBMatch, Session as DBSession
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Database will use SQLite through dependency injection

# Initialize FastAPI app
app = FastAPI(title="CourtChime API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class MatchStatus(str, Enum):
    pending = "pending"
    active = "active" 
    buffer = "buffer"
    done = "done"

class MatchType(str, Enum):
    singles = "singles"
    doubles = "doubles"

class SessionPhase(str, Enum):
    idle = "idle"
    ready = "ready"  # New phase: matches generated, waiting for timer start
    play = "play"
    buffer = "buffer"
    ended = "ended"

class Format(str, Enum):
    singles = "singles"
    doubles = "doubles"
    auto = "auto"

# Data Models
class PlayerStats(BaseModel):
    wins: int = 0
    losses: int = 0
    pointDiff: int = 0

class Player(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str
    sitNextRound: bool = False
    sitCount: int = 0
    missDueToCourtLimit: int = 0
    # DUPR-style rating fields
    rating: float = 3.0  # Starting rating (typical DUPR range 2.0-8.0)
    matchesPlayed: int = 0
    wins: int = 0
    losses: int = 0
    recentForm: List[str] = []  # Last 10 results: 'W' or 'L'
    ratingHistory: List[dict] = []  # Track rating changes over time
    lastUpdated: str = Field(default_factory=lambda: datetime.now().isoformat())
    stats: PlayerStats = Field(default_factory=PlayerStats)

class PlayerCreate(BaseModel):
    name: str
    category: str

class PlayerUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    sitNextRound: Optional[bool] = None

class Category(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class Match(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    roundIndex: int
    courtIndex: int
    category: str
    teamA: List[str]  # Player IDs
    teamB: List[str]  # Player IDs
    status: MatchStatus = MatchStatus.pending
    matchType: MatchType
    scoreA: Optional[int] = None
    scoreB: Optional[int] = None

class MatchScoreUpdate(BaseModel):
    scoreA: int
    scoreB: int

class SessionConfig(BaseModel):
    numCourts: int = 4
    playSeconds: int = 720  # 12 minutes
    bufferSeconds: int = 30  # 30 seconds
    allowSingles: bool = True
    allowDoubles: bool = True
    allowCrossCategory: bool = False
    maximizeCourtUsage: bool = False  # New option for court optimization

class SessionState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    currentRound: int = 0
    phase: SessionPhase = SessionPhase.idle
    timeRemaining: int = 0
    paused: bool = False
    config: SessionConfig = Field(default_factory=SessionConfig)
    histories: Dict[str, Any] = Field(default_factory=dict)  # partners and opponents histories

# Scheduling Algorithm Functions
def shuffle_list(items: List[Any]) -> List[Any]:
    """Shuffle a list for randomization"""
    shuffled = items.copy()
    random.shuffle(shuffled)
    return shuffled

def calculate_rating_change(player_rating: float, opponent_avg_rating: float, game_result: str, 
                          score_margin: int = 0, k_factor: float = 32.0) -> float:
    """
    DUPR-style rating calculation
    
    Args:
        player_rating: Current rating of the player
        opponent_avg_rating: Average rating of opponents in the match
        game_result: 'W' for win, 'L' for loss
        score_margin: Point difference (positive for wins, negative for losses)
        k_factor: How much ratings can change (higher = more volatile)
    
    Returns:
        Rating change (can be positive or negative)
    """
    # Expected score based on rating difference (ELO-style)
    rating_diff = opponent_avg_rating - player_rating
    expected_score = 1 / (1 + 10 ** (rating_diff / 400))
    
    # Actual score (1 for win, 0 for loss)
    actual_score = 1.0 if game_result == 'W' else 0.0
    
    # Base rating change
    base_change = k_factor * (actual_score - expected_score)
    
    # Margin multiplier (DUPR considers score margins)
    # Closer games have less impact, blowout wins/losses have more impact
    margin_multiplier = 1.0
    if score_margin > 0:  # Win
        margin_multiplier = min(1.5, 1.0 + (abs(score_margin) / 20.0))  # Cap at 1.5x
    elif score_margin < 0:  # Loss  
        margin_multiplier = min(1.5, 1.0 + (abs(score_margin) / 20.0))  # Same for losses
    
    # Apply diminishing returns for very high/low ratings
    if player_rating > 6.0:  # High-rated players change less
        base_change *= 0.8
    elif player_rating < 3.0:  # Low-rated players can improve faster
        base_change *= 1.2
    
    final_change = base_change * margin_multiplier
    
    # Ensure rating stays within reasonable bounds
    new_rating = player_rating + final_change
    if new_rating > 8.0:
        final_change = 8.0 - player_rating
    elif new_rating < 2.0:
        final_change = 2.0 - player_rating
    
    return final_change

async def update_player_ratings(match: dict, teamA_score: int, teamB_score: int):
    """
    Update player ratings based on match result (DUPR-style)
    """
    try:
        # Get all players in the match
        all_player_ids = match['teamA'] + match['teamB']
        players = []
        
        for player_id in all_player_ids:
            player = await db.players.find_one({"id": player_id})
            if player:
                players.append(player)
        
        if len(players) != len(all_player_ids):
            return  # Some players not found
        
        # Split into teams
        teamA_players = [p for p in players if p['id'] in match['teamA']]
        teamB_players = [p for p in players if p['id'] in match['teamB']]
        
        # Calculate average ratings for each team
        teamA_avg = sum(p['rating'] for p in teamA_players) / len(teamA_players)
        teamB_avg = sum(p['rating'] for p in teamB_players) / len(teamB_players)
        
        # Determine winner and score margin
        teamA_won = teamA_score > teamB_score
        score_margin = abs(teamA_score - teamB_score)
        
        # Update ratings for all players
        for player in teamA_players:
            result = 'W' if teamA_won else 'L'
            margin = score_margin if teamA_won else -score_margin
            rating_change = calculate_rating_change(
                player['rating'], teamB_avg, result, margin
            )
            
            new_rating = round(player['rating'] + rating_change, 2)
            new_matches = player.get('matchesPlayed', 0) + 1
            new_wins = player.get('wins', 0) + (1 if teamA_won else 0)
            new_losses = player.get('losses', 0) + (0 if teamA_won else 1)
            
            # Update recent form (last 10 games)
            recent_form = player.get('recentForm', [])
            recent_form.append(result)
            if len(recent_form) > 10:
                recent_form = recent_form[-10:]
            
            # Add to rating history
            rating_history = player.get('ratingHistory', [])
            rating_history.append({
                'date': datetime.now().isoformat(),
                'oldRating': player['rating'],
                'newRating': new_rating,
                'change': rating_change,
                'matchId': match['id'],
                'result': result
            })
            if len(rating_history) > 50:
                rating_history = rating_history[-50:]  # Keep last 50 rating changes
            
            # Update player in database
            await db.players.update_one(
                {"id": player['id']},
                {"$set": {
                    "rating": new_rating,
                    "matchesPlayed": new_matches,
                    "wins": new_wins,
                    "losses": new_losses,
                    "recentForm": recent_form,
                    "ratingHistory": rating_history,
                    "lastUpdated": datetime.now().isoformat()
                }}
            )
        
        # Update ratings for Team B
        for player in teamB_players:
            result = 'L' if teamA_won else 'W'
            margin = -score_margin if teamA_won else score_margin
            rating_change = calculate_rating_change(
                player['rating'], teamA_avg, result, margin
            )
            
            new_rating = round(player['rating'] + rating_change, 2)
            new_matches = player.get('matchesPlayed', 0) + 1
            new_wins = player.get('wins', 0) + (0 if teamA_won else 1)
            new_losses = player.get('losses', 0) + (1 if teamA_won else 0)
            
            # Update recent form
            recent_form = player.get('recentForm', [])
            recent_form.append(result)
            if len(recent_form) > 10:
                recent_form = recent_form[-10:]
            
            # Add to rating history
            rating_history = player.get('ratingHistory', [])
            rating_history.append({
                'date': datetime.now().isoformat(),
                'oldRating': player['rating'],
                'newRating': new_rating,
                'change': rating_change,
                'matchId': match['id'],
                'result': result
            })
            if len(rating_history) > 50:
                rating_history = rating_history[-50:]
            
            # Update player in database
            await db.players.update_one(
                {"id": player['id']},
                {"$set": {
                    "rating": new_rating,
                    "matchesPlayed": new_matches,
                    "wins": new_wins,
                    "losses": new_losses,
                    "recentForm": recent_form,
                    "ratingHistory": rating_history,
                    "lastUpdated": datetime.now().isoformat()
                }}
            )
            
    except Exception as e:
        print(f"Error updating player ratings: {e}")
        # Continue without failing the match score update

def calculate_partner_score(player_a: str, player_b: str, histories: Dict[str, Any]) -> int:
    """Calculate how often two players have been partners"""
    partners_history = histories.get('partners', {})
    return partners_history.get(player_a, {}).get(player_b, 0)

def calculate_opponent_score(team_a: List[str], team_b: List[str], histories: Dict[str, Any]) -> int:
    """Calculate opponent history score between two teams"""
    opponents_history = histories.get('opponents', {})
    total_score = 0
    
    for player_a in team_a:
        for player_b in team_b:
            total_score += opponents_history.get(player_a, {}).get(player_b, 0)
    
    return total_score

def update_histories(match: Match, histories: Dict[str, Any]) -> Dict[str, Any]:
    """Update partner and opponent histories based on a match"""
    if 'partners' not in histories:
        histories['partners'] = {}
    if 'opponents' not in histories:
        histories['opponents'] = {}
    
    # Update partner histories (for doubles)
    if match.matchType == MatchType.doubles:
        if len(match.teamA) == 2:
            a1, a2 = match.teamA[0], match.teamA[1]
            if a1 not in histories['partners']:
                histories['partners'][a1] = {}
            if a2 not in histories['partners']:
                histories['partners'][a2] = {}
            histories['partners'][a1][a2] = histories['partners'][a1].get(a2, 0) + 1
            histories['partners'][a2][a1] = histories['partners'][a2].get(a1, 0) + 1
        
        if len(match.teamB) == 2:
            b1, b2 = match.teamB[0], match.teamB[1]
            if b1 not in histories['partners']:
                histories['partners'][b1] = {}
            if b2 not in histories['partners']:
                histories['partners'][b2] = {}
            histories['partners'][b1][b2] = histories['partners'][b1].get(b2, 0) + 1
            histories['partners'][b2][b1] = histories['partners'][b2].get(b1, 0) + 1
    
    # Update opponent histories
    for player_a in match.teamA:
        if player_a not in histories['opponents']:
            histories['opponents'][player_a] = {}
        for player_b in match.teamB:
            if player_b not in histories['opponents']:
                histories['opponents'][player_b] = {}
            histories['opponents'][player_a][player_b] = histories['opponents'][player_a].get(player_b, 0) + 1
            histories['opponents'][player_b][player_a] = histories['opponents'][player_b].get(player_a, 0) + 1
    
    return histories

async def schedule_round(round_index: int) -> List[Match]:
    """
    Core scheduling algorithm for round-robin matchmaking
    Implements category-based fair pairing with singles/doubles/auto-mix support
    """
    # Get current session and configuration
    session = await db.session.find_one()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_obj = SessionState(**session)
    config = session_obj.config
    
    # Get all players and categories
    players_data = await db.players.find().to_list(1000)
    categories_data = await db.categories.find().to_list(1000)
    
    players = [Player(**p) for p in players_data]
    categories = [Category(**c) for c in categories_data]
    
    # Group players by category or all together based on allowCrossCategory
    players_by_category = defaultdict(list)
    
    if config.allowCrossCategory:
        # Mix all players together in one group
        all_eligible = [p for p in players if not p.sitNextRound]
        if all_eligible:
            players_by_category["Mixed"] = all_eligible
    else:
        # Group by individual categories (original behavior)
        for player in players:
            if not player.sitNextRound:  # Exclude players forced to sit
                players_by_category[player.category].append(player)
    
    # Initialize match planning
    court_plans = {}
    created_matches = []
    used_player_ids = set()
    
    # Plan matches per category
    categories_to_process = ["Mixed"] if config.allowCrossCategory else [cat.name for cat in categories]
    
    for cat_name in categories_to_process:
        eligible_players = players_by_category[cat_name]
        
        if len(eligible_players) < 2:
            # Not enough players for any match
            continue
        
        doubles_matches = 0
        singles_matches = 0
        
        # Determine match allocation based on new format system
        # Priority: Doubles first, then singles from remaining players
        if not config.allowSingles and not config.allowDoubles:
            # This should be caught by validation, but just in case
            continue
        
        count = len(eligible_players)
        
        # Base allocation logic
        if config.allowDoubles and count >= 4:
            # Priority: Create as many doubles matches as possible
            doubles_matches = count // 4
            remaining_players = count % 4
            
            # Handle remaining players with singles if allowed
            if config.allowSingles and remaining_players >= 2:
                if remaining_players == 3:
                    # 3 remaining: sit 1 lowest-sit player, make 1 singles match
                    eligible_players.sort(key=lambda p: (p.sitCount, p.missDueToCourtLimit, p.name))
                    sit_player = eligible_players.pop(0)
                    singles_matches = 1
                    count = len(eligible_players)  # Update count after sitting player
                    doubles_matches = (count - 2) // 4  # Recalculate doubles
                elif remaining_players == 2:
                    # 2 remaining: perfect for 1 singles match
                    singles_matches = 1
                # remaining_players == 1: sits out naturally
                # remaining_players == 0: all in doubles, perfect
            # If singles not allowed, remaining players sit out
            
        elif config.allowSingles and count >= 2:
            # Only singles allowed, or not enough players for doubles
            singles_matches = count // 2
            # Odd numbered player sits out naturally
        
        # Apply court optimization OVERRIDE if enabled
        if config.maximizeCourtUsage:
            # Override fairness constraints - maximize player participation
            # Recalculate to use all available players more efficiently
            if config.allowDoubles and config.allowSingles:
                # Mixed approach: maximize doubles, then singles
                max_doubles = count // 4
                remaining_after_doubles = count % 4
                max_singles = remaining_after_doubles // 2
                
                # Always override with maximum possible matches when optimization is enabled
                doubles_matches = max_doubles
                singles_matches = max_singles
            elif config.allowDoubles:
                # Doubles only - maximize doubles matches
                doubles_matches = count // 4
            elif config.allowSingles:
                # Singles only - maximize singles matches  
                singles_matches = count // 2
        
        court_plans[cat_name] = {
            'doubles': doubles_matches,
            'singles': singles_matches,
            'eligible_players': eligible_players
        }
        
        # Debug logging for optimization
        if config.maximizeCourtUsage:
            print(f"DEBUG: Category {cat_name} - {count} players -> {doubles_matches} doubles, {singles_matches} singles")
    
    # Calculate total courts needed - FIXED for optimization
    total_courts_needed = sum(plan['doubles'] + plan['singles'] for plan in court_plans.values())
    
    # CRITICAL FIX: When optimization is enabled, don't limit courts to initially planned amount
    if config.maximizeCourtUsage:
        available_courts = config.numCourts  # Use all available courts
        print(f"DEBUG: Optimization enabled - using all {available_courts} courts, planned {total_courts_needed} matches")
    else:
        available_courts = min(config.numCourts, total_courts_needed)
        print(f"DEBUG: Standard mode - limiting to {available_courts} courts for {total_courts_needed} matches")
    
    # Court Allocation Optimization: Maximize court usage if enabled
    if config.maximizeCourtUsage and total_courts_needed < config.numCourts:
        # Advanced optimization: Try to create more matches to utilize available courts
        # This uses a greedy approach to fill unused courts with additional matches
        
        additional_courts_available = config.numCourts - total_courts_needed
        
        # Instead of limiting to one match per category, allow multiple matches
        # when we have enough players and courts available
        for cat_name in list(court_plans.keys()):
            if additional_courts_available <= 0:
                break
                
            plan = court_plans[cat_name]
            eligible = plan['eligible_players']
            
            # Calculate how many players are currently used
            current_players_used = (plan['doubles'] * 4) + (plan['singles'] * 2)
            remaining_players = len(eligible) - current_players_used
            
            # Create additional doubles matches if possible
            if config.allowDoubles and remaining_players >= 4:
                additional_doubles_possible = min(remaining_players // 4, additional_courts_available)
                if additional_doubles_possible > 0:
                    plan['doubles'] += additional_doubles_possible
                    additional_courts_available -= additional_doubles_possible
                    remaining_players -= additional_doubles_possible * 4
            
            # Create additional singles matches with remaining players
            if config.allowSingles and remaining_players >= 2 and additional_courts_available > 0:
                additional_singles_possible = min(remaining_players // 2, additional_courts_available)
                if additional_singles_possible > 0:
                    plan['singles'] += additional_singles_possible
                    additional_courts_available -= additional_singles_possible
        
        # If we still have unused courts and players sitting out, try cross-category optimization
        if additional_courts_available > 0 and not config.allowCrossCategory:
            # Collect all unused players across categories
            all_unused_players = []
            for cat_name, plan in court_plans.items():
                current_players_used = (plan['doubles'] * 4) + (plan['singles'] * 2)
                unused_players = plan['eligible_players'][current_players_used:]
                all_unused_players.extend(unused_players)
            
            # Try to create mixed matches with unused players to fill courts
            if len(all_unused_players) >= 4 and config.allowDoubles and additional_courts_available > 0:
                mixed_doubles = min(len(all_unused_players) // 4, additional_courts_available)
                if mixed_doubles > 0 and "Mixed" not in court_plans:
                    court_plans["Mixed"] = {
                        'doubles': mixed_doubles,
                        'singles': 0,
                        'eligible_players': all_unused_players[:mixed_doubles * 4]
                    }
                    additional_courts_available -= mixed_doubles
            
            # Remaining players for singles matches
            remaining_mixed = len(all_unused_players) % 4
            if remaining_mixed >= 2 and config.allowSingles and additional_courts_available > 0:
                mixed_singles = min(remaining_mixed // 2, additional_courts_available)
                if mixed_singles > 0:
                    if "Mixed" in court_plans:
                        court_plans["Mixed"]['singles'] += mixed_singles
                    else:
                        court_plans["Mixed"] = {
                            'doubles': 0,
                            'singles': mixed_singles,
                            'eligible_players': all_unused_players[-mixed_singles * 2:]
                        }
        
        # Recalculate total courts needed after optimization
        total_courts_needed = sum(plan['doubles'] + plan['singles'] for plan in court_plans.values())
        # DON'T override available_courts here - keep the optimization setting from above
        print(f"DEBUG: After optimization - total_courts_needed: {total_courts_needed}, available_courts: {available_courts}")
    
    # Fair court allocation across categories (rotate by round)
    if config.allowCrossCategory:
        rotated_categories = ["Mixed"]
    else:
        sorted_categories = sorted([cat.name for cat in categories])
        rotated_categories = sorted_categories[round_index % len(sorted_categories):] + sorted_categories[:round_index % len(sorted_categories)] if sorted_categories else []
    
    allocated_courts = {}
    courts_used = 0
    
    # Allocate courts in rotated order, doubles first
    for cat_name in rotated_categories:
        if cat_name not in court_plans:
            continue
        
        allocated_courts[cat_name] = {'doubles': 0, 'singles': 0}
        plan = court_plans[cat_name]
        
        # Allocate doubles courts first
        doubles_to_allocate = min(plan['doubles'], available_courts - courts_used)
        allocated_courts[cat_name]['doubles'] = doubles_to_allocate
        courts_used += doubles_to_allocate
        
        # Debug logging for court allocation
        if config.maximizeCourtUsage:
            print(f"DEBUG: Allocating {doubles_to_allocate}/{plan['doubles']} doubles for {cat_name}, courts_used: {courts_used}/{available_courts}")
        
        if courts_used >= available_courts:
            break
    
    # Allocate remaining courts for singles
    for cat_name in rotated_categories:
        if courts_used >= available_courts:
            break
        if cat_name not in court_plans:
            continue
        
        plan = court_plans[cat_name]
        singles_to_allocate = min(plan['singles'], available_courts - courts_used)
        allocated_courts[cat_name]['singles'] = singles_to_allocate
        courts_used += singles_to_allocate
    
    # Create actual matches
    court_index = 0
    
    for cat_name in rotated_categories:
        if cat_name not in allocated_courts:
            continue
        
        allocation = allocated_courts[cat_name]
        eligible_players = court_plans[cat_name]['eligible_players']
        
        # Create doubles matches
        if allocation['doubles'] > 0:
            doubles_matches = await create_doubles_matches(
                eligible_players, allocation['doubles'], cat_name, 
                round_index, court_index, session_obj.histories
            )
            created_matches.extend(doubles_matches)
            court_index += len(doubles_matches)
            
            # Track used players
            for match in doubles_matches:
                used_player_ids.update(match.teamA + match.teamB)
        
        # Create singles matches
        if allocation['singles'] > 0:
            # Get remaining players not used in doubles
            remaining_players = [p for p in eligible_players if p.id not in used_player_ids]
            
            singles_matches = await create_singles_matches(
                remaining_players, allocation['singles'], cat_name,
                round_index, court_index, session_obj.histories
            )
            created_matches.extend(singles_matches)
            court_index += len(singles_matches)
            
            # Track used players
            for match in singles_matches:
                used_player_ids.update(match.teamA + match.teamB)
    
    # Update sit counts and missDueToCourtLimit
    for player in players:
        if player.id not in used_player_ids and not player.sitNextRound:
            # Player is sitting due to court limitations
            await db.players.update_one(
                {"id": player.id},
                {"$inc": {"missDueToCourtLimit": 1}}
            )
        
        if player.id not in used_player_ids:
            # Player is sitting (either forced or due to limitations)
            await db.players.update_one(
                {"id": player.id},
                {"$inc": {"sitCount": 1}}
            )
        
        # Reset sitNextRound flag
        await db.players.update_one(
            {"id": player.id},
            {"$set": {"sitNextRound": False}}
        )
    
    # Save matches to database
    for match in created_matches:
        await db.matches.insert_one(match.dict())
        # Update histories
        session_obj.histories = update_histories(match, session_obj.histories)
    
    # Update session histories
    await db.session.update_one({}, {"$set": {"histories": session_obj.histories}})
    
    return created_matches

async def create_doubles_matches(
    players: List[Player], 
    num_matches: int, 
    category: str, 
    round_index: int, 
    start_court_index: int,
    histories: Dict[str, Any]
) -> List[Match]:
    """Create doubles matches with fair partner pairing"""
    matches = []
    shuffled_players = shuffle_list(players)
    
    # Create teams (pairs)
    teams = []
    used_indices = set()
    
    for i, player_a in enumerate(shuffled_players):
        if i in used_indices:
            continue
        
        best_partner = None
        best_score = float('inf')
        best_index = -1
        
        # Find best partner (lowest partner history score)
        for j, player_b in enumerate(shuffled_players[i+1:], i+1):
            if j in used_indices:
                continue
            
            partner_score = calculate_partner_score(player_a.id, player_b.id, histories)
            
            if partner_score < best_score or (partner_score == best_score and player_b.name < (best_partner.name if best_partner else "zzz")):
                best_partner = player_b
                best_score = partner_score
                best_index = j
        
        if best_partner:
            teams.append([player_a.id, best_partner.id])
            used_indices.add(i)
            used_indices.add(best_index)
            
            if len(teams) >= num_matches * 2:
                break
    
    # Pair teams into matches
    used_team_indices = set()
    
    for i, team_a in enumerate(teams):
        # Check if we've created enough matches
        if len(matches) >= num_matches:
            break
            
        # Skip if this team is already used
        if i in used_team_indices:
            continue  # Continue to next team instead of breaking
        
        best_opponent_team = None
        best_opponent_score = float('inf')
        best_opponent_index = -1
        
        # Find best opponent team (lowest opponent history score)
        for j, team_b in enumerate(teams[i+1:], i+1):
            if j in used_team_indices:
                continue
            
            opponent_score = calculate_opponent_score(team_a, team_b, histories)
            
            if opponent_score < best_opponent_score:
                best_opponent_team = team_b
                best_opponent_score = opponent_score
                best_opponent_index = j
        
        if best_opponent_team:
            match = Match(
                roundIndex=round_index,
                courtIndex=start_court_index + len(matches),
                category=category,
                teamA=team_a,
                teamB=best_opponent_team,
                matchType=MatchType.doubles,
                status=MatchStatus.pending
            )
            matches.append(match)
            used_team_indices.add(i)
            used_team_indices.add(best_opponent_index)
    
    return matches

async def create_singles_matches(
    players: List[Player], 
    num_matches: int, 
    category: str, 
    round_index: int, 
    start_court_index: int,
    histories: Dict[str, Any]
) -> List[Match]:
    """Create singles matches with fair opponent pairing"""
    matches = []
    
    # Sort players by sit priority (least sits first)
    sorted_players = sorted(players, key=lambda p: (p.sitCount, p.missDueToCourtLimit, p.name))
    
    # Take players for singles matches
    players_for_singles = sorted_players[:num_matches * 2]
    shuffled_singles = shuffle_list(players_for_singles)
    
    used_indices = set()
    
    for i, player_a in enumerate(shuffled_singles):
        if i in used_indices or len(matches) >= num_matches:
            break
        
        best_opponent = None
        best_score = float('inf')
        best_index = -1
        
        # Find best opponent (lowest opponent history)
        for j, player_b in enumerate(shuffled_singles[i+1:], i+1):
            if j in used_indices:
                continue
            
            opponent_score = calculate_opponent_score([player_a.id], [player_b.id], histories)
            
            if opponent_score < best_score or (opponent_score == best_score and player_b.name < (best_opponent.name if best_opponent else "zzz")):
                best_opponent = player_b
                best_score = opponent_score
                best_index = j
        
        if best_opponent:
            match = Match(
                roundIndex=round_index,
                courtIndex=start_court_index + len(matches),
                category=category,
                teamA=[player_a.id],
                teamB=[best_opponent.id],
                matchType=MatchType.singles,
                status=MatchStatus.pending
            )
            matches.append(match)
            used_indices.add(i)
            used_indices.add(best_index)
    
    return matches

# API Routes

# Categories
@api_router.get("/categories", response_model=List[Category])
async def get_categories(db_session: AsyncSession = Depends(get_db_session)):
    """Get all categories from SQLite database"""
    try:
        result = await db_session.execute(select(DBCategory))
        categories = result.scalars().all()
        
        # Convert SQLAlchemy models to Pydantic models
        category_list = []
        for db_category in categories:
            category_dict = {
                "id": db_category.id,
                "name": db_category.name,
                "description": db_category.description
            }
            category_list.append(Category(**category_dict))
        
        return category_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")

@api_router.post("/categories", response_model=Category)
async def create_category(category: CategoryCreate, db_session: AsyncSession = Depends(get_db_session)):
    """Create a new category in SQLite database"""
    try:
        # Check if category already exists
        result = await db_session.execute(select(DBCategory).where(DBCategory.name == category.name))
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(status_code=400, detail="Category already exists")
        
        # Create new category
        db_category = DBCategory(
            name=category.name,
            description=category.description
        )
        
        db_session.add(db_category)
        await db_session.commit()
        await db_session.refresh(db_category)
        
        # Convert to Pydantic model for response
        category_dict = {
            "id": db_category.id,
            "name": db_category.name,
            "description": db_category.description
        }
        
        return Category(**category_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create category: {str(e)}")

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, db_session: AsyncSession = Depends(get_db_session)):
    """Delete a category from SQLite database"""
    try:
        # Find the category
        result = await db_session.execute(select(DBCategory).where(DBCategory.id == category_id))
        db_category = result.scalar_one_or_none()
        
        if not db_category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Delete the category
        await db_session.delete(db_category)
        await db_session.commit()
        
        return {"message": "Category deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete category: {str(e)}")

# Data Management
@api_router.delete("/clear-all-data", response_model=dict)
async def clear_all_data(db: AsyncSession = Depends(get_db_session)):
    """Clear all data from the database for fresh start"""
    try:
        # Clear all SQLite tables
        await db.execute(delete(DBPlayer))
        await db.execute(delete(DBCategory))  
        await db.execute(delete(DBMatch))
        await db.execute(delete(DBSession))
        
        # Reinitialize with default categories
        default_categories = [
            DBCategory(name="Beginner"),
            DBCategory(name="Intermediate"), 
            DBCategory(name="Advanced")
        ]
        
        for category in default_categories:
            db.add(category)
        
        # Create fresh session
        session_obj = DBSession(
            config=json.dumps({
                "numCourts": 4,
                "playSeconds": 720,
                "bufferSeconds": 30,
                "allowSingles": True,
                "allowDoubles": True,
                "allowCrossCategory": False,
                "maximizeCourtUsage": False
            }),
            histories=json.dumps({
                "partnerHistory": {},
                "opponentHistory": {}
            })
        )
        db.add(session_obj)
        
        await db.commit()
        return {"message": "All data cleared successfully"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")

@api_router.post("/add-test-data", response_model=dict)
async def add_test_data(db: AsyncSession = Depends(get_db_session)):
    """Add sample test players for testing purposes"""
    try:
        # Sample players with ratings
        test_players = [
            {"name": "John Smith", "category": "Beginner", "rating": 3.2},
            {"name": "Jane Doe", "category": "Beginner", "rating": 3.5},
            {"name": "Mike Johnson", "category": "Intermediate", "rating": 4.1},
            {"name": "Sarah Wilson", "category": "Intermediate", "rating": 4.3},
            {"name": "David Brown", "category": "Advanced", "rating": 5.2},
            {"name": "Lisa Garcia", "category": "Advanced", "rating": 5.5},
            {"name": "Tom Anderson", "category": "Beginner", "rating": 3.0},
            {"name": "Emily Chen", "category": "Intermediate", "rating": 4.0},
            {"name": "Robert Taylor", "category": "Advanced", "rating": 5.8},
            {"name": "Maria Rodriguez", "category": "Beginner", "rating": 3.3},
            {"name": "James Wilson", "category": "Intermediate", "rating": 4.2},
            {"name": "Ashley Johnson", "category": "Advanced", "rating": 5.1}
        ]
        
        # Clear existing players first
        await db.execute(delete(DBPlayer))
        
        # Add test players
        created_count = 0
        for player_data in test_players:
            player = DBPlayer(
                name=player_data["name"],
                category=player_data["category"],
                rating=player_data["rating"]
            )
            db.add(player)
            created_count += 1
        
        await db.commit()
        return {"message": f"Successfully added {created_count} test players"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add test data: {str(e)}")

# Players
@api_router.get("/players", response_model=List[Player])
async def get_players(db_session: AsyncSession = Depends(get_db_session)):
    """Get all players from SQLite database"""
    try:
        result = await db_session.execute(select(DBPlayer))
        players = result.scalars().all()
        
        # Convert SQLAlchemy models to Pydantic models for response
        player_list = []
        for db_player in players:
            # Parse JSON fields
            recent_form = json.loads(db_player.recent_form) if db_player.recent_form else []
            rating_history = json.loads(db_player.rating_history) if db_player.rating_history else []
            
            player_dict = {
                "id": db_player.id,
                "name": db_player.name,
                "category": db_player.category,
                "sitNextRound": db_player.sit_next_round,
                "sitCount": db_player.sit_count,
                "missDueToCourtLimit": db_player.miss_due_to_court_limit,
                "rating": db_player.rating,
                "matchesPlayed": db_player.matches_played,
                "wins": db_player.wins,
                "losses": db_player.losses,
                "recentForm": recent_form,
                "ratingHistory": rating_history,
                "lastUpdated": db_player.last_updated.isoformat() if db_player.last_updated else datetime.now().isoformat(),
                "stats": {
                    "wins": db_player.stats_wins,
                    "losses": db_player.stats_losses,
                    "pointDiff": db_player.stats_point_diff
                }
            }
            player_list.append(Player(**player_dict))
        
        return player_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get players: {str(e)}")

# SQLite Players API (for testing)
@api_router.get("/sqlite/players")
async def get_sqlite_players(db_session: AsyncSession = Depends(get_db_session)):
    """Get players from SQLite database"""
    try:
        result = await db_session.execute(select(DBPlayer))
        players = result.scalars().all()
        
        # Convert SQLAlchemy models to Pydantic models for response
        player_list = []
        for db_player in players:
            # Parse JSON fields
            recent_form = json.loads(db_player.recent_form) if db_player.recent_form else []
            rating_history = json.loads(db_player.rating_history) if db_player.rating_history else []
            
            player_dict = {
                "id": db_player.id,
                "name": db_player.name,
                "category": db_player.category,
                "sitNextRound": db_player.sit_next_round,
                "sitCount": db_player.sit_count,
                "missDueToCourtLimit": db_player.miss_due_to_court_limit,
                "rating": db_player.rating,
                "matchesPlayed": db_player.matches_played,
                "wins": db_player.wins,
                "losses": db_player.losses,
                "recentForm": recent_form,
                "ratingHistory": rating_history,
                "lastUpdated": db_player.last_updated.isoformat() if db_player.last_updated else datetime.now().isoformat(),
                "stats": {
                    "wins": db_player.stats_wins,
                    "losses": db_player.stats_losses,
                    "pointDiff": db_player.stats_point_diff
                }
            }
            player_list.append(player_dict)
        
        return player_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get players: {str(e)}")

@api_router.post("/players", response_model=Player)
async def create_player(player: PlayerCreate, db_session: AsyncSession = Depends(get_db_session)):
    """Create a new player in SQLite database"""
    try:
        # Create SQLAlchemy player object
        db_player = DBPlayer(
            name=player.name,
            category=player.category,
            rating=3.0,  # Default DUPR rating
            recent_form=json.dumps([]),  # Empty recent form
            rating_history=json.dumps([])  # Empty rating history
        )
        
        db_session.add(db_player)
        await db_session.commit()
        await db_session.refresh(db_player)
        
        # Convert back to Pydantic model for response
        player_dict = {
            "id": db_player.id,
            "name": db_player.name,
            "category": db_player.category,
            "sitNextRound": db_player.sit_next_round,
            "sitCount": db_player.sit_count,
            "missDueToCourtLimit": db_player.miss_due_to_court_limit,
            "rating": db_player.rating,
            "matchesPlayed": db_player.matches_played,
            "wins": db_player.wins,
            "losses": db_player.losses,
            "recentForm": [],
            "ratingHistory": [],
            "lastUpdated": db_player.last_updated.isoformat() if db_player.last_updated else datetime.now().isoformat(),
            "stats": {
                "wins": db_player.stats_wins,
                "losses": db_player.stats_losses,
                "pointDiff": db_player.stats_point_diff
            }
        }
        
        return Player(**player_dict)
        
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create player: {str(e)}")

@api_router.put("/players/{player_id}", response_model=Player)
async def update_player(player_id: str, updates: PlayerUpdate, db_session: AsyncSession = Depends(get_db_session)):
    """Update a player in SQLite database"""
    try:
        # Find the player
        result = await db_session.execute(select(DBPlayer).where(DBPlayer.id == player_id))
        db_player = result.scalar_one_or_none()
        
        if not db_player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Update fields that are provided
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        
        if "name" in update_data:
            db_player.name = update_data["name"]
        if "category" in update_data:
            db_player.category = update_data["category"]
        if "sitNextRound" in update_data:
            db_player.sit_next_round = update_data["sitNextRound"]
        
        await db_session.commit()
        await db_session.refresh(db_player)
        
        # Convert back to Pydantic model for response
        recent_form = json.loads(db_player.recent_form) if db_player.recent_form else []
        rating_history = json.loads(db_player.rating_history) if db_player.rating_history else []
        
        player_dict = {
            "id": db_player.id,
            "name": db_player.name,
            "category": db_player.category,
            "sitNextRound": db_player.sit_next_round,
            "sitCount": db_player.sit_count,
            "missDueToCourtLimit": db_player.miss_due_to_court_limit,
            "rating": db_player.rating,
            "matchesPlayed": db_player.matches_played,
            "wins": db_player.wins,
            "losses": db_player.losses,
            "recentForm": recent_form,
            "ratingHistory": rating_history,
            "lastUpdated": db_player.last_updated.isoformat() if db_player.last_updated else datetime.now().isoformat(),
            "stats": {
                "wins": db_player.stats_wins,
                "losses": db_player.stats_losses,
                "pointDiff": db_player.stats_point_diff
            }
        }
        
        return Player(**player_dict)
        
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update player: {str(e)}")

@api_router.delete("/players/{player_id}")
async def delete_player(player_id: str, db_session: AsyncSession = Depends(get_db_session)):
    """Delete a player from SQLite database"""
    try:
        # Find the player
        result = await db_session.execute(select(DBPlayer).where(DBPlayer.id == player_id))
        db_player = result.scalar_one_or_none()
        
        if not db_player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Delete the player
        await db_session.delete(db_player)
        await db_session.commit()
        
        return {"message": "Player deleted"}
        
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete player: {str(e)}")

# Matches
@api_router.get("/matches", response_model=List[Match])
async def get_matches(db_session: AsyncSession = Depends(get_db_session)):
    """Get all matches from SQLite database"""
    try:
        result = await db_session.execute(select(DBMatch))
        matches = result.scalars().all()
        
        # Convert SQLAlchemy models to Pydantic models
        match_list = []
        for db_match in matches:
            # Parse JSON fields
            team_a = json.loads(db_match.team_a) if db_match.team_a else []
            team_b = json.loads(db_match.team_b) if db_match.team_b else []
            
            match_dict = {
                "id": db_match.id,
                "roundIndex": db_match.round_index,
                "courtIndex": db_match.court_index,
                "category": db_match.category,
                "teamA": team_a,
                "teamB": team_b,
                "status": db_match.status,
                "matchType": db_match.match_type,
                "scoreA": db_match.score_a,
                "scoreB": db_match.score_b
            }
            match_list.append(Match(**match_dict))
        
        return match_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get matches: {str(e)}")

@api_router.get("/matches/round/{round_index}", response_model=List[Match])
async def get_matches_by_round(round_index: int, db_session: AsyncSession = Depends(get_db_session)):
    """Get matches by round from SQLite database"""
    try:
        result = await db_session.execute(select(DBMatch).where(DBMatch.round_index == round_index))
        matches = result.scalars().all()
        
        # Convert SQLAlchemy models to Pydantic models
        match_list = []
        for db_match in matches:
            # Parse JSON fields
            team_a = json.loads(db_match.team_a) if db_match.team_a else []
            team_b = json.loads(db_match.team_b) if db_match.team_b else []
            
            match_dict = {
                "id": db_match.id,
                "roundIndex": db_match.round_index,
                "courtIndex": db_match.court_index,
                "category": db_match.category,
                "teamA": team_a,
                "teamB": team_b,
                "status": db_match.status,
                "matchType": db_match.match_type,
                "scoreA": db_match.score_a,
                "scoreB": db_match.score_b
            }
            match_list.append(Match(**match_dict))
        
        return match_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get matches by round: {str(e)}")

@api_router.put("/matches/{match_id}/score", response_model=Match)
async def update_match_score(match_id: str, score_update: MatchScoreUpdate):
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Update match with scores and mark as done
    await db.matches.update_one(
        {"id": match_id}, 
        {"$set": {
            "scoreA": score_update.scoreA,
            "scoreB": score_update.scoreB,
            "status": MatchStatus.done.value
        }}
    )
    
    # Update player stats
    match_obj = Match(**match)
    
    # Determine winner and loser
    if score_update.scoreA > score_update.scoreB:
        winner_team = match_obj.teamA
        loser_team = match_obj.teamB
        winner_score = score_update.scoreA
        loser_score = score_update.scoreB
    else:
        winner_team = match_obj.teamB
        loser_team = match_obj.teamA
        winner_score = score_update.scoreB
        loser_score = score_update.scoreA
    
    point_diff = winner_score - loser_score
    
    # Update winner stats
    for player_id in winner_team:
        await db.players.update_one(
            {"id": player_id},
            {"$inc": {
                "stats.wins": 1,
                "stats.pointDiff": point_diff
            }}
        )
    
    # Update loser stats
    for player_id in loser_team:
        await db.players.update_one(
            {"id": player_id},
            {"$inc": {
                "stats.losses": 1,
                "stats.pointDiff": -point_diff
            }}
        )
    
    # Update DUPR-style ratings
    await update_player_ratings(match, score_update.scoreA, score_update.scoreB)
    
    updated_match = await db.matches.find_one({"id": match_id})
    return Match(**updated_match)

# Session Management
@api_router.get("/session", response_model=SessionState)
async def get_session():
    session = await db.session.find_one()
    if not session:
        # Create default session
        session_obj = SessionState()
        await db.session.insert_one(session_obj.dict())
        return session_obj
    return SessionState(**session)

@api_router.put("/session/config", response_model=SessionState)
async def update_session_config(config: SessionConfig):
    # Validate that at least one format is selected
    if not config.allowSingles and not config.allowDoubles:
        raise HTTPException(
            status_code=400, 
            detail="At least one format (Singles or Doubles) must be selected"
        )
    
    session = await db.session.find_one()
    if not session:
        session_obj = SessionState(config=config)
        await db.session.insert_one(session_obj.dict())
        return session_obj
    
    await db.session.update_one({}, {"$set": {"config": config.dict()}})
    updated_session = await db.session.find_one()
    return SessionState(**updated_session)

@api_router.post("/session/generate-matches", response_model=SessionState)
async def generate_matches():
    """Generate matches and set session to 'ready' phase - players can see assignments"""
    try:
        # Get current session
        session_obj = await get_session()
        
        # Check if we have enough players based on enabled formats
        players_count = await db.players.count_documents({})
        
        # Validate format configuration
        if not session_obj.config.allowSingles and not session_obj.config.allowDoubles:
            raise HTTPException(
                status_code=400,
                detail="At least one format (Singles or Doubles) must be enabled"
            )
        
        # Determine minimum players needed
        if session_obj.config.allowDoubles:
            min_players = 4  # Need at least 4 for doubles
        elif session_obj.config.allowSingles:
            min_players = 2  # Need at least 2 for singles
        else:
            min_players = 2  # Fallback
        
        if players_count < min_players:
            raise HTTPException(
                status_code=400, 
                detail=f"Need at least {min_players} players to generate matches"
            )
        
        # Reset all matches
        await db.matches.delete_many({})
        
        # Generate Round 1 matches
        matches = await schedule_round(1)
        if matches:
            for match in matches:
                await db.matches.insert_one(match.dict())
        
        # Update session to 'ready' phase (matches generated, waiting for timer start)
        await db.session.update_one(
            {}, 
            {"$set": {
                "currentRound": 1,
                "phase": SessionPhase.ready,  # New ready phase
                "timeRemaining": session_obj.config.playSeconds,
                "paused": False
            }}
        )
        
        return await get_session()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate matches: {str(e)}")

@api_router.post("/session/start", response_model=SessionState)
async def start_session():
    """Start the timer for matches that are already generated"""
    try:
        session_obj = await get_session()
        
        # Must be in 'ready' phase to start timer
        if session_obj.phase != SessionPhase.ready:
            raise HTTPException(
                status_code=400,
                detail="Session must be in 'ready' phase to start timer. Generate matches first."
            )
        
        # Start the timer by setting phase to 'play'
        await db.session.update_one(
            {}, 
            {"$set": {
                "phase": SessionPhase.play,
                "timeRemaining": session_obj.config.playSeconds
            }}
        )
        
        return await get_session()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")

@api_router.post("/session/next-round")
async def start_next_round():
    """Generate the next round of matches"""
    try:
        session = await db.session.find_one()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_obj = SessionState(**session)
        next_round = session_obj.currentRound + 1
        
        # Generate next round
        matches = await schedule_round(next_round)
        
        # Update session state
        await db.session.update_one(
            {}, 
            {"$set": {
                "currentRound": next_round,
                "phase": SessionPhase.play.value,
                "timeRemaining": session_obj.config.playSeconds
            }}
        )
        
        return {
            "message": f"Round {next_round} started successfully",
            "round": next_round,
            "matches_created": len(matches)
        }
        
    except Exception as e:
        logger.error(f"Error starting next round: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start next round: {str(e)}")

@api_router.post("/session/play")
async def start_play():
    """Start the play phase with timer"""
    session = await db.session.find_one()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_obj = SessionState(**session)
    
    await db.session.update_one({}, {"$set": {
        "phase": SessionPhase.play.value,
        "timeRemaining": session_obj.config.playSeconds,
        "paused": False
    }})
    
    return {"message": "Play started", "phase": "play", "timeRemaining": session_obj.config.playSeconds}

@api_router.post("/session/pause")
async def pause_session():
    await db.session.update_one({}, {"$set": {"paused": True}})
    return {"message": "Session paused"}

@api_router.post("/session/resume")
async def resume_session():
    await db.session.update_one({}, {"$set": {"paused": False}})
    return {"message": "Session resumed"}

@api_router.post("/session/horn")
async def horn_now():
    """Manual horn activation and phase transition"""
    session = await db.session.find_one()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_obj = SessionState(**session)
    
    if session_obj.phase == SessionPhase.play:
        # Transition to buffer
        await db.session.update_one({}, {"$set": {
            "phase": SessionPhase.buffer.value,
            "timeRemaining": session_obj.config.bufferSeconds
        }})
        return {"message": "Horn activated - Buffer phase", "phase": "buffer", "horn": "end"}
    
    elif session_obj.phase == SessionPhase.buffer:
        # Transition to next round or end session
        total_rounds = math.floor(7200 / max(1, session_obj.config.playSeconds + session_obj.config.bufferSeconds))
        
        if session_obj.currentRound >= total_rounds:
            # End session
            await db.session.update_one({}, {"$set": {
                "phase": SessionPhase.ended.value,
                "timeRemaining": 0
            }})
            return {"message": "Session ended", "phase": "ended", "horn": "end"}
        else:
            # Start next round
            try:
                matches = await schedule_round(session_obj.currentRound + 1)
                await db.session.update_one({}, {"$set": {
                    "currentRound": session_obj.currentRound + 1,
                    "phase": SessionPhase.play.value,
                    "timeRemaining": session_obj.config.playSeconds
                }})
                return {
                    "message": f"Round {session_obj.currentRound + 1} started", 
                    "phase": "play", 
                    "horn": "start",
                    "round": session_obj.currentRound + 1,
                    "matches_created": len(matches)
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to start next round: {str(e)}")
    
    return {"message": "Horn activated", "horn": "manual"}

@api_router.post("/session/reset")
async def reset_session():
    # Clear all matches
    await db.matches.delete_many({})
    
    # Reset player counters and stats
    await db.players.update_many({}, {"$set": {
        "sitNextRound": False,
        "sitCount": 0,
        "missDueToCourtLimit": 0,
        "stats.wins": 0,
        "stats.losses": 0,
        "stats.pointDiff": 0
    }})
    
    # Get current session to preserve config
    session = await db.session.find_one()
    if session:
        session_obj = SessionState(**session)
        play_time = session_obj.config.playSeconds
    else:
        play_time = 720  # default 12 minutes
    
    # Reset session state with timer set to play time
    await db.session.update_one({}, {"$set": {
        "currentRound": 0,
        "phase": SessionPhase.idle.value,
        "timeRemaining": play_time,  # Set to play time instead of 0
        "paused": False,
        "histories": {}
    }})
    
    return {"message": "Session reset"}

@api_router.post("/session/horn")
async def horn_now():
    # This will implement the horn logic
    return {"message": "Horn activated"}

# Initialize default categories
@api_router.post("/init")
async def initialize_data():
    # Check if categories exist
    existing_cats = await db.categories.count_documents({})
    if existing_cats == 0:
        default_categories = [
            Category(name="Beginner", description="New to pickleball"),
            Category(name="Intermediate", description="Some experience"),
            Category(name="Advanced", description="Experienced players")
        ]
        for cat in default_categories:
            await db.categories.insert_one(cat.dict())
    
    # Ensure session exists
    session = await db.session.find_one()
    if not session:
        session_obj = SessionState()
        await db.session.insert_one(session_obj.dict())
    
    return {"message": "Data initialized"}

# Include the router in the main app
app.include_router(api_router)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    await init_database()
    print("✅ SQLite database initialized")

@app.on_event("shutdown") 
async def shutdown_event():
    print("🔄 Shutting down...")

# Removed MongoDB cleanup as we're using SQLite now