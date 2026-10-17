from sqlalchemy import and_

from models.course import Course
from models.favourite import Favourite
from sqlalchemy.orm import Session
from fastapi.exceptions import HTTPException

def add_course_to_favourite(course_id: int, user_id: str, db: Session):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    existing = db.query(Favourite).filter_by(course_id=course_id, user_id=user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Course already in favourites")

    favourite = Favourite(course_id=course_id, user_id=user_id)
    db.add(favourite)
    db.commit()
    db.refresh(favourite)
    return {"message": "Course added to favourites", "favourite": favourite.id}


def remove_course_from_favourites(course_id: int, user_id: str, db: Session):
    favourite = db.query(Favourite).filter_by(course_id=course_id, user_id=user_id).first()
    if not favourite:
        raise HTTPException(status_code=404, detail="Favourite not found")

    db.delete(favourite)
    db.commit()
    return {"message": "Course removed from favourites"}

def get_favourites_from_student(user_id: str, db: Session):
    course_ids = (db.query(Favourite.course_id).filter(Favourite.user_id == user_id).subquery())

    return db.query(Course).filter(Course.id.in_(course_ids)).all()

def get_favourite_from_student_with_name(user_id: str, name: str, db: Session):
    course_ids = (db.query(Favourite.course_id).filter(Favourite.user_id == user_id).subquery())

    courses = db.query(Course).filter(and_(Course.id.in_(course_ids),Course.title.ilike(f"%{name}%"))).all()

    return courses



