from pydantic import BaseModel

class ErrorResponse(BaseModel):
    """
    Pydantic model for the error response (for display in the UI purpose)
    """

    type: str
    title: str
    status: int
    detail: str
    instance: str


class Error:
    """
    Model for the error response
    """

    def __init__(self, type: str, title: str, status: int, detail: str, instance: str):
        """
        Initialize the error object
        """
        self.type = type
        self.title = title
        self.status = status
        self.detail = detail
        self.instance = instance

    def to_dict(self) -> dict:
        """
        returns the error object as a dictionary to send as a json response
        """
        return {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "instance": self.instance,
        }


def not_found_error(detail: str, instance: str):
    """
    Error in case course is not found in the database
    """
    error = Error(
        type="about:blank",
        title="Not Found",
        status=404,
        detail=detail,
        instance=instance,
    )
    return error.to_dict()

def missing_prerequisites_error():
    error = Error(
        type="about:blank",
        title="Missing Prerequisites",
        status=409,
        detail="Student does not meet the prerequisites to enroll in this course",
        instance="/courses/enrollment",
    )
    return error.to_dict()

def submission_deadline_pased():
    error = Error(
        type="about:blank",
        title="Missing Prerequisites",
        status=409,
        detail="Sorry, Submission deadline already passed. Please check with teaching staff",
        instance="/courses/submissions",
    )
    return error.to_dict()

def course_full_error():
    error = Error(
        type="about:blank",
        title="Course Full",
        status = 409,
        detail="Course is full",
        instance="/courses/enrollment",
    )
    return error.to_dict()

def subject_wrong_error():
    error = Error(
        type="about:blank",
        title="Subject Wrong Error",
        status = 409,
        detail="Subject is wrong",
        instance="/courses/",
    )
    return error.to_dict()