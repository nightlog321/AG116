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
    format: Format = Format.auto

class SessionState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    currentRound: int = 0
    phase: SessionPhase = SessionPhase.idle
    timeRemaining: int = 0
    paused: bool = False
    config: SessionConfig = Field(default_factory=SessionConfig)
    histories: Dict[str, Any] = Field(default_factory=dict)  # partners and opponents histories

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
    # This will be implemented with the scheduling logic
    await db.session.update_one(
        {}, 
        {"$set": {
            "phase": SessionPhase.play.value,
            "currentRound": 1,
            "paused": False
        }},
        upsert=True
    )
    return {"message": "Session started"}

@api_router.post("/session/pause")
async def pause_session():
    await db.session.update_one({}, {"$set": {"paused": True}})
    return {"message": "Session paused"}

@api_router.post("/session/resume")
async def resume_session():
    await db.session.update_one({}, {"$set": {"paused": False}})
    return {"message": "Session resumed"}

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
    
    # Reset session state
    await db.session.update_one({}, {"$set": {
        "currentRound": 0,
        "phase": SessionPhase.idle.value,
        "timeRemaining": 0,
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