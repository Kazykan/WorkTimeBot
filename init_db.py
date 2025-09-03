import asyncio
import logging

from app.config import get_settings
from app.db.session import _engine, Base
from app.models import User, WorkObject, TimeEntry, Payment  # Import models to register them

logger = logging.getLogger(__name__)


async def init_db():
    """Initialize database tables"""
    settings = get_settings()
    
    logger.info("Creating database tables...")
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())
