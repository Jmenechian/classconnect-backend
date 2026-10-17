from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from controllers.course_controller import (
    add_course,
    get_course_by_ID,
    delete_course_by_ID,
    update_a_course_by_ID,
    get_courses
)
from controllers.enrollment_controller import (
    enroll_user,
    get_enrollment,
    get_user_enrollment_status,
    get_user_enrollments,
    get_course_enrollments,
    #    upgrade_to_auxiliar_teacher,
    #    downgrade_to_student,
    delete_enrolled_user, approve_a_student, get_available_courses
)
from controllers.event_controller import log_event, get_logs_from_course, no_body_event, body_event
from controllers.favourite_controller import add_course_to_favourite, remove_course_from_favourites, \
    get_favourites_from_student, get_favourite_from_student_with_name
from controllers.feedback_controller import give_feedback_to_course_as_student, give_feedback_to_student_as_teacher, \
    get_all_feedback_from_course, get_all_feedback_from_student, get_all_feedback_from_course_summary, \
    get_all_feedback_from_student_summary
from controllers.module_controller import (
    add_module,
    create_documents,
    delete_resource_by_name,
    get_document,
    get_documents,
    get_modules,
    get_module_by_ID,    
    delete_module_by_ID
)
from controllers.exam_controller import (
    add_correction,
    add_exam,
    get_activities,
    get_activities_by_module,
    get_activity,
    get_exam,
    get_exams,
    get_exams_by_module,
    delete_exam_by_ID,
    get_exams_pending_correction,
    get_exams_pending_submission,
    get_submission,
    get_user_submissions,
    submit_exam
)
from controllers.stats_controller import get_global_stats, get_stats_by_course, get_stats_by_student
from controllers.subject_controller import create_a_subject, search_subject_by_name, search_subject_by_id, search_all_subjects
from controllers.token_verifier import verify_token, valid_permission
from controllers.utils import get_db
from models.constants import AUXILIAR_TEACHER_ROLE, STUDENT_ROLE
from models.course import (
    CourseBase,
    CourseResponseWrapper,
    CoursesResponseWrapper,
    CourseUpdate,
)
from models.document import DocumentBase, DocumentsResponseWrapper
from models.enrollment import (
    EnrollmentBase,
    EnrollmentListResponseWrapper,
    EnrollmentResponseWrapper,
)
from models.event import EventBase
from models.feedback import FeedbackBase
from models.module import (
    ModuleBase,
    ModuleResponseWrapper,
    ModulesResponseWrapper,
)
from models.responses import (
    ExamAndSubmissionWrapper,
    ExamResponseWrapper,
    ExamSubmissionResponseWrapper,
    ExamsResponseWrapper,
    SubjectResponseWrapper,
    SubjectsResponseWrapper,
)
from models.base import (
    CorrectionBase,
    ExamBase,
    ExamSubmissionBase
)
from datetime import datetime

from models.error import ErrorResponse
import logging

from models.subject import SubjectBase

router = APIRouter()

# Extra logger in case FastAPI is not enough
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Create course endpoint
@router.post("/courses/", status_code=201, response_model=CourseResponseWrapper)
def create_a_new_course(course: CourseBase, db: Session = Depends(get_db)):
    """
    Creates a new course, needs a title and description
    """
    logging.info("Creating a new course")
    return add_course(course, db)


# Get all courses endpoint
@router.get("/courses/", response_model=CoursesResponseWrapper)
def retrieve_courses(user_id: Optional[str] = None, db: Session = Depends(get_db), ):
    """
    Get courses
    If it gots variables, then it would filter by user_id
    """

    data = []
    if user_id is None:
        logging.info("Getting all courses")
        data = get_courses(db)
    else:
        logging.info(f"Getting courses of {user_id}")
        for course in get_user_enrollments(user_id=user_id,db=db):
            data.append(get_course_by_ID(id=course.course_id,db=db))
    return {"data":data}

# Get all courses endpoint
@router.get("/courses/enrollments/{user_id}", response_model=EnrollmentListResponseWrapper)
def retrieve_courses(user_id: str, db: Session = Depends(get_db), ):
    """
    Get all user enrollments 
    """
    return {"data":get_user_enrollment_status(user_id=user_id,db=db)}

# Get course enrollments
@router.get("/courses/{id}/enrollments", responses={200: {"model": CourseResponseWrapper}, 404: {"model": ErrorResponse}})
def retrieve_course_enrollments(id: int, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get a course by ID, error if not found
    """
    if user_id is None:
        return get_course_enrollments(course_id=id,db=db)
    else:
        return get_enrollment(course_id=id,user_id=user_id,db=db)
# Get course by ID
@router.get(
    "/courses/{id}",
    responses={200: {"model": CourseResponseWrapper}, 404: {"model": ErrorResponse}},
)
def retrieve_a_course_by_ID(id: int, db: Session = Depends(get_db)):
    """
    Get a course by ID, error if not found
    """
    return get_course_by_ID(id, db)

@router.put("/courses/{id}", response_model=CourseResponseWrapper)
def update_a_course(
    id: int, course_update: CourseUpdate, db: Session = Depends(get_db)
):


    return update_a_course_by_ID(id, course_update, db)

# Delete course by ID
@router.delete("/courses/{id}", responses={404: {"model": ErrorResponse}})
def delete_a_course_by_ID(id: int, db: Session = Depends(get_db)):
    """
    Deletes a course by ID, error if not found
    """
    return delete_course_by_ID(id, db)

# Enroll user
@router.post("/courses/enrollment", response_model=EnrollmentResponseWrapper)
def enroll_user_to_course(enroll_body: EnrollmentBase, db: Session = Depends(get_db) ):
    logging.info("Enrolling user to course")
    return enroll_user(enroll_body, STUDENT_ROLE, db)

#Enroll Auxiliar teacher
@router.post("/courses/enrollment/auxiliar_teacher", response_model=EnrollmentResponseWrapper)
def enroll_user_to_course(enroll_body: EnrollmentBase, db: Session = Depends(get_db) ):
    logging.info("Enrolling user to course as auxiliar teacher")
    return enroll_user(enroll_body, AUXILIAR_TEACHER_ROLE, db)

#Delete Enrolled user
@router.delete("/courses/enrollment/delete")
def delete_enrolled_user_on_course(enroll_body: EnrollmentBase, db: Session = Depends(get_db)):
    logging.info("Deleting enrolled user")
    return delete_enrolled_user(enroll_body, db)

@router.put("/courses/enrollment/{enrollment_id}/approve")
def approve_student(enrollment_id: int, db: Session = Depends(get_db)):
    logging.info("Approving enrolled user")
    return approve_a_student(enrollment_id, db)

# Create module
@router.post("/courses/modules", status_code=201, response_model=ModuleResponseWrapper)
def create_module(module: ModuleBase, db: Session = Depends(get_db), token: str = Header(..., convert_underscores=False)):
    """
    Creates a new module
    """

    user_id = verify_token(token)
    role = valid_permission(user_id, module.course_id, db)
    logging.info("Creating new module")

    try:
        result = add_module(module, db)
    except Exception as e:
        print("chau")
        raise e

    if role == AUXILIAR_TEACHER_ROLE:
        event = body_event(module.course_id, module, "/courses/modules", user_id)
        log_event(event, db)
    return result
# Get module
@router.get("/courses/{course_id}/modules", status_code=200,
            responses={200: {"model": ModulesResponseWrapper}, 404: {"model": ErrorResponse}})
def retrieve_modules(course_id: int, module_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Gets module
    """
    data = []
    if module_id is None:
        logging.info(f"Retrieving modules for course {course_id}")
        data = get_modules(course_id=course_id,db=db)
    else:
        logging.info(f"Retrieving module {module_id} for course {course_id}")
        data = [ get_module_by_ID(course_id=course_id,module_id=module_id,db=db) ] 
        
    return { "data": data }

# Delete module by ID
@router.delete("/courses/{course_id}/module/{id}", responses={404: {"model": ErrorResponse}})
def delete_a_module_by_ID(course_id: int, id: int,db: Session = Depends(get_db), token: str = Header(..., convert_underscores=False)):
    """
    Deletes a module by ID, error if not found
    """

    user_id = verify_token(token)
    role = valid_permission(user_id, course_id, db)
    logging.info(f"Delete module {id} of course {course_id}")

    try:
        result = delete_module_by_ID(course_id=course_id, module_id=id, db=db)
    except Exception as e:
        raise e

    if role == AUXILIAR_TEACHER_ROLE:
        endpoint = f"/courses/{course_id}/modules/{id}"
        event = no_body_event(course_id, endpoint, user_id)
        log_event(event, db)
    return result


# Resources 
@router.get("/courses/{course_id}/module/{module_id}/resources",     
            responses={200: {"model": DocumentsResponseWrapper}, 404: {"model": ErrorResponse}})
def retrieve_docs(course_id: int, module_id: int, document_name: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Retrieve document by ID, error if not found
    """
    if document_name:
        logging.info(f"Retrieving URL for doc {document_name}. Course {course_id} Module {module_id}")
        return { "data": get_document(course_id=course_id, module_id=module_id, document_name=document_name, db=db) }
    else:
        logging.info(f"Retrieving all docs for Course {course_id} Module {module_id}")
        return { "data": get_documents(course_id=course_id, module_id=module_id, db=db) }

# Resources 
@router.post("/courses/resources",     
            responses={200: {"model": DocumentsResponseWrapper}, 404: {"model": ErrorResponse}})
def retrieve_docs(document_body: DocumentBase, db: Session = Depends(get_db), token: str = Header(..., convert_underscores=False)):
    """
    Persist documents on backend
    """

    user_id = verify_token(token)
    role = valid_permission(user_id, document_body.course_id, db)
    logging.info(f"Persisting documents for Course {document_body.course_id} Module {document_body.module_id}")

    try:
        result = create_documents(document_body=document_body, db=db)
    except Exception as e:
        raise e

    if role == AUXILIAR_TEACHER_ROLE:
        endpoint = "/courses/resources"
        event = body_event(document_body.course_id, document_body, endpoint, user_id)
        log_event(event, db)
    return { "data": result }


@router.delete("/courses/{course_id}/module/{module_id}/resources/{resource_name}")     
def delete_document(course_id: int, module_id: int, resource_name: str, db: Session = Depends(get_db), token: str = Header(..., convert_underscores=False)):

    user_id = verify_token(token)
    role = valid_permission(user_id, course_id, db)
    logging.info(f"Delete resource {resource_name} of course {course_id} module {module_id}")

    try:
        result = delete_resource_by_name(resource_name=resource_name, course_id=course_id, module_id=module_id, db=db)
    except Exception as e:
        raise e

    if role == AUXILIAR_TEACHER_ROLE:
        endpoint = f"/courses/{course_id}/modules/{module_id}/resources/{resource_name}"
        event = no_body_event(course_id, endpoint, user_id)
        log_event(event, db)
    return result
 

# EXAMS 
@router.get("/courses/{course_id}/exams",     
            responses={200: {"model": ExamsResponseWrapper}, 404: {"model": ErrorResponse}})
def retrieve_exams(course_id: int, module_id: Optional[str] = None, exam_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get Exams
    """
    data = []
    if module_id is None:
        logging.info(f"Retrieve all exams of course {course_id}")
        data = get_exams(course_id=course_id,db=db)
    elif exam_id is None:
        logging.info(f"Retrieve all exams of course {course_id} for module {module_id}")
        data = get_exams_by_module(course_id=course_id,module_id=module_id,db=db)
    else:
        logging.info(f"Retrieve exam {exam_id} of course {course_id} for module {module_id}")
        data = [ get_exam(course_id=course_id,module_id=module_id,exam_id=exam_id,show_answer=False,show_activities=False,db=db) ]
    return {"data":data}

@router.get("/courses/{course_id}/activities",     
            responses={200: {"model": ExamsResponseWrapper}, 404: {"model": ErrorResponse}})
def retrieve_activities(course_id: int, module_id: Optional[str] = None, exam_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get Activities
    """
    data = []
    if module_id is None:
        logging.info(f"Retrieve all activities of course {course_id}")
        data = get_activities(course_id=course_id,db=db)
    elif exam_id is None:
        logging.info(f"Retrieve all activities of course {course_id} for module {module_id}")
        data = get_activities_by_module(course_id=course_id,module_id=module_id,db=db)
    else:
        logging.info(f"Retrieve activities {exam_id} of course {course_id} for module {module_id}")
        data = [ get_activity(course_id=course_id,module_id=module_id,exam_id=exam_id,show_answer=False,db=db) ]
    return {"data":data}

@router.post("/courses/exams", response_model=ExamResponseWrapper)
def create_exam(exam_body: ExamBase, db: Session = Depends(get_db), token: str = Header(..., convert_underscores=False)):
    # Se debe recibir un JSON con todos los datos del examen

    user_id = verify_token(token)
    role = valid_permission(user_id, exam_body.course_id, db)
    logging.info(f"Exam name: {exam_body.exam_name} Desc {exam_body.exam_description}")
    logging.info(f"Creating Exam for Course {exam_body.course_id} Module {exam_body.module_id}")

    try:
        result = add_exam(exam=exam_body, db=db)
    except Exception as e:
        raise e

    if role == AUXILIAR_TEACHER_ROLE:
        endpoint = f"/courses/exams"
        event = body_event(exam_body.course_id, exam_body, endpoint, user_id)
        log_event(event, db)
    return {"data": result }


# Delete Exam by ID
@router.delete("/courses/{course_id}/module/{module_id}/exam/{id}", responses={404: {"model": ErrorResponse}})
def delete_an_exam_by_ID(course_id: int, module_id: int, id: int,db: Session = Depends(get_db), token: str = Header(..., convert_underscores=False)):
    """
    Deletes a Exam by ID, error if not found
    """

    user_id = verify_token(token)
    role = valid_permission(user_id, course_id, db)
    logging.info(f"Delete exam {id} of course {course_id} module {module_id}")

    try:
        result = delete_exam_by_ID(exam_id=id, course_id=course_id, module_id=module_id, db=db)
    except Exception as e:
        raise e

    if role == AUXILIAR_TEACHER_ROLE:
        endpoint = f"/courses/{course_id}/module/{module_id}/exams/{id}"
        event = no_body_event(course_id, endpoint, user_id)
        log_event(event, db)
    return result

@router.post("/courses/submission", response_model=ExamSubmissionResponseWrapper)
def create_submission(submit_body: ExamSubmissionBase, db: Session = Depends(get_db) ):
    """
    Create exam submission
    """
    logging.info(f"Publishing Submission for for Course {submit_body.course_id} Module {submit_body.module_id} Exam {submit_body.exam_id}")
    return { "data": submit_exam(submit=submit_body, db=db) }

@router.get("/courses/{course_id}/exams/{user_id}/pending",     
            responses={200: {"model": ExamsResponseWrapper}, 404: {"model": ErrorResponse}})
def retrieve_pending_submission(course_id: int, user_id: int,module_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Get pending user submissions (Returns exam list)
    """
    return {"data":get_exams_pending_submission(course_id=course_id,module_id=module_id,user_id=user_id,isExam=True,db=db) }

@router.get("/courses/{course_id}/activities/{user_id}/pending",     
            responses={200: {"model": ExamsResponseWrapper}, 404: {"model": ErrorResponse}})
def retrieve_pending_submission(course_id: int, user_id: int,module_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Get pending user submissions (Returns activities list)
    """
    return {"data": get_exams_pending_submission(course_id=course_id,module_id=module_id,user_id=user_id,isExam=False,db=db) }

@router.get("/courses/{course_id}/exams/{user_id}",     
            responses={200: {"model": ExamsResponseWrapper}, 404: {"model": ErrorResponse}})
def retrieve_user_submission(course_id: int, user_id: int,module_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Get user submissions (Returns exam list)
    """
    return {"data": get_user_submissions(course_id=course_id,module_id=module_id,user_id=user_id,isExam=True,db=db) }

@router.get("/courses/{course_id}/activities/{user_id}",     
            responses={200: {"model": ExamsResponseWrapper}, 404: {"model": ErrorResponse}})
def retrieve_user_submission(course_id: int, user_id: int,module_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Get user submissions (Returns activities list)
    """
    return {"data": get_user_submissions(course_id=course_id,module_id=module_id,user_id=user_id,isExam=False,db=db) }

@router.get("/courses/{course_id}/corrections/pending",     
            responses={200: {"model": ExamsResponseWrapper}, 404: {"model": ErrorResponse}})
def retrieve_pending_submission(course_id: int, module_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Get submissions pending correction 
    """
    return get_exams_pending_correction(course_id=course_id,module_id=module_id,db=db)

@router.get("/courses/{course_id}/module/{module_id}/exam/{exam_id}/submission/{user_id}",     
            responses={200: {"model": ExamAndSubmissionWrapper}, 404: {"model": ErrorResponse}})
def retrieve_submission(course_id: int, module_id: int, exam_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Get submission for exam 
    Returns both responses and exam, for easing correction and information display. If corrected also returns points 
    """
    logging.info(f"Retrieving exam submission C{course_id} M{module_id} E{exam_id} U{user_id}")
    exam, submission = get_submission(course_id=course_id,module_id=module_id, exam_id=exam_id, user_id=user_id,db=db)
    return ExamAndSubmissionWrapper(exam=exam, submission=submission)

@router.post("/courses/corrections",     
            responses={200: {"model": ExamResponseWrapper}, 404: {"model": ErrorResponse}})
def correct_submission(correction: CorrectionBase, db: Session = Depends(get_db), token: str = Header(..., convert_underscores=False)):
    """
    POST: Correct exam submission
    """
    user_id = verify_token(token)
    role = valid_permission(user_id, correction.course_id, db)
    logging.info(f"Exam correction in progress")

    try:
        result = add_correction(correction=correction, using_AI = False, db=db)
    except Exception as e:
        raise e

    if role == AUXILIAR_TEACHER_ROLE:
        endpoint = f"/courses/corrections"
        event = body_event(correction.course_id, correction, endpoint, user_id)
        log_event(event, db)
    return result

'''
# Upgrade to auxiliar teacher
@router.put("/courses/{course_id}/enrollments/{user_id}/upgrade", response_model=EnrollmentResponseWrapper)
def upgrade_user_to_auxiliar_teacher(course_id: int, user_id: str, db: Session = Depends(get_db)):
    """
    Upgrade a student to auxiliar_teacher role
    """
    logging.info(f"Upgrading user {user_id} to auxiliar_teacher in course {course_id}")
    return upgrade_to_auxiliar_teacher(course_id, user_id, db)

# Downgrade to student
@router.put("/courses/{course_id}/enrollments/{user_id}/downgrade", response_model=EnrollmentResponseWrapper)
def downgrade_auxiliar_teacher_to_student(course_id: int, user_id: str, db: Session = Depends(get_db)):
    """
    Downgrade an auxiliar_teacher to student role
    """
    logging.info(f"Downgrading user {user_id} to student in course {course_id}")
    return downgrade_to_student(course_id, user_id, db)
'''

@router.get("/courses/stats/global")
def global_stats(db: Session = Depends(get_db)):
    logging.info(f"Getting global stats")
    return get_global_stats(db)

@router.get("/courses/{course_id}/stats")
def stats_by_course(course_id: int, date: Optional[datetime] = None, db: Session = Depends(get_db)):
    logging.info(f"Getting stats for course {course_id}")
    return get_stats_by_course(course_id, date, db)

@router.get("/courses/{course_id}/student/{user_id}/stats")
def stats_by_student(course_id: int, user_id: int, db: Session = Depends(get_db)):
    logging.info(f"Getting stats for student {course_id}")
    return get_stats_by_student(course_id, user_id, db)

@router.post("/courses/subjects/", responses={201: {"model": SubjectResponseWrapper}, 404: {"model": ErrorResponse}})
def create_subject(subject_body: SubjectBase, db: Session = Depends(get_db)):
    logging.info(f"Creating subject")
    return {"data":create_a_subject(subject_body, db)}

@router.get("/courses/subjects/", status_code=200, response_model=SubjectsResponseWrapper)
def search_subjects(title: Optional[str] = None, db: Session = Depends(get_db)):
    if title:
        logging.info(f"Searching subject by title {title}")
        return {"data":search_subject_by_name(title, db)}
    else:
        logging.info(f"Searching all subjects full")
        return {"data": search_all_subjects(db)}

@router.get("/courses/subjects/{subject_id}", responses={200: {"model": SubjectResponseWrapper}, 404: {"model": ErrorResponse}})
def search_subject_BY_ID(subject_id: int, db: Session = Depends(get_db)):
    logging.info(f"Searching subject {subject_id}")
    return {"data":search_subject_by_id(subject_id, db)}

@router.post("/courses/{course_id}/user/{user_id}/favourite/add")
def favourite_a_course(course_id: int, user_id: str, db: Session = Depends(get_db)):
    logging.info(f"Adding favourite course {course_id}")
    return add_course_to_favourite(course_id=course_id, user_id=user_id, db=db)

@router.delete("/courses/{course_id}/user/{user_id}/favourite/remove")
def unfavourite_a_course(course_id: int, user_id: str, db: Session = Depends(get_db)):
    logging.info(f"Removing favourite course {course_id}")
    return remove_course_from_favourites(course_id=course_id, user_id=user_id, db=db)

@router.get("/courses/user/{user_id}/favourite")
def get_favourites(user_id: str, db: Session = Depends(get_db)):
    logging.info(f"Getting favourites")
    return get_favourites_from_student(user_id=user_id, db=db)

@router.get("/courses/user/{user_id}/favourite/name/{course_name}")
def get_favourites_by_name(user_id: str, course_name: str, db: Session = Depends(get_db)):
    logging.info(f"Getting favourites by name {course_name}")
    return get_favourite_from_student_with_name(user_id=user_id, name=course_name, db=db)

@router.post("/courses/feedback/course")
def give_feedback_to_course(feedback: FeedbackBase, db: Session = Depends(get_db)):
    logging.info(f"Give feedback to course {feedback.course_id}")
    return give_feedback_to_course_as_student(feedback, db)
@router.post("/courses/feedback/student/")
def give_feedback_to_student(feedback: FeedbackBase, db: Session = Depends(get_db)):
    logging.info(f"Give feedback to student in {feedback.course_id}")
    return give_feedback_to_student_as_teacher(feedback, db)
@router.get("/courses/feedback/course/{course_id}/full")
def get_all_feedback(course_id: int, db: Session = Depends(get_db)):
    logging.info(f"Getting all feedback")
    return get_all_feedback_from_course(course_id, db)

@router.get("/courses/feedback/course/{course_id}/full/summary")
def get_all_feedback(course_id: int, db: Session = Depends(get_db)):
    logging.info(f"Getting all feedback")
    return get_all_feedback_from_course_summary(course_id, db)
@router.get("/courses/feedback/student/{user_id}/")
def get_all_student_feedback(user_id: str, db: Session = Depends(get_db)):
    logging.info(f"Getting all student feedback")
    return get_all_feedback_from_student(user_id=user_id, score=0, db=db)

@router.get("/courses/feedback/student/{user_id}/min_score/{min_score}")
def get_all_student_feedback_above_score(user_id: str, min_score: int, db: Session = Depends(get_db)):
    logging.info(f"Getting all student feedback above score")
    return get_all_feedback_from_student(user_id=user_id, score=min_score, db=db)

@router.get("/courses/feedback/student/{user_id}/summary")
def get_all_student_feedback(user_id: str, db: Session = Depends(get_db)):
    logging.info(f"Getting all student feedback")
    return get_all_feedback_from_student_summary(user_id, db)

@router.post("/courses/corrections/ai",
            responses={200: {"model": ExamResponseWrapper}, 404: {"model": ErrorResponse}})
def correct_submission(correction: CorrectionBase, db: Session = Depends(get_db)):
    logging.info(f"Exam correction in progress using AI")

    return add_correction(correction = correction,using_AI=True, db=db)

@router.get("/courses/log/{course_id}/")
def get_all_logs(course_id: int, db: Session = Depends(get_db)):
    logging.info(f"Getting all logs from course")
    return get_logs_from_course(course_id, db)

@router.get("/courses/available/user/{user_id}")
def get_available_courses_for_user(user_id: str, db: Session = Depends(get_db)):
    logging.info(f"Getting available courses for user {user_id}")
    return get_available_courses(user_id, db)

