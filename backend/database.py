from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import json
from datetime import datetime
import uuid
import os

# SQLite database URL
DATABASE_URL = "sqlite+aiosqlite:///./courtchime.db"

# Create async engine for SQLite
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Database Models (SQLAlchemy equivalent of Pydantic models)

class Club(Base):
    __tablename__ = "clubs"
    
    name = Column(String, primary_key=True)  # Club name is the identifier
    display_name = Column(String, nullable=False)  # For display purposes
    description = Column(String)
    created_at = Column(DateTime, default=datetime.now)

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(String)

class Player(Base):
    __tablename__ = "players"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    sit_next_round = Column(Boolean, default=False)
    sit_count = Column(Integer, default=0)
    miss_due_to_court_limit = Column(Integer, default=0)
    
    # DUPR-style rating fields
    rating = Column(Float, default=3.0)
    matches_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    recent_form = Column(Text, default="[]")  # JSON string for list of W/L
    rating_history = Column(Text, default="[]")  # JSON string for rating changes
    last_updated = Column(DateTime, default=datetime.now)
    
    # Stats
    stats_wins = Column(Integer, default=0)
    stats_losses = Column(Integer, default=0)
    stats_point_diff = Column(Integer, default=0)

class Match(Base):
    __tablename__ = "matches"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    round_index = Column(Integer, nullable=False)
    court_index = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    match_type = Column(String, nullable=False)  # 'singles' or 'doubles'
    team_a = Column(Text, nullable=False)  # JSON string for list of player IDs
    team_b = Column(Text, nullable=False)  # JSON string for list of player IDs
    score_a = Column(Integer)
    score_b = Column(Integer)
    status = Column(String, default="pending")  # pending, completed

class Session(Base):
    __tablename__ = "session"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    current_round = Column(Integer, default=0)
    phase = Column(String, default="idle")  # idle, ready, play, buffer, ended
    time_remaining = Column(Integer, default=720)  # seconds
    paused = Column(Boolean, default=False)
    
    # Configuration as JSON
    config = Column(Text, default="{}")  # JSON string for session config
    
    # Histories as JSON
    histories = Column(Text, default="{}")  # JSON string for partner/opponent histories

# Database helper functions
async def get_db_session():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def init_database():
    """Initialize database with default data"""
    await create_tables()
    
    async with async_session() as session:
        # Check if categories exist
        from sqlalchemy import select
        result = await session.execute(select(Category))
        categories = result.scalars().all()
        
        if not categories:
            # Add default categories
            default_categories = [
                Category(name="Beginner"),
                Category(name="Intermediate"),
                Category(name="Advanced")
            ]
            
            for category in default_categories:
                session.add(category)
            
            # Add default session
            from datetime import datetime
            default_session = Session(
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
            session.add(default_session)
            
            await session.commit()
            print("✅ Database initialized with default data")