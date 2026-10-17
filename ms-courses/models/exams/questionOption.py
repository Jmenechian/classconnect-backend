from typing import List
from models.base import Base
from models.constants import EXAM_QUESTION_TABLE_NAME, EXAM_QUESTION_OPTIONS_TABLE_NAME
from models.exams.question import Question
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

class QuestionOption(Base):
    """
    Question Option model to be stored in the database

    """
    __tablename__ = EXAM_QUESTION_OPTIONS_TABLE_NAME

    # Identificación de la pregunta
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(primary_key=True)

    option_text: Mapped[str] = mapped_column(nullable=False)  # Texto de la opcion
    is_correct: Mapped[bool] = mapped_column(nullable=False)  # Correcta o incorrecta

    __table_args__ = (
        ForeignKeyConstraint(
            ["course_id", "module_id", "exam_id", "question_id"],
            [f"{EXAM_QUESTION_TABLE_NAME}.course_id", f"{EXAM_QUESTION_TABLE_NAME}.module_id", f"{EXAM_QUESTION_TABLE_NAME}.exam_id", f"{EXAM_QUESTION_TABLE_NAME}.id"],
            ondelete="CASCADE"
        ),
    )    

    chosen_options: Mapped[List["ResolutionOption"]] = relationship(back_populates="option", cascade="all, delete-orphan")
    question: Mapped["Question"] = relationship(back_populates="options")

