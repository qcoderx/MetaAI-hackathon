from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auto_closer.db")

# Configure engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={
        "check_same_thread": False  # Needed for SQLite
    } if "sqlite" in DATABASE_URL else {
        "sslmode": "require",
        "connect_timeout": 10,
        "application_name": "auto_closer"
    }
)

def create_db_and_tables():
    try:
        SQLModel.metadata.create_all(engine)
        print(f"✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Database creation failed: {e}")

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session