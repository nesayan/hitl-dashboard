from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Synchronous engine and session
engine = create_engine('sqlite:///dev.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Asynchronous engine and session
async_engine = create_async_engine('sqlite+aiosqlite:///dev.db')  # echo=True for logging SQL queries
AsyncSessionLocal = sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

            