from sqlalchemy import String, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class LayoutRecord(Base):
    __tablename__ = "layouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    warehouse_id: Mapped[str] = mapped_column(String, index=True)
    constraint_inputs:Mapped[dict] = mapped_column(JSON)        # The OptimizeRequest
    optimized_layout: Mapped[dict] = mapped_column(JSON)        # The Layout
    