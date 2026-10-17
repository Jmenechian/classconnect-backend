from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from models.base import QuestionType
from models.subject import SubjectBase


class QuestionOptionResponse(BaseModel):
    """
    Complete model of a course in the database
    """
    id: int
    option_text: str
    is_correct: bool = None      

# Wrapper for the POST
class QuestionOptionResponseWrapper(BaseModel):
    """
    A full Course with a wrapper for the POST
    """

    data: QuestionOptionResponse


# Wrapper for the GET ALL
class QuestionsOptionResponseWrapper(BaseModel):
    """
    A full Course with a wrapper for the GET all
    """

    data: list[QuestionOptionResponse]

class QuestionResponse(BaseModel):
    """
    Complete model of a course in the database
    """
    id: int
    question: str
    questionType: QuestionType
    points: int
    options: List[QuestionOptionResponse]

# Wrapper for the POST
class QuestionResponseWrapper(BaseModel):
    """
    A full Course with a wrapper for the POST
    """

    data: QuestionResponse


# Wrapper for the GET ALL
class QuestionsResponseWrapper(BaseModel):
    """
    A full Course with a wrapper for the GET all
    """

    data: list[QuestionResponse]


class ExamResponse(BaseModel):
    """
    Complete model of a course in the database
    """

    id: int = None
    course_id: int
    module_id: int 
    exam_name: str
    description: str
    submission_deadline: Optional[datetime] = None
    questions: Optional[List[QuestionResponse]] = None
    
# Wrapper for the POST
class ExamResponseWrapper(BaseModel):
    """
    A full Course with a wrapper for the POST
    """

    data: ExamResponse


# Wrapper for the GET ALL
class ExamsResponseWrapper(BaseModel):
    """
    A full Course with a wrapper for the GET all
    """

    data: list[ExamResponse]







class ResolutionOptionResponse(BaseModel):
    """
    Complete model of a ResolutionOption in the database
    """

    id: int

# Wrapper for the POST
class ResolutionOptionResponseWrapper(BaseModel):
    """
    A full ResolutionOption with a wrapper for the POST
    """

    data: ResolutionOptionResponse


# Wrapper for the GET ALL
class ResolutionsOptionResponseWrapper(BaseModel):
    """
    A full ResolutionOption with a wrapper for the GET all
    """

    data: list[ResolutionOptionResponse]

class ExamResolutionResponse(BaseModel):
    """
    Complete model of a course in the database
    """
    question_id: int
    answer: Optional[str] = None
    feedback: Optional[str] = None
    points_earned: Optional[int] = None
    options: Optional[list[ResolutionOptionResponse]] = None

class ExamSubmissionResponse(BaseModel):
    """
    Complete model of submission response
    """
    user_id: int
    course_id: int
    module_id: int 
    exam_id: int
    submitted_date: datetime
    corrected_date: Optional[datetime] = None
    general_feedback: Optional[str] = None
    points_earned: Optional[int] = None
    resolutions: list[ExamResolutionResponse] = None


# Wrapper for the POST
class ExamSubmissionResponseWrapper(BaseModel):
    """
    A full ExamResponseWrapper for the POST
    """

    data: ExamSubmissionResponse


# Wrapper for the GET ALL
class ExamSubmissionsResponseWrapper(BaseModel):
    """
    A full ExamResponseWrapper for the GET all
    """

    data: list[ExamSubmissionResponse]

# Wrapper for the POST
class ExamSubmissionResponseWrapper(BaseModel):
    """
    A full ExamResponseWrapper for the POST
    """

    data: ExamSubmissionResponse


# Wrapper for the GET ALL
class ExamsSubmissionResponseWrapper(BaseModel):
    """
    A full ExamResponseWrapper for the GET all
    """

    data: list[ExamSubmissionResponse]

class ExamAndSubmissionWrapper(BaseModel):
    exam: ExamResponse
    submission: ExamSubmissionResponse

class QuestionCorrectionResponse(BaseModel):
    earned_points: int
    question_points: int
    feedback: str 

class CorrectionResponse(ExamSubmissionResponse):
    total_earned_points: int
    total_question_points: int
    general_feedback: str
    options_responses: list[QuestionCorrectionResponse]



class SubjectResponseWrapper(BaseModel):
    """
    A full subject with a wrapper for the POST
    """

    data: SubjectBase


# Wrapper for the GET ALL
class SubjectsResponseWrapper(BaseModel):
    """
    A full subject with a wrapper for the GET all
    """

    data: list[SubjectBase]
