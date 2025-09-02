from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from enum import Enum
import random
import math
from collections import defaultdict

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

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
        
        # Determine match allocation based on format
        if config.format == Format.singles:
            if len(eligible_players) >= 2:
                singles_matches = len(eligible_players) // 2
        else:  # doubles or auto
            count = len(eligible_players)
            if count >= 4:
                # Tentative doubles calculation
                tentative_doubles = count // 4
                remainder = count % 4
                
                # Handle remainder to avoid 1 or 3 leftovers
                if remainder in [1, 3]:
                    # Sit 1 lowest-sit player to make remainder 0 or 2
                    eligible_players.sort(key=lambda p: (p.sitCount, p.missDueToCourtLimit, p.name))
                    sit_player = eligible_players.pop(0)
                    # Mark this player to get missDueToCourtLimit increment later
                    
                    # Recalculate after sitting one player
                    count = len(eligible_players)
                    doubles_matches = count // 4
                    remainder = count % 4
                
                if remainder == 2 and config.format == Format.auto:
                    # Use 2 leftovers for singles match
                    singles_matches = 1
                    doubles_matches = (count - 2) // 4
                else:
                    doubles_matches = count // 4
            elif len(eligible_players) == 2 and config.format == Format.auto:
                # Fallback to singles for 2 players
                singles_matches = 1
        
        court_plans[cat_name] = {
            'doubles': doubles_matches,
            'singles': singles_matches,
            'eligible_players': eligible_players
        }
    
    # Calculate total courts needed
    total_courts_needed = sum(plan['doubles'] + plan['singles'] for plan in court_plans.values())
    available_courts = min(config.numCourts, total_courts_needed)
    
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
        if i in used_team_indices or len(matches) >= num_matches:
            break
        
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
async def get_categories():
    categories = await db.categories.find().to_list(1000)
    return [Category(**cat) for cat in categories]

@api_router.post("/categories", response_model=Category)
async def create_category(category: CategoryCreate):
    # Check if category already exists
    existing = await db.categories.find_one({"name": category.name})
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    cat_obj = Category(**category.dict())
    await db.categories.insert_one(cat_obj.dict())
    return cat_obj

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str):
    result = await db.categories.delete_one({"id": category_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted"}

# Players
@api_router.get("/players", response_model=List[Player])
async def get_players():
    players = await db.players.find().to_list(1000)
    return [Player(**player) for player in players]

@api_router.post("/players", response_model=Player)
async def create_player(player: PlayerCreate):
    player_obj = Player(**player.dict())
    await db.players.insert_one(player_obj.dict())
    return player_obj

@api_router.put("/players/{player_id}", response_model=Player)
async def update_player(player_id: str, updates: PlayerUpdate):
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    await db.players.update_one({"id": player_id}, {"$set": update_data})
    
    updated_player = await db.players.find_one({"id": player_id})
    return Player(**updated_player)

@api_router.delete("/players/{player_id}")
async def delete_player(player_id: str):
    result = await db.players.delete_one({"id": player_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Player not found")
    return {"message": "Player deleted"}

# Matches
@api_router.get("/matches", response_model=List[Match])
async def get_matches():
    matches = await db.matches.find().to_list(1000)
    return [Match(**match) for match in matches]

@api_router.get("/matches/round/{round_index}", response_model=List[Match])
async def get_matches_by_round(round_index: int):
    matches = await db.matches.find({"roundIndex": round_index}).to_list(1000)
    return [Match(**match) for match in matches]

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
    session = await db.session.find_one()
    if not session:
        session_obj = SessionState(config=config)
        await db.session.insert_one(session_obj.dict())
        return session_obj
    
    await db.session.update_one({}, {"$set": {"config": config.dict()}})
    updated_session = await db.session.find_one()
    return SessionState(**updated_session)

@api_router.post("/session/start")
async def start_session():
    """Start a new pickleball session and generate the first round"""
    try:
        # Get current session
        session = await db.session.find_one()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_obj = SessionState(**session)
        
        # Check if we have enough players
        players_count = await db.players.count_documents({})
        min_players = 4 if session_obj.config.format in [Format.doubles, Format.auto] else 2
        
        if players_count < min_players:
            raise HTTPException(
                status_code=400, 
                detail=f"Need at least {min_players} players to start session"
            )
        
        # Clear any existing matches
        await db.matches.delete_many({})
        
        # Generate first round
        matches = await schedule_round(1)
        
        # Update session state
        await db.session.update_one(
            {}, 
            {"$set": {
                "phase": SessionPhase.play.value,
                "currentRound": 1,
                "paused": False,
                "timeRemaining": session_obj.config.playSeconds
            }}
        )
        
        return {
            "message": "Session started successfully",
            "round": 1,
            "matches_created": len(matches)
        }
        
    except Exception as e:
        logger.error(f"Error starting session: {str(e)}")
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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()