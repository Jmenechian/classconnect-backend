from models.base import Base
from models.constants import COURSE_TABLE_NAME, MODULES_TABLE_NAME

from typing import List
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ModuleBase(BaseModel):
    id: int = None
    course_id: int
    module_name: str
    module_description: str

class Module(Base):
    """
    Module model to be stored in the database

    """
    __tablename__ = MODULES_TABLE_NAME

    # Modulos es una entidad débil de cursos 
    # Todos los cursos tendran modulo 0 (datos generales del curso) y modulo (1..N) que seran especificos 
    # Un modulo se identifica de forma absoluta por medio de: course_id, id 
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    course_id: Mapped[int] = Column(Integer, ForeignKey(f"{COURSE_TABLE_NAME}.id", ondelete="CASCADE"), primary_key=True, index=True)
    module_name: Mapped[str] = mapped_column(nullable=False)
    module_description: Mapped[str] = mapped_column(nullable=False)

    # Materiales del modulo
    # Se almacenaran como JSONs tal de ser lo mas flexible posibles 
    educational_material: Mapped[dict[str, str]] = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default=None)   # Docs: pdfs, videos, etc. 
    learning_activities: Mapped[dict[str, str]] = mapped_column(JSON, nullable=True, default=None)    
    additional_stuff: Mapped[list[str]] = mapped_column(JSON, nullable=True, default=None)       

    course: Mapped["Course"] = relationship(back_populates="modules")
    exams: Mapped[List["Exam"]] = relationship(back_populates="module", cascade="all, delete-orphan", primaryjoin="and_(Module.id == Exam.module_id, Module.course_id == Exam.course_id)")

class ModuleResponse(ModuleBase):
    """
    Complete model of a course in the database
    """

    id: int
    course_id: int = None

# Wrapper for the POST
class ModuleResponseWrapper(BaseModel):
    """
    A full Course with a wrapper for the POST
    """

    data: ModuleBase


# Wrapper for the GET ALL
class ModulesResponseWrapper(BaseModel):
    """
    A full Course with a wrapper for the GET all
    """

    data: list[ModuleBase]
