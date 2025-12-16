from sqlmodel import SQLModel
from sqlalchemy import text
from app.database import engine
# Import your models to register them with SQLModel
from app.models import Business, Customer, BusinessRule, StatusReply

def reset_database():
    print("☢️  NUKING the database schema (Handling Zombie Tables)...")
    
    with engine.connect() as conn:
        # 1. Force drop the entire schema and everything inside it
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        conn.commit()
    
    print("✨ Schema wiped. Creating new clean tables...")
    
    # 2. Create tables based ONLY on your current models.py
    SQLModel.metadata.create_all(engine)
    
    print("✅ Database reset complete! You are ready to go.")

if __name__ == "__main__":
    reset_database()