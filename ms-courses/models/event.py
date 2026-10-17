from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from models.base import Base
from models.constants import COURSE_TABLE_NAME, EVENTS_TABLE_NAME
from typing import Optional, Dict, Any
from sqlalchemy.dialects.postgresql import JSON


class EventBase(BaseModel):

    course_id: int
    teacher_full_name: str
    event: str
    data: Optional[Dict[str, Any]] = None
    date: Optional[datetime] = None

class Event(Base):
    """
    Event model to be stored in the database
    """
    __tablename__ = EVENTS_TABLE_NAME

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True, unique=True)
    course_id: Mapped[int] = Column(ForeignKey(f"{COURSE_TABLE_NAME}.id", ondelete="CASCADE"), primary_key=True)
    teacher_full_name: Mapped[str] = mapped_column(primary_key=True)   # From ms-users
    event: Mapped[str] = mapped_column(nullable=True)
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Stores JSON body if any
    date: Mapped[datetime] = mapped_column(default=datetime.now())

    course: Mapped["Course"] = relationship(back_populates="events")
