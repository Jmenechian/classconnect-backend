from models.base import Base
from models.constants import COURSE_TABLE_NAME, SUBJECT_TABLE_NAME
from models.subject import Subject  # Import Subject model

from pydantic import BaseModel
from sqlalchemy import Integer, String, ForeignKey, JSON     
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import Optional, List
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json

class CourseBase(BaseModel):  # base without id for post
    """
    Basic model of a course
    """

    title: str
    description: str
    subject_id: int 
    quota: int = 30
    remaining_quota: int = quota
    date_start: Optional[datetime] = None
    date_finish: Optional[datetime] = None

    user_id: str  # ID of the user creating the course


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    quota: Optional[int] = None
    date_start: Optional[datetime] = None
    date_finish: Optional[datetime] = None


# Simulate how a full Course looks like
class CourseResponse(CourseBase):
    """
    Complete model of a course in the database
    """

    id: int


# Wrapper for the POST
class CourseResponseWrapper(BaseModel):
    """
    A full Course with a wrapper for the POST
    """

    data: CourseResponse


# Wrapper for the GET ALL
class CoursesResponseWrapper(BaseModel):
    """
    A full Course with a wrapper for the GET all
    """

    data: list[CourseResponse]


#Base = declarative_base()


class Course(Base):
    """
    Course model to be stored in the database
    """

    __tablename__ = COURSE_TABLE_NAME

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String)
    quota: Mapped[int] = mapped_column(Integer)
    remaining_quota: Mapped[int] = mapped_column(Integer)
    date_start: Mapped[datetime] = mapped_column(default=datetime.now())
    date_finish: Mapped[datetime] = mapped_column(default=lambda: datetime.now() + relativedelta(months=4))
    
    subject_id: Mapped[int] = mapped_column(ForeignKey(f"{SUBJECT_TABLE_NAME}.id"), default=None,nullable=True)
#    prerequisites: Mapped[List[int]] = mapped_column(JSON, default=list)
#    minimum_credits: Mapped[int] = mapped_column(Integer, default=0)

    user_id: Mapped[str] = mapped_column(String)
    
    subject: Mapped["Subject"] = relationship("Subject", back_populates="courses")
    enrollments: Mapped[List["Enrollment"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    modules: Mapped[List["Module"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    favourites = relationship("Favourite", back_populates="course", cascade="all, delete-orphan")

    enrollments : Mapped[List["Enrollment"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    modules : Mapped[List["Module"]]  = relationship(back_populates="course", cascade="all, delete-orphan")
    favourites = relationship("Favourite", back_populates="course", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="course", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="course", cascade="all, delete-orphan")