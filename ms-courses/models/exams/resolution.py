from typing import List
from models.base import Base
from models.constants import EXAM_QUESTION_TABLE_NAME, EXAM_RESOLUTION_TABLE_NAME, EXAM_SUBMISSION_TABLE_NAME

from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

class ExamQuestionResolution(Base):
    """
    User ExamResolution model to be stored in the database
    """
    __tablename__ = EXAM_RESOLUTION_TABLE_NAME

    user_id:     Mapped[int] = mapped_column(primary_key=True)
    course_id:   Mapped[int] = mapped_column(primary_key=True)
    module_id:   Mapped[int] = mapped_column(primary_key=True)
    exam_id:     Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(primary_key=True)

    answer: Mapped[str]         = mapped_column(default=None, nullable=True) # Respuesta en texto ( utilizada para pregunta de respuesta unica o desarrollo)
    feedback: Mapped[str]       = mapped_column(default=None, nullable=True) # Feedback de la pregunta
    points_earned: Mapped[int]  = mapped_column(default=0)    # Puntos por la respuesta (automatico si es multiple choice, multiple answer o single value)

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id","course_id", "module_id", "exam_id"],
            [f"{EXAM_SUBMISSION_TABLE_NAME}.user_id", f"{EXAM_SUBMISSION_TABLE_NAME}.course_id", f"{EXAM_SUBMISSION_TABLE_NAME}.module_id", f"{EXAM_SUBMISSION_TABLE_NAME}.exam_id"],
            ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["question_id", "course_id", "module_id", "exam_id"],
            [f"{EXAM_QUESTION_TABLE_NAME}.id", f"{EXAM_QUESTION_TABLE_NAME}.course_id", f"{EXAM_QUESTION_TABLE_NAME}.module_id", f"{EXAM_QUESTION_TABLE_NAME}.exam_id"],
            ondelete="CASCADE"
        ),
    )

    submission: Mapped["ExamSubmission"] = relationship(back_populates="resolutions")
    question: Mapped["Question"] = relationship(back_populates="resolutions")
    resolution_options: Mapped[List["ResolutionOption"]] = relationship(back_populates="exam_resolution", cascade="all, delete-orphan")
