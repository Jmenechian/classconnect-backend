from datetime import datetime, timezone
from fastapi.exceptions import HTTPException
from controllers.notification_controller import send_notification
from models.constants import MAIN_TEACHER_ROLE
from models.course import CourseBase, Course, CourseUpdate
from models.error import not_found_error, course_full_error, subject_wrong_error
from models.enrollment import Enrollment
from sqlalchemy.orm import Session
import logging

from models.subject import Subject

# Extra logger in case FastAPI is not enough
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


def subject_exists(subject_id, db) -> bool:
    '''
    Checks if subject exists
    '''
    try:
        if db.query(Subject).filter(Subject.id == subject_id).first():
            return True
        else:
            return False
    except:
        return False

def add_course(course: CourseBase, db: Session):  # search how to detect invalid course
    """
    Adds a course to the database and enrolls the creator as main_teacher
    """
    # Create the course
    if course.date_finish.date() > course.date_start.date() >= datetime.now().date():
        if course.quota != course.remaining_quota:
            course.remaining_quota = course.quota

        if course.subject_id:
            if not subject_exists(course.subject_id, db):
                logging.info(f"Something wrong with subjects")
                raise HTTPException(status_code=409, detail=subject_wrong_error())

        db_course = Course(**course.model_dump())
        db.add(db_course)
        db.commit()
        db.refresh(db_course)

        # Create the enrollment for the creator as main_teacher
        creator_enrollment = Enrollment(
            course_id=db_course.id,
            user_id=course.user_id,
            role=MAIN_TEACHER_ROLE,  
            status="Creator"
        )
        db.add(creator_enrollment)
        db.commit()

        send_course_notification(course_title=course.title,user_id=course.user_id,course_id=db_course.id)
        return {"data": db_course}
    else:
        logging.info(f"Invalid dates. Start: {str(course.date_start)}  Finish: {str(course.date_finish)}")
        content = not_found_error(
            detail=f"Invalid dates. Start: {str(course.date_start)}  Finish: {str(course.date_finish)}",
            instance=f"/courses/"
        )
        raise HTTPException(status_code=400, detail=content)

def get_courses(db: Session):
    logging.info("Retrieving all courses")
    return db.query(Course).order_by(Course.id.desc()).all()

def get_course_by_ID(id: int, db: Session):
    """
    Get a course by ID, return if found, 404 error if not
    """
    db_course = db.query(Course).filter_by(id=id).first()
    if not db_course:
        logging.info(f"Course with id: {id} not found")
        content = not_found_error(
            detail="The requested Course was not found on the server.",
            instance=f"/courses/{id}"
        )
        raise HTTPException(status_code=404, detail=content)

    logging.info(f"Course with id: {id} found")
    return db_course


def update_a_course_by_ID(id: int, course_update: CourseUpdate, db: Session):
    db_course = db.query(Course).filter_by(id=id).first()
    if not db_course:
        logging.info(f"Course with id: {id} not found")
        content = not_found_error(
            detail="The requested Course was not found on the server.",
            instance=f"/courses/{id}"
        )
        raise HTTPException(status_code=404, detail=content)
    
    course_data = course_update.model_dump(exclude_unset=True)

    for field, value in course_data.items():
        setattr(db_course, field, value)

    db.commit()
    db.refresh(db_course)
    return {"data": db_course}


def delete_course_by_ID(id: int, db: Session):
    """
    Get a course by ID, return success message if found, 404 error if not
    """
    db_course = db.query(Course).filter_by(id=id).first()
    if not db_course:
        logging.info(f"Course with id: {id} not found")
        content = not_found_error(
            detail="The requested Course was not found on the server.",
            instance=f"/courses/{id}"
        )
        raise HTTPException(status_code=404, detail=content)

    db.delete(db_course)
    db.commit()

    logging.info(f"Course with id: {id} deleted")
    return {"message": "Course deleted successfully"}

def send_course_notification(course_title: int, user_id: str, course_id: int):
    title: str = "You made a new course!"
    message: str = f"Course \"{course_title}\" created successfully"
    metadata = {
        "course_id": str(course_id),
    }
    send_notification(title=title, message=message,users=[user_id], metadata=metadata)