import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Deployment environment detection
IS_DEPLOYMENT = os.getenv("DEPLOYMENT_ENV") == "production" or os.getenv("MONGO_URL") is not None

class DatabaseManager:
    def __init__(self):
        self.is_mongo = IS_DEPLOYMENT
        if self.is_mongo:
            self._setup_mongodb()
        else:
            self._setup_sqlite()
    
    def _setup_mongodb(self):
        """Setup MongoDB connection for deployment"""
        mongo_url = os.getenv("MONGO_URL")
        if not mongo_url:
            raise ValueError("MONGO_URL environment variable required for deployment")
        
        self.mongo_client = AsyncIOMotorClient(mongo_url)
        self.db = self.mongo_client[os.getenv("DB_NAME", "courtchime")]
        
    def _setup_sqlite(self):
        """Setup SQLite connection for development"""
        db_name = os.getenv("DB_NAME", "courtchime")
        database_url = f"sqlite+aiosqlite:///./{db_name}.db"
        
        # Create async engine
        self.engine = create_async_engine(
            database_url,
            echo=False,
            future=True
        )
        
        # Create session factory
        self.async_session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def get_session(self):
        """Get database session based on environment"""
        if self.is_mongo:
            return self.db
        else:
            return self.async_session_factory()
    
    def is_mongodb(self) -> bool:
        """Check if using MongoDB"""
        return self.is_mongo

# Global database manager instance
db_manager = DatabaseManager()

async def get_db_session():
    """Dependency for FastAPI to get database session"""
    return await db_manager.get_session()