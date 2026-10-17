import os
import logging
import requests
import json

from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.constants import AUXILIAR_TEACHER_ENROLLMENT_NOTIFICATION_TITLE, AUXILIAR_TEACHER_ROLE, STUDENT_ENROLLMENT_NOTIFICATION_TITLE, STUDENT_ROLE
from models.correlative import Correlative
from models.course import Course
from models.enrollment import Enrollment, EnrollmentBase
from models.error import not_found_error, course_full_error, missing_prerequisites_error
from controllers.notification_controller import send_notification
from models.subject import Subject

USERS_URL = os.environ['DEV_USERS_URL'] if os.environ['ENVIRONMENT'] == 'development' else os.environ['MS_USERS_URL']

# Extra logger in case FastAPI is not enough
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

def student_can_enroll(user_id, course_id, db):
    '''
    Checks if student has all prerequisites for enroll into course. 
    PreReqs: All correlatives and minimum amount of credits 
    '''
    logging.info(f"student_can_enroll: Checking if {user_id} can enroll in {course_id}")

    # Correlatives
    subject_id = db.query(Course.subject_id).filter(Course.id == course_id).first()[0]
    correlative_rows = db.query(Correlative.correlative_id).filter(Correlative.subject_id == subject_id).all()
    correlative_ids = [row[0] for row in correlative_rows]

    if correlative_ids:
        logging.info(f"student_can_enroll: Correlatives required for subject {subject_id}")

        approved_subjects = db.query(Course.subject_id).join(Enrollment, Enrollment.course_id == Course.id).filter(
            Enrollment.user_id == user_id,
            Enrollment.status == "Approved",
            Course.subject_id.in_(correlative_ids)
        ).distinct().all()
        approved_subject_ids = [row[0] for row in approved_subjects]

        if not set(correlative_ids).issubset(set(approved_subject_ids)):
            logging.info(f"student_can_enroll: Student {user_id} does not meet all correlatives")
            return False
    else: 
        logging.info(f"student_can_enroll: NO correlatives required for subject {subject_id}")

    # Credits 
    minimum_credits = db.query(Subject.minimum_credits).filter(Subject.id == subject_id).first()[0]
    if minimum_credits == 0:
        logging.info(f"student_can_enroll: course {course_id} gots not credit requirements")
        return True

    total_credits = db.query(func.sum(Subject.credits))\
        .join(Course, Subject.id == Course.subject_id)\
        .join(Enrollment, and_(
            Enrollment.user_id == user_id,
            Enrollment.status == "Approved",
            Enrollment.course_id == Course.id
        )).scalar()

    logging.info(f"student_can_enroll: CREDITS DB QUERY OK")
    logging.info(f"student_can_enroll: {course_id} requires {minimum_credits}")
    logging.info(f"student_can_enroll: {user_id} gots {total_credits}")

    return (total_credits or 0) >= minimum_credits

def get_user_enrollments(user_id: str, db: Session):
    """
    Get user ENROLLMENTS (just user-course_id)
    """
    logging.info(f"Retrieving all Enrollments for user {user_id}")
    return db.query(Enrollment).filter_by(user_id=user_id).order_by(Enrollment.course_id.desc()).all()

def get_enrollment(user_id: str, course_id: int, db: Session):
    """
    Get user_id ENROLLMENT in course_id
    """
    logging.info(f"Retrieving Enrollment for user {user_id} in course {course_id}" )
    return db.query(Enrollment).filter_by(user_id=user_id, course_id=course_id).order_by(Enrollment.course_id.desc()).first()

def get_course_enrollments(course_id: int, db: Session):
    """
    Get users enrolled in course
    """
    logging.info(f"Retrieving all Enrollments for course {course_id}")
    data = []
    for enrollment in db.query(Enrollment).filter_by(course_id=course_id).order_by(Enrollment.user_id.desc()).all():
        user = get_user(enrollment.user_id)
        if not user is None:
            data_to_append = {
                "enrollment_id": enrollment.id,
                **user,
                "role": enrollment.role,
            }
            data.append(data_to_append)
    return data

def get_course_students(course_id: int, db: Session):
    students = get_course_enrollments(course_id=course_id,db=db)
#    print(students)
    return [ user["data"]["id"] for user in get_course_enrollments(course_id=course_id,db=db) if user["role"] == STUDENT_ROLE]    

def get_course_teachers(course_id: int, db: Session):
    return [ user["data"]["id"] for user in get_course_enrollments(course_id=course_id,db=db) if user["role"] != STUDENT_ROLE]    

def enroll_user(enroll: EnrollmentBase, role: str, db: Session): 
    """
    Persist user's course enrollment with role set to student
    """
    if db.query(Enrollment).filter_by(user_id=enroll.user_id, course_id=enroll.course_id).first():
        logging.info("User already enrolled")
        content = {"Error": "User already enrolled"}
        return JSONResponse(content=content, status_code=409)

    if check_user_exists(enroll.user_id):
        try:
            enrollment_data = enroll.model_dump()
            enrollment_data['role'] = role
            if role == STUDENT_ROLE:
                course = db.query(Course).filter_by(id=enroll.model_dump()['course_id']).first()
                if course:
                    if course.remaining_quota == 0:
                        logging.info(f"There's no more space in course {enroll.course_id} to enroll")
                        content = course_full_error()
                        return JSONResponse(content=content, status_code=409)
                    course.remaining_quota -= 1
                else:
                    logging.info(f"Course {enroll.course_id} not found")
                    content = not_found_error(detail="The requested course was not found on the server.",instance="/courses/enrollment")
                    return JSONResponse(status_code=404, content=content)

            if role == STUDENT_ROLE:
                enrollment_data['status'] = "In Progress"
            else:
                enrollment_data['status'] = "Not Student"

            if not student_can_enroll(enrollment_data['user_id'], enrollment_data['course_id'], db):
                logging.info(f"User {enroll.user_id} can't take course yet")
                content = missing_prerequisites_error()
                raise HTTPException(status_code=409,detail=content )
            
            db_enroll = Enrollment(**enrollment_data)
            db.add(db_enroll)
            db.commit()
            db.refresh(db_enroll)

            send_enrollment_notification(course_id=db_enroll.course_id,user_id=db_enroll.user_id,role=role,db=db)
            return {"data": db_enroll}
        except IntegrityError as e:
            db.rollback()
            logging.info(f"Integrity error while enrolling user {enroll.user_id} to course {enroll.course_id}")
            content=not_found_error(detail="The requested course was not found on the server.",instance=f"/courses/enrollment")
            return JSONResponse(status_code=404, content=content)
    else:
        logging.info(f"Integrity error while enrolling user {enroll.user_id} to course {enroll.course_id}")
        content=not_found_error(detail="The requested user was not found on the server.",instance=f"/courses/enrollment")
        return JSONResponse(status_code=404, content=content)

def approve_a_student(enrollment_id: int, db: Session):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()

    if not enrollment:
        logging.info(f"Enrollment {enrollment_id} not found")
        content = not_found_error("Enrollment not found", "/courses/enrollment/{enrollment_id}/approve")
        return JSONResponse(content=content, status_code=404)

    enrollment.status = "Approved"
    db.commit()
    db.refresh(enrollment)

    return {"Message": "Enrollment approved"}

def check_user_exists(user_id: str) -> bool:
    """
    Check in ms-users if the user exists
    """
    headers= {
        "content-type":"application/json",
        "Accept":"*/*"
    }
    url = USERS_URL + "/users/" + user_id
    try:
        return requests.get(url=url, headers=headers).status_code == 200
    except Exception as e:
        logging.error("Error check_user_exists", e)
        return False

def get_user(user_id: str) -> dict:
    '''
    Get user for ms-users
    '''
    headers= {
        "content-type":"application/json",
        "Accept":"*/*"
    }
    url = USERS_URL + "/users/" + user_id

    return json.loads(requests.get(url=url, headers=headers).text)

def get_user_enrollment_status(user_id: str, db: Session):
    return db.query(Enrollment).filter_by(user_id=user_id).all()

'''
def upgrade_to_auxiliar_teacher(course_id: int, user_id: str, db: Session):
    """
    Upgrade a student to auxiliar_teacher role
    """
    logging.info(f"Upgrading user {user_id} to auxiliar_teacher in course {course_id}")
    enrollment = db.query(Enrollment).filter_by(course_id=course_id, user_id=user_id).first()
    if not enrollment:
        content = not_found_error(detail="Enrollment not found", instance=f"/courses/{course_id}/enrollments/{user_id}")
        return JSONResponse(status_code=404, content=content)

    enrollment.role = AUXILIAR_TEACHER_ROLE
    db.commit()
    db.refresh(enrollment)
    return {"data": enrollment}

def downgrade_to_student(course_id: int, user_id: str, db: Session):
    """
    Downgrade an auxiliar_teacher to student role
    """
    logging.info(f"Downgrading user {user_id} to student in course {course_id}")
    enrollment = db.query(Enrollment).filter_by(course_id=course_id, user_id=user_id).first()
    if not enrollment:
        content = not_found_error(detail="Enrollment not found", instance=f"/courses/{course_id}/enrollments/{user_id}")
        return JSONResponse(status_code=404, content=content)

    if enrollment.role != AUXILIAR_TEACHER_ROLE:
        content = not_found_error(detail="User is not an auxiliar teacher", instance=f"/courses/{course_id}/enrollments/{user_id}")
        return JSONResponse(status_code=400, content=content)

    enrollment.role = STUDENT_ROLE
    db.commit()
    db.refresh(enrollment)
    return {"data": enrollment}
'''

def send_enrollment_notification(course_id: int, user_id: str, role: str, db: Session):
    course_title: str = db.query(Course.title).filter_by(id=course_id).first()
    
    metadata = {
        "course_id": str(course_id),
    }

    if role == STUDENT_ROLE:
        title: str = STUDENT_ENROLLMENT_NOTIFICATION_TITLE
        message: str = f"Successfully enrolled to {course_title[0]}"
        send_notification(title=title, message=message,users=[user_id], metadata=metadata)
    elif role == AUXILIAR_TEACHER_ROLE:
        title: str = AUXILIAR_TEACHER_ENROLLMENT_NOTIFICATION_TITLE
        message: str = f"Successfully enrolled as auxiliar teacher to {course_title[0]}"
        send_notification(title=title, message=message,users=[user_id], metadata=metadata)
    else:
        logging.warning("Uncatched notification case: tried to enroll not student nor auxiliar teacher")

def delete_enrolled_user(enroll: EnrollmentBase, db: Session):
    """
    Delete enrolled user
    """

    enroll = db.query(Enrollment).filter_by(course_id=enroll.course_id,user_id=enroll.user_id).first()
    if not enroll:
        content = not_found_error(detail="User not enrolled to course", instance="/courses/enrollments")
        return JSONResponse(status_code=404, content=content)

    course = db.query(Course).filter_by(id=enroll.course_id).first()
    if course and enroll.role == STUDENT_ROLE:
        course.remaining_quota += 1

    db.delete(enroll)
    db.commit()

    logging.info("Enrolled user deleted")
    return {"message": "Enrolled user deleted"}


def get_available_courses(user_id: str, db: Session):
    enrolled_course_ids = {e.course_id for e in db.query(Enrollment.course_id).filter(Enrollment.user_id == user_id).all()}

    all_courses = db.query(Course).all()

    available_courses = [
        course for course in all_courses
        if course.id not in enrolled_course_ids and student_can_enroll(user_id, course.id, db)
    ]

    return available_courses
