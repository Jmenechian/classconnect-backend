from datetime import datetime
from models.base import Base
from models.constants import MODULES_TABLE_NAME, EXAM_TABLE_NAME

from typing import List

from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Exam(Base):
    """
    Exam model to be stored in the database
    """
    __tablename__ = EXAM_TABLE_NAME

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    course_id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(primary_key=True)

    exam_name: Mapped[str] = mapped_column(nullable=False)
    exam_description: Mapped[str] = mapped_column(nullable=False)
    submission_deadline: Mapped[datetime] = mapped_column(nullable=True, default=None)
    isExam: Mapped[bool] = mapped_column(nullable=False, default=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["course_id", "module_id"],
            [f"{MODULES_TABLE_NAME}.course_id", f"{MODULES_TABLE_NAME}.id"],
            ondelete="CASCADE"
        ),
    )

    module: Mapped["Module"] = relationship("Module", back_populates="exams")
    questions: Mapped[List["Question"]] = relationship(back_populates="exam", cascade="all, delete-orphan")
    submissions: Mapped[List["ExamSubmission"]] = relationship(back_populates="exam", cascade="all, delete-orphan")
