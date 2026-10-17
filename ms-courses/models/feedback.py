from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.constants import COURSE_TABLE_NAME, FEEDBACKS_TABLE_NAME

class FeedbackBase(BaseModel):

    course_id: int
    user_id: str
    teacher_id: Optional[str] = None
    target: Optional[str] = None
    comment: str
    score: int

class Feedback(Base):
    """
    Feedback model to be stored in the database
    """
    __tablename__ = FEEDBACKS_TABLE_NAME

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True, unique=True)
    course_id: Mapped[int] = Column(ForeignKey(f"{COURSE_TABLE_NAME}.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(primary_key=True)   # From ms-users
    teacher_id: Mapped[str] = mapped_column(nullable=True)
    target: Mapped[str] = mapped_column(primary_key=True)
    score: Mapped[int] = mapped_column(primary_key=True)
    comment: Mapped[str] = mapped_column()

    course: Mapped["Course"] = relationship(back_populates="feedbacks")
