from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from beanie import Document, Indexed
import uuid

# MongoDB document models using Beanie
class MongoPlayer(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Indexed(str)
    category: str
    sit_next_round: bool = False
    sit_count: int = 0
    miss_due_to_court_limit: int = 0
    stats_wins: int = 0
    stats_losses: int = 0  
    stats_point_diff: int = 0
    rating: float = 3.0
    matches_played: int = 0
    recent_form: List[str] = []
    rating_history: List[Dict[str, Any]] = []
    last_updated: Optional[datetime] = None
    club_name: str = "Main Club"

    class Settings:
        name = "players"

class MongoCategory(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None

    class Settings:
        name = "categories"

class MongoMatch(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    round_index: int
    court_index: int
    category: str
    match_type: str = "doubles"
    team_a: List[str] = []
    team_b: List[str] = []
    score_a: int = 0
    score_b: int = 0
    status: str = "pending"
    club_name: str = "Main Club"

    class Settings:
        name = "matches"

class MongoSession(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    current_round: int = 0
    phase: str = "idle"
    time_remaining: int = 720
    paused: bool = False
    config: Dict[str, Any] = {}
    histories: Dict[str, Any] = {"partnerHistory": {}, "opponentHistory": {}}
    club_name: str = "Main Club"

    class Settings:
        name = "session"

class MongoClub(Document):
    name: Indexed(str, unique=True)
    display_name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "clubs"