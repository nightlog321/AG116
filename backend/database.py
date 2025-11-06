from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import json
from datetime import datetime
import uuid
import os

# prefer a libsql remote connection (Turso) or fallback to local sqlite file
LIBSQL_URL = os.getenv("LIBSQL_DB_URL")   # put Turso URL here in Vercel
LIBSQL_AUTH = os.getenv("LIBSQL_DB_AUTH_TOKEN")

if LIBSQL_URL:
    # Turso/libSQL can be used via SQLAlchemy dialect `sqlite+aiosqlite://` is local,
    # but for Turso we will use the libsql/sqlite HTTP URL; SQLAlchemy's
    # create_async_engine with a proper dialect may be used - simplest approach:
    DATABASE_URL = LIBSQL_URL
    # If you prefer sqlalchemy-libsql dialect, set DATABASE_URL accordingly,
    # e.g. "libsql+asyncpg://..." depending on the adapter you choose.
else:
    # fallback to local sqlite file (for local dev / quick deploy)
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
    access_code = Column(String, nullable=False)  # Access code for club authentication
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
    club_name = Column(String, ForeignKey("clubs.name"), nullable=False)
    sit_next_round = Column(Boolean, default=False)
    sit_count = Column(Integer, default=0)
    miss_due_to_court_limit = Column(Integer, default=0)
    
    # Active status for daily sessions
    is_active = Column(Boolean, default=False)  # Default to inactive - must add to session
    
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
    
    # Relationship to club
    club = relationship("Club", backref="players")

class Match(Base):
    __tablename__ = "matches"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    round_index = Column(Integer, nullable=False)
    court_index = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    club_name = Column(String, ForeignKey("clubs.name"), nullable=False)
    match_type = Column(String, nullable=False)  # 'singles' or 'doubles'
    team_a = Column(Text, nullable=False)  # JSON string for list of player IDs
    team_b = Column(Text, nullable=False)  # JSON string for list of player IDs
    score_a = Column(Integer)
    score_b = Column(Integer)
    status = Column(String, default="pending")  # pending, completed
    
    # Match date tracking
    match_date = Column(DateTime, default=datetime.utcnow)  # Date when match was created
    
    # Relationship to club
    club = relationship("Club", backref="matches")

class Session(Base):
    __tablename__ = "session"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    club_name = Column(String, ForeignKey("clubs.name"), nullable=False)
    current_round = Column(Integer, default=0)
    phase = Column(String, default="idle")  # idle, ready, play, buffer, ended
    time_remaining = Column(Integer, default=720)  # seconds
    paused = Column(Boolean, default=False)
    
    # Session date - automatically captures the date when session is created/started
    session_date = Column(DateTime, default=datetime.now)  # Calendar date of the session
    
    # Configuration as JSON
    config = Column(Text, default="{}")  # JSON string for session config
    
    # Histories as JSON
    histories = Column(Text, default="{}")  # JSON string for partner/opponent histories
    
    # Relationship to club
    club = relationship("Club", backref="sessions")

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
    
    # Add migration for session_date column if it doesn't exist
    async with async_session() as db_session:
        try:
            from sqlalchemy import text
            from datetime import datetime
            # Check if session_date column exists
            result = await db_session.execute(text("PRAGMA table_info(session)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'session_date' not in columns:
                # Add the column without default first
                await db_session.execute(text("ALTER TABLE session ADD COLUMN session_date TIMESTAMP"))
                # Update existing rows with current timestamp
                current_time = datetime.now().isoformat()
                await db_session.execute(text(f"UPDATE session SET session_date = '{current_time}'"))
                await db_session.commit()
                print("✅ Added session_date column to session table")
        except Exception as e:
            print(f"Migration info: {e}")
            await db_session.rollback()
    
    async with async_session() as session:
        # Check if clubs exist
        from sqlalchemy import select
        result = await session.execute(select(Club))
        clubs = result.scalars().all()
        
        if not clubs:
            # Create default "Main Club" with access code
            default_club = Club(
                name="Main Club",
                display_name="Main Club",
                description="Default club for existing data migration",
                access_code="demo123"  # Default access code for Main Club
            )
            session.add(default_club)
        
        # Check if categories exist
        result = await session.execute(select(Category))
        categories = result.scalars().all()
        
        if not categories:
            # Add default global categories
            default_categories = [
                Category(name="Beginner"),
                Category(name="Intermediate"),
                Category(name="Advanced"),
                Category(name="Social")
            ]
            
            for category in default_categories:
                session.add(category)
        
        # Check if session exists for Main Club
        result = await session.execute(select(Session).where(Session.club_name == "Main Club"))
        main_session = result.scalar_one_or_none()
        
        if not main_session:
            # Add default session for Main Club
            from datetime import datetime
            default_session = Session(
                club_name="Main Club",
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
        print("✅ Database initialized with default multi-club data")
