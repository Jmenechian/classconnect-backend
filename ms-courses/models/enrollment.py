from typing import List
from models.base import Base
from models.constants import COURSE_TABLE_NAME, ENROLLMENT_TABLE_NAME
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List

class EnrollmentBase(BaseModel):
    user_id: str = None
    course_id: int = None
    role: Optional[str] = None  # Making role optional since it will be set to 'student' anyway
    status: Optional[str] = "In Progress"

class Enrollment(Base):
    """
    Enrollment model to be stored in the database

    """
    __tablename__ = ENROLLMENT_TABLE_NAME

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True, unique=True)
    course_id: Mapped[int] = Column(ForeignKey(f"{COURSE_TABLE_NAME}.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(primary_key=True)   # From ms-users
    role: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    
    course: Mapped["Course"] = relationship(back_populates="enrollments")
    exam_submissions: Mapped[List["ExamSubmission"]] = relationship(back_populates="user", cascade="all, delete-orphan")    

class EnrollmentResponse(EnrollmentBase):
    """
    Complete model of a course in the database
    """

    id: int

class EnrollmentResponseWrapper(BaseModel):
    """
    A full Enrollment with a wrapper for the POST
    """

    data: EnrollmentResponse

class EnrollmentListResponseWrapper(BaseModel):
    """
    A list of Enrollments with a wrapper for the GET
    """

    data: list[EnrollmentResponse]

class TeacherResponse(BaseModel):
    id: str
    uid: str
    token: str
    name: Optional[str] = None
    surname: Optional[str] = None
    email: str
    country: Optional[str] = None
    role: str

class TeachersResponseWrapper(BaseModel):
    """
    A list of teachers with a wrapper for the GET
    """
    data: List[TeacherResponse]
