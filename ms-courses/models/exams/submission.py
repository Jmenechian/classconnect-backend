from typing import List
from models.base import Base
from models.constants import ENROLLMENT_TABLE_NAME, EXAM_TABLE_NAME, EXAM_SUBMISSION_TABLE_NAME

from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

class ExamSubmission(Base):
    """
    User ExamResolution model to be stored in the database
    Destinado a almacenar la metadata de la entrega del examen e indexar respuestas 
    """
    __tablename__ = EXAM_SUBMISSION_TABLE_NAME

    user_id:    Mapped[str] = mapped_column(ForeignKey(f"{ENROLLMENT_TABLE_NAME}.id", ondelete="CASCADE"), primary_key=True)
    module_id:  Mapped[int] = mapped_column(primary_key=True)
    course_id:  Mapped[int] = mapped_column(primary_key=True)
    exam_id:    Mapped[int] = mapped_column(primary_key=True)

    submitted_date: Mapped[datetime]    = mapped_column(default=datetime.now(), nullable=False)
    corrected_date: Mapped[datetime]         = mapped_column(default=None, nullable=True)
    general_feedback: Mapped[str]       = mapped_column(default=None, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["course_id", "module_id","exam_id"],
            [f"{EXAM_TABLE_NAME}.course_id", f"{EXAM_TABLE_NAME}.module_id",f"{EXAM_TABLE_NAME}.id"],
            ondelete="CASCADE"
        ),
    )

    user: Mapped["Enrollment"] = relationship(back_populates="exam_submissions")
    exam: Mapped["Exam"] = relationship(back_populates="submissions")
    resolutions: Mapped[List["ExamQuestionResolution"]] = relationship(back_populates="submission", cascade="all, delete-orphan")

