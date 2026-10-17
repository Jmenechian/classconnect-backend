import logging
import requests
from fastapi import HTTPException

from controllers.enrollment_controller import USERS_URL
from models.constants import AUXILIAR_TEACHER_ROLE, MAIN_TEACHER_ROLE
from models.enrollment import Enrollment
from sqlalchemy.orm import Session


def verify_token(token: str):
    """
    Verify a token by calling the auth service.
    Raises an exception if the request fails.
    Returns user_id if valid
    """

    logging.info(f"TOKEN RECEIVED FROM USER: {token}")

    headers = {
        "Token": token,
        "Accept": "application/json"
    }
    url = USERS_URL + "/auth/verify"
    response = requests.get(url, headers=headers)
    result = response.json()

    if "data" not in result:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return result["data"]["id"]

def valid_permission(user_id: str, course_id: int, db: Session):
    role = db.query(Enrollment.role).filter((Enrollment.user_id == user_id) & (Enrollment.course_id == course_id)).scalar()

    if role not in {MAIN_TEACHER_ROLE, AUXILIAR_TEACHER_ROLE}:
        raise HTTPException(status_code=403, detail="Unauthorized")

    return role