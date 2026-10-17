from sqlalchemy.orm import Mapped
from sqlalchemy.testing.schema import mapped_column
from sqlalchemy.orm import relationship

from models.base import Base
from models.constants import SUBJECT_TABLE_NAME

from pydantic import BaseModel
from sqlalchemy import Integer, String
from typing import Optional, List

class SubjectBase(BaseModel):  # base without id for post
    """
    Basic model of a Subject
    """
    id: int = None
    title: str
    credits: Optional[int] = 0
    minimum_credits: Optional[int] = 0
    correlatives: Optional[List[int]] = None

class Subject(Base):
    """
    Subject model to be stored in the database
    """

    __tablename__ = SUBJECT_TABLE_NAME

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String)
    credits: Mapped[int] = mapped_column(Integer, default=4)
    minimum_credits: Mapped[int] = mapped_column(Integer, default=0)

    courses: Mapped[List["Course"]] = relationship(back_populates="subject")

    # Subjects this subject requires
    correlatives: Mapped[List["Correlative"]] = relationship(
        "Correlative",
        back_populates="subject",
        foreign_keys="[Correlative.subject_id]",
        cascade="all, delete-orphan"
    )

    # Subjects that require this subject
    required_by: Mapped[List["Correlative"]] = relationship(
        "Correlative",
        back_populates="correlative",
        foreign_keys="[Correlative.correlative_id]",
        cascade="all, delete-orphan"
    )