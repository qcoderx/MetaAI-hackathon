from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./naira_sniper.db")

# Configure engine with proper connection parameters for Neon
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "sslmode": "require",
        "connect_timeout": 10,
        "application_name": "naira_sniper"
    } if DATABASE_URL.startswith("postgresql") else {}
)

def create_db_and_tables():
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            SQLModel.metadata.create_all(engine)
            print(f"✅ Database tables created successfully")
            return
        except Exception as e:
            print(f"❌ Database attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise

def get_session() -> Generator[Session, None, None]:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with Session(engine) as session:
                yield session
                return
        except Exception as e:
            print(f"❌ Session attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(1)
            else:
                raise
