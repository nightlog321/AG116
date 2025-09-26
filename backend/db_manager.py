import os
from typing import Optional, Union, List
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

# Import both database models
from database import get_db_session as get_sqlite_session, engine, init_database
from mongodb_models import MongoPlayer, MongoCategory, MongoMatch, MongoSession, MongoClub

load_dotenv()

class DatabaseManager:
    def __init__(self):
        # Detect environment based on MONGO_URL presence
        self.mongo_url = os.getenv("MONGO_URL")
        self.is_production = bool(self.mongo_url)
        self.db = None
        
    async def initialize(self):
        """Initialize the appropriate database"""
        if self.is_production:
            await self._init_mongodb()
        else:
            await self._init_sqlite()
    
    async def _init_mongodb(self):
        """Initialize MongoDB connection for production"""
        client = AsyncIOMotorClient(self.mongo_url)
        self.db = client[os.getenv("DB_NAME", "courtchime")]
        
        # Initialize Beanie with document models
        await init_beanie(
            database=self.db,
            document_models=[MongoPlayer, MongoCategory, MongoMatch, MongoSession, MongoClub]
        )
    
    async def _init_sqlite(self):
        """Initialize SQLite for development"""
        await init_database()
    
    def is_mongodb(self) -> bool:
        """Check if using MongoDB"""
        return self.is_production
    
    async def get_session(self):
        """Get appropriate database session"""
        if self.is_production:
            return self.db
        else:
            return await get_sqlite_session().__anext__()

# Global database manager
db_manager = DatabaseManager()

async def get_database_session():
    """FastAPI dependency to get database session"""
    return await db_manager.get_session()

def is_using_mongodb() -> bool:
    """Helper function to check if using MongoDB"""
    return db_manager.is_mongodb()