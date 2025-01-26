from app.services.db import engine, Base
from app.models import Trigger,EventLog

def initialize_database():
    print("Creating SQLite database and tables...")
    Base.metadata.create_all(bind=engine)
    print("Database and tables created successfully!")

if __name__ == "__main__":
    initialize_database()
