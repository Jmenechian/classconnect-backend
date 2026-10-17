from datetime import datetime
from typing import Any
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from controllers.enrollment_controller import get_user
from models.constants import AUXILIAR_TEACHER_ROLE
from models.enrollment import Enrollment
from models.event import EventBase, Event
from models.module import ModuleBase


def log_event(event: EventBase, db: Session):
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_logs_from_course(course_id: int, db: Session):

    events = db.query(Event).filter(Event.course_id == course_id).all()

    return events

def body_event(course_id, body, endpoint, user_id):
    full_name = get_name_from_user(user_id)

    def serialize(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: serialize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [serialize(item) for item in value]
        return value

    event = Event(
        course_id=course_id,
        teacher_full_name=full_name,
        event=endpoint,
        data=serialize(body.model_dump()),
        date=datetime.now()
    )

    return event

def no_body_event(course_id, endpoint: str, user_id: str):
    full_name = get_name_from_user(user_id)

    event = Event(
        course_id=course_id,
        teacher_full_name=full_name,
        event=endpoint,
        date=datetime.now()
    )

    return event

def get_name_from_user(user_id):
    name = "Unknown"
    surname = "User"
    user = get_user(user_id)
    if user and isinstance(user, dict):
        user_data = user.get("data", {})
        if isinstance(user_data, dict):
            name = user_data.get("name", "Unknown")
            surname = user_data.get("surname", "User")
    full_name = f"{name} {surname}"
    return full_name

