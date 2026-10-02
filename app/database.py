import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shelfsense.db")

# Neon (and Heroku, and Render) hand out "postgresql://..." or "postgres://...".
# SQLAlchemy reads that as "use psycopg2", which we don't install -- point it
# at psycopg 3 so the connection string can be pasted in verbatim.
for prefix in ("postgresql://", "postgres://"):
    if DATABASE_URL.startswith(prefix):
        DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len(prefix):]
        break

IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    # Neon autosuspends an idle database; without this the first query after a
    # sleep hits a dead pooled socket and raises instead of reconnecting.
    pool_pre_ping=not IS_SQLITE,
)

SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
