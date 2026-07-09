from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# The connection string : "talk SQLite, to the file ./shelfsense.db"
engine = create_engine("sqlite:///.shelfsense.db",
                       connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass