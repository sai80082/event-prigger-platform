from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Read environment variables
ENV = os.getenv("ENV", "dev")  # Default to "dev" if not set
SQLITE_DB_URL = "sqlite:///./app.db"
POSTGRES_DB_URL = os.getenv("POSTGRES_DB_URL", "postgresql://user:password@localhost/dbname")

# Choose database URL based on environment
DATABASE_URL = SQLITE_DB_URL if ENV == "dev" else POSTGRES_DB_URL

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if ENV == "dev" else {},  # SQLite-specific argument
    pool_pre_ping=True,  # Ensures broken connections are checked and discarded
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()

# Create all tables in the database
def create_tables():
    Base.metadata.create_all(bind=engine)

# Dependency for getting the database session
def get_db():
    """
    Dependency to get the database session for FastAPI routes.
    Automatically closes the session after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
