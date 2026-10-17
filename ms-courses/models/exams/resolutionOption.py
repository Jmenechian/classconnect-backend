from models.base import Base
from models.constants import ENROLLMENT_TABLE_NAME, EXAM_QUESTION_OPTIONS_TABLE_NAME, EXAM_QUESTION_TABLE_NAME, EXAM_RESOLUTION_OPTIONS_TABLE_NAME, EXAM_RESOLUTION_TABLE_NAME
from pydantic import BaseModel
from sqlalchemy import Column, ForeignKeyConstraint, Integer, String, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

class ResolutionOptionBase(BaseModel):
    id: int = None
    course_id: int
    module_id: int
    exam_id: int
    question: str
    points: int      

class ResolutionOption(Base):
    """
    Question Option model to be stored in the database

    """
    __tablename__ = EXAM_RESOLUTION_OPTIONS_TABLE_NAME

    # Identificación de la respuesta de la opcion
    user_id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(primary_key=True)
    option_id: Mapped[int] = mapped_column(primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id","course_id", "module_id", "exam_id", "question_id"],
            [f"{EXAM_RESOLUTION_TABLE_NAME}.user_id", f"{EXAM_RESOLUTION_TABLE_NAME}.course_id", f"{EXAM_RESOLUTION_TABLE_NAME}.module_id", f"{EXAM_RESOLUTION_TABLE_NAME}.exam_id", f"{EXAM_RESOLUTION_TABLE_NAME}.question_id"],
            ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["question_id", "course_id", "module_id", "exam_id"],
            [f"{EXAM_QUESTION_TABLE_NAME}.id", f"{EXAM_QUESTION_TABLE_NAME}.course_id", f"{EXAM_QUESTION_TABLE_NAME}.module_id", f"{EXAM_QUESTION_TABLE_NAME}.exam_id"],
            ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["option_id","question_id", "course_id", "module_id", "exam_id"],
            [f"{EXAM_QUESTION_OPTIONS_TABLE_NAME}.id",f"{EXAM_QUESTION_OPTIONS_TABLE_NAME}.question_id", f"{EXAM_QUESTION_OPTIONS_TABLE_NAME}.course_id", f"{EXAM_QUESTION_OPTIONS_TABLE_NAME}.module_id", f"{EXAM_QUESTION_OPTIONS_TABLE_NAME}.exam_id"],
            ondelete="CASCADE"
        ),
    )

    # Si existe entrada en esta tabla, significa que el alumno eligio esta opción como verdadera
    # La aplicación debe encargarse de no introducir inconsistencias ( ejemplo: Seleccion multiple con más de una respuesta correcta )
    exam_resolution: Mapped["ExamQuestionResolution"] = relationship(back_populates="resolution_options")
    option: Mapped["QuestionOption"] = relationship(back_populates="chosen_options")

class ResolutionOptionResponse(ResolutionOptionBase):
    """
    Complete model of a course in the database
    """

    id: int

# Wrapper for the POST
class ResolutionOptionResponseWrapper(BaseModel):
    """
    A full Course with a wrapper for the POST
    """

    data: ResolutionOptionResponse


# Wrapper for the GET ALL
class ResolutionsOptionResponseWrapper(BaseModel):
    """
    A full Course with a wrapper for the GET all
    """

    data: list[ResolutionOptionResponse]
