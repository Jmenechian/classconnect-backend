from models.base import Base
from models.exams.exam import Exam
from models.constants import EXAM_TABLE_NAME, EXAM_QUESTION_TABLE_NAME

from typing import List
from enum import Enum

from sqlalchemy import ForeignKeyConstraint, Enum as EnumDB
from sqlalchemy.orm import Mapped, mapped_column, relationship

MULTIPLE_CHOICE_VALUE = "MULTIPLE_CHOICE"
MULTIPLE_ANSWER_VALUE = "MULTIPLE_ANSWER"
SINGLE_VALUE_VALUE = "SINGLE_VALUE"   
TEXT_ANSWER_VALUE = "TEXT_ANSWER"    

class QuestionType(str, Enum):
    MULTIPLE_CHOICE = MULTIPLE_CHOICE_VALUE     # A, B, C o D (una sola opcion)
    MULTIPLE_ANSWER = MULTIPLE_ANSWER_VALUE     # Mas de una respuesta correcta
    SINGLE_VALUE = SINGLE_VALUE_VALUE           # Sin opciones, pregunta con respuesta sintetica ( 1 + 1 = ? -> Se debe almacenar un numero )
    TEXT_ANSWER = TEXT_ANSWER_VALUE             # Pregunta a desarrollar
    
class Question(Base):
    """
    Question model to be stored in the database

    """
    __tablename__ = EXAM_QUESTION_TABLE_NAME

    # Identificación de la pregunta
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(primary_key=True)

    question: Mapped[str] = mapped_column(nullable=False)                                       # Texto de la pregunta
    questionType: Mapped[QuestionType] = mapped_column(EnumDB(QuestionType), nullable=False)    # Tipo de pregunta (indica si tiene opciones o no)
    points: Mapped[int] = mapped_column(nullable=False)                                         # Puntos de la pregunta

    __table_args__ = (
        ForeignKeyConstraint(
            ["course_id", "module_id", "exam_id"],
            [f"{EXAM_TABLE_NAME}.course_id", f"{EXAM_TABLE_NAME}.module_id", f"{EXAM_TABLE_NAME}.id"],
            ondelete="CASCADE"
        ),
    )    

    exam: Mapped["Exam"] = relationship(back_populates="questions" )
    options: Mapped[List["QuestionOption"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    resolutions: Mapped[List["ExamQuestionResolution"]] = relationship(back_populates="question", cascade="all, delete-orphan")
