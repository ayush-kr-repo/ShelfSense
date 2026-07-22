from sqlalchemy import String, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy import String, Integer, JSON, DateTime, ForeignKey

class LayoutRecord(Base):
    __tablename__ = "layouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    warehouse_id: Mapped[str] = mapped_column(String, index=True)
    constraint_inputs:Mapped[dict] = mapped_column(JSON)        # The OptimizeRequest
    optimized_layout: Mapped[dict] = mapped_column(JSON)        # The Layout
    
class TaskRecord(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer,primary_key=True, autoincrement=True)
    warehouse_id: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String, nullable=True )

class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class WarehouseRecord(Base):
    __tablename__="warehouses"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    image_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))