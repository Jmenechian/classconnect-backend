from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ResolutionOptionBase(BaseModel):
    id: int = None
    course_id: int = None
    module_id: int = None
    exam_id: int = None

class ExamQuestionResolutionBase(BaseModel):
    user_id:     int = None
    module_id:   int = None
    course_id:   int = None
    exam_id:     int = None
    question_id: int
    answer: str
    options_chosen: list[ResolutionOptionBase] = None

class ExamSubmissionBase(BaseModel):
    user_id:     int
    module_id:   int
    course_id:   int
    exam_id:     int
    answered_questions: list[ExamQuestionResolutionBase] 

class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    MULTIPLE_ANSWER = "MULTIPLE_ANSWER"
    SINGLE_VALUE = "SINGLE_VALUE"
    TEXT_ANSWER = "TEXT_ANSWER"

class ExamBase(BaseModel):
    id: int = None
    course_id: int
    module_id: int
    exam_name: str
    exam_description: str
    submission_deadline: Optional[datetime] = None
    isExam: Optional[bool] = True
    questions: list[QuestionBase] = None

class QuestionBase(BaseModel):
    id: int = None
    course_id: int = None
    module_id: int = None
    exam_id: int = None
    question: str 
    questionType: QuestionType 
    points: int      
    options: list[QuestionOptionBase] = None

class QuestionOptionBase(BaseModel):
    id: int = None
    course_id: int = None
    module_id: int = None
    exam_id: int = None 
    question_id: int = None
    option_text: str
    is_correct: bool

class QuestionCorrectionBase(BaseModel):
    question_id: int 
    feedback: str
    points_earned: int

class CorrectionBase(BaseModel):
    course_id: int
    module_id: int
    exam_id: int
    user_id: int
    general_feedback: str = None
    questions_feedback: list[QuestionCorrectionBase]

class CorrectionReducedBase(BaseModel):
    course_id: int
    module_id: int
    exam_id: int
    user_id: int