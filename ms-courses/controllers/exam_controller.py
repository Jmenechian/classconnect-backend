import os
from datetime import datetime
from typing import Optional
from fastapi.exceptions import HTTPException
from sqlalchemy import or_, not_
from controllers.enrollment_controller import get_course_students, get_course_teachers
from controllers.notification_controller import send_notification
from models.constants import ACTIVITY_CREATION_NOTIFICATION_TITLE, ACTIVITY_SUBMISSION_NOTIFICATION_TITLE, EXAM_CORRECTION_NOTIFICATION_TITLE, ACTIVITY_CORRECTION_NOTIFICATION_TITLE, EXAM_CREATION_NOTIFICATION_TITLE, EXAM_OR_ACTIVITY_CREATION_NOTIFICATION_TITLE, EXAM_SUBMISSION_NOTIFICATION_TITLE
from models.course import Course
from models.enrollment import Enrollment
from models.exams.question import TEXT_ANSWER_VALUE, Question
from models.exams.questionOption import QuestionOption
from models.exams.exam import Exam
from models.exams.resolution import ExamQuestionResolution
from models.exams.resolutionOption import ResolutionOption
from models.exams.submission import ExamSubmission
from models.responses import ExamResolutionResponse, ExamResponse, QuestionOptionResponse, QuestionResponse, ExamSubmissionResponse, ResolutionOptionResponse
from models.base import CorrectionBase, ExamBase, ExamQuestionResolutionBase, ExamSubmissionBase, QuestionType, \
    ResolutionOptionBase, CorrectionReducedBase, QuestionCorrectionBase
from models.error import not_found_error, submission_deadline_pased
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload

from controllers.module_controller import get_module_by_ID
from controllers.course_controller import get_course_by_ID
from sqlalchemy.orm import Session
import logging
import google.generativeai as genai
import ast

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "_")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash")

def call_ai_model(prompt: str): #falta tal vez hacer los strip/format aca
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        return content

    except Exception as e:
        raise RuntimeError(f"Error al llamar al modelo de IA: {e}")

# Extra logger in case FastAPI is not enough
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

def add_exam(exam: ExamBase, db: Session):  # search how to detect invalid course
    """
    Adds exam to the database
    """
    try:        
        model = exam.model_dump()
        model.pop("questions", None) 
        db_exam = Exam(**model)
        
        if db.in_transaction():
            # If already in transaction, just add and flush
            logging.info(f"Adding exam (existing transaction)")
            db.add(db_exam)
            db.flush() 

            if exam.questions:
                for question in exam.questions:
                    logging.info(f"Adding question")

                    model = question.model_dump()
                    model.pop("options")

                    db_question = Question(**model)
                    db_question.course_id = db_exam.course_id
                    db_question.module_id = db_exam.module_id
                    db_question.exam_id = db_exam.id
                    db.add(db_question)
                    db.flush() 

                    if question.options:
                        for option in question.options:
                            logging.info(f"Adding question option")
                            db_question_option = QuestionOption(**option.model_dump())
                            db_question_option.course_id = db_question.course_id
                            db_question_option.module_id = db_question.module_id
                            db_question_option.exam_id = db_question.exam_id
                            db_question_option.question_id = db_question.id
                            db.add(db_question_option)
            
            # Commit the transaction since we're managing it manually
            db.commit()
        else:
            # Start new transaction
            with db.begin():
                logging.info(f"Adding exam (new transaction)")
                db.add(db_exam)
                db.flush() 

                if exam.questions:
                    for question in exam.questions:
                        logging.info(f"Adding question")

                        model = question.model_dump()
                        model.pop("options")

                        db_question = Question(**model)
                        db_question.course_id = db_exam.course_id
                        db_question.module_id = db_exam.module_id
                        db_question.exam_id = db_exam.id
                        db.add(db_question)
                        db.flush() 

                        if question.options:
                            for option in question.options:
                                logging.info(f"Adding question option")
                                db_question_option = QuestionOption(**option.model_dump())
                                db_question_option.course_id = db_question.course_id
                                db_question_option.module_id = db_question.module_id
                                db_question_option.exam_id = db_question.exam_id
                                db_question_option.question_id = db_question.id
                                db.add(db_question_option)
                        
        exam = db.query(Exam).filter_by(id=db_exam.id, course_id=db_exam.course_id, module_id=db_exam.module_id).first()
        send_exam_notification(exam=exam,db=db)        

        return ExamResponse(id=exam.id, course_id=exam.course_id, module_id=exam.module_id, exam_name=exam.exam_name, description=exam.exam_description)

    except IntegrityError as e:
        logging.error(f"IntegrityError in add_exam: {str(e)}")
        content = not_found_error(
            detail=f"Integrity error: {str(e)}",
            instance=f"/courses/exams"
        )
        raise HTTPException(status_code=404, detail=content)
    except SQLAlchemyError as e:
        logging.error(f"SQLAlchemyError in add_exam: {str(e)}")
        content = not_found_error(
            detail=f"Database error: {str(e)}",
            instance=f"/courses/exams"
        )
        raise HTTPException(status_code=500, detail=content)
    
    except Exception as e:
        logging.error(f"Uncatched error in add_exam: {str(e)}")
        content = not_found_error(
            detail=f"Database error: {str(e)}",
            instance=f"/courses/exams"
        )
        raise HTTPException(status_code=500, detail=content)

def add_correction(correction: CorrectionBase, using_AI: bool, db: Session):
    '''
    Adds correction to database    
    Assumes valid input. Teacher could modify auto corrections
    '''
    # Get para Confirmar que exista submission ( ante error HTTP Exception )  
    exam, submission = get_submission(course_id=correction.course_id, module_id=correction.module_id, exam_id=correction.exam_id, user_id=correction.user_id, db=db )

    if using_AI:
        correction = generate_ai_correction(exam, submission)
    try:
        
        db_submission = (  # Consultamos la respuesta del alumno al examen, agregando preguntas y opciones
            db.query(ExamSubmission)
            .filter_by(course_id=correction.course_id,module_id=correction.module_id,exam_id=correction.exam_id, user_id=correction.user_id)
            .options(
                joinedload(ExamSubmission.resolutions).joinedload(ExamQuestionResolution.resolution_options)
            )
            .first()
        )    

        db_exam = (
            db.query(Exam)
            .filter_by(course_id=correction.course_id, module_id=correction.module_id, id=correction.exam_id)
            .options(
                joinedload(Exam.questions)
            )
            .first()
        )

        # Add teacher corrections-feedback
        for question_feedback in correction.questions_feedback:
            res = next(
                (r for r in db_submission.resolutions if r.question_id == question_feedback.question_id),
                None
            )
            if res:
                logging.info(f"Adding feedback for question {question_feedback.question_id}")
                res.points_earned = question_feedback.points_earned
                res.feedback = question_feedback.feedback        
        db_submission.general_feedback = correction.general_feedback
        # If no other manual question is pending, mark exam as correct
        index = 0
        pending_questions_for_correction = False
        while index < len(db_exam.questions) and not pending_questions_for_correction:
            if db_exam.questions[index].questionType == QuestionType.TEXT_ANSWER:
                pending_questions_for_correction = not db_exam.questions[index].id in [ q.question_id for q in correction.questions_feedback ]
            index += 1

        if not pending_questions_for_correction:
            db_submission.corrected_date = datetime.now()

        db.commit()

        send_correction_notification(exam=db_exam,auto_correct=False,user_id=db_submission.user_id,db=db)

        return ExamResponse(id=exam.id, course_id=exam.course_id, module_id=exam.module_id, exam_name=exam.exam_name, description=exam.description)

    except IntegrityError as e:
        db.rollback()
        content = not_found_error(
            detail="Integrity error, check input.",
            instance=f"/courses/corrections"
        )
        raise HTTPException(status_code=404, detail=content)
    except SQLAlchemyError as e:
        db.rollback()
        content = not_found_error(
            detail=f"Database error: {str(e)}",
            instance=f"/courses/corrections"
        )
        raise HTTPException(status_code=500, detail=content)
    
    except Exception as e:
        logging.error(f"Uncatched error {str(e)}")
        db.rollback()
        content = not_found_error(
            detail=f"Uncatched error: {str(e)}",
            instance=f"/courses/corrections"
        )
        raise HTTPException(status_code=500, detail=content)

def generate_ai_correction(exam, submission) -> CorrectionBase:
    """
    Usa IA para generar correcciones (puntaje + feedback) para respuestas de tipo TEXT_ANSWER.
    """
    questions_feedback = []

    for question in exam.questions:
        if question.questionType == QuestionType.TEXT_ANSWER:
            resolution = next(
                (r for r in submission.resolutions if r.question_id == question.id),
                None
            )
            if not resolution:
                continue

            prompt = f""" 
            Pregunta: {question.question}
            Respuesta del alumno: {resolution.answer}

            Asigná un puntaje entre 0 y {question.points} y da feedback breve.

            Respondé **solo con un diccionario de Python** (no JSON), así:

            {{'points_earned': número, 'feedback': 'comentario'}}
            """

            #buena prompt, parece andar
            ai_response = call_ai_model(prompt)

            #clear para que quede formato, ojo rompe si prompt la tira mal
            clean = ai_response.strip("```")
            if clean.startswith("python"):
                clean = clean[len("python"):]
            data = ast.literal_eval(clean)
            puntos = data['points_earned']
            feedback = data['feedback']

            ##reemplazamos con datos de la ia
            questions_feedback.append(QuestionCorrectionBase(
                question_id=question.id,
                points_earned=puntos,
                feedback=feedback
            ))

            # Feedback general del examen
    general_prompt = f"""
        Sos un docente. El alumno respondió las siguientes preguntas de un examen. Dame un feedback general (positivo y constructivo) de máximo 2 oraciones.
        {[
            {
                "pregunta": q.question,
                "respuesta": r.answer
            }
            for q in exam.questions if q.questionType == QuestionType.TEXT_ANSWER
            for r in submission.resolutions if r.question_id == q.id
        ]}

        Solo devolveme el texto.
        """

    general_feedback = call_ai_model(general_prompt)

    return CorrectionBase(
        course_id=exam.course_id,
        module_id=exam.module_id,
        exam_id=exam.id,
        user_id=submission.user_id,
        general_feedback=general_feedback,
        questions_feedback=questions_feedback
    )

def get_exams_pending_correction(course_id: int, module_id: Optional[int], db: Session):
    """
    Get exams submissions pending correction
    """
    if module_id is None:
        logging.info(f"Retrieving pending corrections for course {course_id} module {module_id}")
        return db.query(ExamSubmission).filter_by(course_id=course_id,corrected_date=None).all()
    else:
        logging.info(f"Retrieving pending corrections for course {course_id}")
        return db.query(ExamSubmission).filter_by(course_id=course_id,module_id=module_id,corrected_date=None).all()

def get_submission(course_id: int, module_id: int, exam_id: int, user_id: int, db: Session):
    """
    Get specific submission for exam matching course,module,exam,user 
    """
    exam: ExamResponse = get_exam(course_id=course_id, module_id=module_id, exam_id=exam_id, show_answer=True, show_activities=True,db=db)

    submission = (  # Consultamos la respuesta del alumno al examen, agregando preguntas y opciones
        db.query(ExamSubmission)
        .filter_by(course_id=course_id,module_id=module_id,exam_id=exam_id, user_id=user_id)
        .options(
            joinedload(ExamSubmission.resolutions).joinedload(ExamQuestionResolution.resolution_options)
        )
        .first()
    )
    if not submission:
        logging.info(f"Submission C{course_id} M{module_id} E{exam_id} U{user_id} not found")
        content = not_found_error(
            detail="The requested submission was not found on the server.",
            instance=f"/courses/{course_id}/module/{module_id}/exam/{exam_id}/submission/{user_id}"
        )
        raise HTTPException(status_code=404, detail=content)

    submission = format_submission_response(db_submission=submission)
    return (exam,submission)

def get_exams(course_id: int, db: Session):
    """
    Get exams by course
    """
    logging.info(f"Retrieving all exams for course {course_id}")
    if not get_course_by_ID(id=course_id, db=db):
        logging.info(f"Course with id: {id} not found")
        content = not_found_error(
            detail="The requested Course was not found on the server.",
            instance=f"/courses/{id}/exams"
        )
        raise HTTPException(status_code=404, detail=content)

    db_exams = db.query(Exam).filter(Exam.course_id==course_id,or_(Exam.isExam.is_(None), Exam.isExam.is_(True))).order_by(Exam.course_id.asc(), Exam.id.asc()).all()
    return format_exam_responses(db_exams=db_exams)

def get_exams_by_module(module_id: int, course_id: int, db: Session):
    """
    Get exams by course module
    """
    if not get_course_by_ID(id=course_id, db=db):
        logging.info(f"Course with id: {id} not found")
        content = not_found_error(
            detail="The requested Course was not found on the server.",
            instance=f"/courses/{id}/exams"
        )
        raise HTTPException(status_code=404, detail=content)

    if not get_module_by_ID(course_id=course_id,module_id=module_id, db=db):
        logging.info(f"Module {module_id} doesn't exist on {course_id}")
        content = not_found_error(
            detail="The requested Module was not found on the server.",
            instance=f"/courses/{id}/exams"
        )
        raise HTTPException(status_code=404, detail=content)

    db_exams = db.query(Exam).filter(Exam.course_id==course_id, Exam.module_id==module_id,or_(Exam.isExam.is_(None), Exam.isExam.is_(True))).all()
    return format_exam_responses(db_exams=db_exams)

def get_exam(course_id: int, module_id: int, exam_id: int, show_answer: bool, show_activities: bool, db: Session):
    """
    Get Exam by course module exam
    Return FULL ANSWER of exam 
    """
    logging.info(f"Retrieving exam {exam_id} for course {course_id} module {module_id}")

    if not get_course_by_ID(id=course_id,db=db):
        logging.info(f"Course with id: {id} not found")
        content = not_found_error(
            detail="The requested Course was not found on the server.",
            instance=f"/courses/{id}/exams"
        )
        raise HTTPException(status_code=404, detail=content)

    if not get_module_by_ID(course_id=course_id,module_id=module_id, db=db):
        logging.info(f"Module {module_id} doesn't exist on {course_id}")
        content = not_found_error(
            detail="The requested Module was not found on the server.",
            instance=f"/courses/{id}/exams"
        )
        raise HTTPException(status_code=404, detail=content)

    logging.info(f"Pre querying database for exam {exam_id} {module_id} {course_id}")
    db_exam = (
        db.query(Exam)
        .filter(
            Exam.course_id == course_id,
            Exam.module_id == module_id,
            Exam.id == exam_id,
            or_(Exam.isExam.is_(None), Exam.isExam.is_(True))
        )
        .options(
            joinedload(Exam.questions).joinedload(Question.options)
        )
        .first()
    ) if not show_activities else ( # Hotfix
        db.query(Exam)
        .filter(
            Exam.course_id == course_id,
            Exam.module_id == module_id,
            Exam.id == exam_id,
        )
        .options(
            joinedload(Exam.questions).joinedload(Question.options)
        )
        .first()
    )

    if not db_exam:
        logging.info(f"Exam {exam_id} doesn't exist on course {course_id} module {module_id}")
        content = not_found_error(
            detail="The requested Exam was not found on the server.",
            instance=f"/courses/{course_id}/exams"
        )
        raise HTTPException(status_code=404, detail=content)

    return format_exam_response(db_exam=db_exam, show_answer=show_answer)

# Activities
def get_activities(course_id: int, db: Session):
    """
    Get activities by course
    """
    logging.info(f"Retrieving all activities for course {course_id}")
    if not get_course_by_ID(id=course_id, db=db):
        logging.info(f"Course with id: {id} not found")
        content = not_found_error(
            detail="The requested Course was not found on the server.",
            instance=f"/courses/{id}/activities"
        )
        raise HTTPException(status_code=404, detail=content)

    db_activities = db.query(Exam).filter(Exam.course_id==course_id,Exam.isExam == False).order_by(Exam.course_id.asc(), Exam.id.asc()).all()
    return format_exam_responses(db_exams=db_activities)


def get_activities_by_module(module_id: int, course_id: int, db: Session):
    """
    Get activities by course module
    """
    if not get_course_by_ID(id=course_id, db=db):
        logging.info(f"Course with id: {id} not found")
        content = not_found_error(
            detail="The requested Course was not found on the server.",
            instance=f"/courses/{id}/activities"
        )
        raise HTTPException(status_code=404, detail=content)

    if not get_module_by_ID(course_id=course_id,module_id=module_id, db=db):
        logging.info(f"Module {module_id} doesn't exist on {course_id}")
        content = not_found_error(
            detail="The requested Module was not found on the server.",
            instance=f"/courses/{id}/activities"
        )
        raise HTTPException(status_code=404, detail=content)

    db_activities = db.query(Exam).filter(Exam.course_id==course_id, Exam.module_id==module_id,Exam.isExam==False).all()
    return format_exam_responses(db_exams=db_activities)

def get_activity(course_id: int, module_id: int, exam_id: int, show_answer: bool, db: Session):
    """
    Get activity by course module exam_id
    Return FULL activity (all question details) 
    """
    logging.info(f"Retrieving exam {exam_id} for course {course_id} module {module_id}")

    if not get_course_by_ID(id=course_id,db=db):
        logging.info(f"Course with id: {id} not found")
        content = not_found_error(
            detail="The requested Course was not found on the server.",
            instance=f"/courses/{id}/activities"
        )
        raise HTTPException(status_code=404, detail=content)

    if not get_module_by_ID(course_id=course_id,module_id=module_id, db=db):
        logging.info(f"Module {module_id} doesn't exist on {course_id}")
        content = not_found_error(
            detail="The requested Module was not found on the server.",
            instance=f"/courses/{id}/activities"
        )
        raise HTTPException(status_code=404, detail=content)

    logging.info(f"Pre querying database for activity {exam_id} {module_id} {course_id}")
    db_exam = (
        db.query(Exam)
        .filter(
            Exam.course_id == course_id,
            Exam.module_id == module_id,
            Exam.id == exam_id,
            Exam.isExam == False
        )
        .options(
            joinedload(Exam.questions).joinedload(Question.options)
        )
        .first()
    )

    if not db_exam:
        logging.info(f"Activity {exam_id} doesn't exist on course {course_id} module {module_id}")
        content = not_found_error(
            detail="The requested Activity was not found on the server.",
            instance=f"/courses/{course_id}/activites"
        )
        raise HTTPException(status_code=404, detail=content)

    return format_exam_response(db_exam=db_exam, show_answer=show_answer)

def get_exams_pending_submission(course_id: int, user_id: int, isExam: bool, module_id: Optional[int], db: Session):
    '''
    Retrieve Exams pending for user submission
    '''
    if module_id:
        submission_ids = [ exam_id for (exam_id,) in db.query(ExamSubmission.exam_id).filter_by(course_id=course_id,module_id=module_id, user_id=user_id).all() ]
        db_pending_exams = db.query(Exam).filter(Exam.course_id==course_id,Exam.module_id==module_id,~Exam.id.in_(submission_ids),Exam.isExam==isExam).all()
    else:
        submission_ids = [ exam_id for (exam_id,) in db.query(ExamSubmission.exam_id).filter_by(course_id=course_id,module_id=module_id, user_id=user_id).all() ]
        db_pending_exams = db.query(Exam).filter(Exam.course_id==course_id,~Exam.id.in_(submission_ids),Exam.isExam==isExam).all()
    return format_exam_responses(db_exams=db_pending_exams)

def get_user_submissions(course_id: int, user_id: int, isExam: bool, module_id: Optional[int], db: Session):
    '''
    Retrieve Exams submitted by user
    '''
    if module_id:
        submission_ids = [ exam_id for (exam_id,) in db.query(ExamSubmission.exam_id).filter_by(course_id=course_id,module_id=module_id, user_id=user_id).all() ]
        db_pending_exams = db.query(Exam).filter(Exam.course_id==course_id,Exam.module_id==module_id,Exam.id.in_(submission_ids),Exam.isExam==isExam).all()
    else:
        submission_ids = [ exam_id for (exam_id,) in db.query(ExamSubmission.exam_id).filter_by(course_id=course_id,module_id=module_id, user_id=user_id).all() ]
        db_pending_exams = db.query(Exam).filter(Exam.course_id==course_id,Exam.id.in_(submission_ids),Exam.isExam==isExam).all()
    return format_exam_responses(db_exams=db_pending_exams)


def format_submission_response(db_submission: ExamSubmission) -> ExamSubmissionResponse:
    response = ExamSubmissionResponse(
        course_id=db_submission.course_id,
        module_id=db_submission.module_id,
        exam_id=db_submission.exam_id,
        user_id=db_submission.user_id,
        submitted_date=db_submission.submitted_date,
        resolutions=[
            ExamResolutionResponse(
                question_id=resolution.question_id,
                answer=resolution.answer,
                points_earned=resolution.points_earned,
                feedback=resolution.feedback,
                options=[
                    ResolutionOptionResponse(id=option.option_id) for option in resolution.resolution_options
                ]
            )
            for resolution in db_submission.resolutions
        ]
    )

    # Si esta corregido, agregamos resultados de corrección
    if db_submission.corrected_date:
        response.corrected_date = db_submission.corrected_date
        response.general_feedback = db_submission.general_feedback
        points_earned = 0
        for resolution in db_submission.resolutions:
            points_earned += resolution.points_earned
        response.points_earned = points_earned

    return response

def format_exam_responses(db_exams: list[Exam]) -> list[ExamResponse]:
    '''
    Strips isExam from retrieved Exam.
    '''
    return [ ExamResponse(
        id=exam.id,
        course_id=exam.course_id,
        module_id=exam.module_id,
        exam_name=exam.exam_name,
        description=exam.exam_description,
        submission_deadline=exam.submission_deadline,
    ) for exam in db_exams ]

def format_exam_response(db_exam: Exam, show_answer: bool) -> ExamResponse:
    '''
    Manually format the response to include questions and their options
    '''
    return ExamResponse(
        id=db_exam.id,
        course_id=db_exam.course_id,
        module_id=db_exam.module_id,
        exam_name=db_exam.exam_name,
        description=db_exam.exam_description,
        submission_deadline=db_exam.submission_deadline,
        questions=[
            QuestionResponse(
                id=q.id,
                question=q.question,
                questionType=q.questionType.value,
                points=q.points,
                options=[
                    QuestionOptionResponse(
                        id=opt.id,
                        option_text=opt.option_text,
                        is_correct=opt.is_correct if show_answer else False
                    ) 
                    for opt in q.options if q.questionType.value != QuestionType.SINGLE_VALUE or show_answer
                ]
            )
            for q in db_exam.questions
        ]
    )

def delete_exam_by_ID(exam_id: int, module_id: int, course_id: int, db: Session):
    """
    Deletes exam by ID, return success message if found, 404 error if not
    """
    db_exam = db.query(Exam).filter_by(id=exam_id,course_id=course_id, module_id=module_id).first()
    if not db_exam:
        logging.info(f"Exam {exam_id} doesn't exist on course {course_id} module {module_id}")
        content = not_found_error(
            detail="The requested Course was not found on the server.",
            instance=f"/courses/{id}/exams"
        )
        raise HTTPException(status_code=404, detail=content)

    db.delete(db_exam)
    db.commit()

    logging.info(f"Exam {exam_id} of module {module_id} course {course_id} deleted")
    return {"message": "Exam deleted successfully"}

def submit_exam(submit: ExamSubmissionBase, db: Session):
    """
    Adds exam submission to the database. Also triggers auto correction 
    If submission deadline had passed, it returns HTTP 409 conflict
    """
    exam_response = get_exam(course_id=submit.course_id,module_id=submit.module_id,exam_id=submit.exam_id, show_answer=False,show_activities=True,db=db)
    if exam_response.submission_deadline:
        if exam_response.submission_deadline < datetime.now():
            raise HTTPException(status_code=409, detail=submission_deadline_pased())
    try:        
        model = submit.model_dump()
        model.pop("answered_questions", None) 
        db_exam = ExamSubmission(**model)
        
        logging.info(f"Adding exam submission")
        db.add(db_exam)
        db.flush() 

        if submit.answered_questions:
            for question in submit.answered_questions:
                logging.info(f"Adding answer to question {question.question_id}")
                db_question = format_resolution(question=question,exam=db_exam)
                db.add(db_question)
                db.flush() 

                if question.options_chosen:
                    for option in question.options_chosen:
                        logging.info(f"Adding question options chosen")
                        db.add(format_resolution_option(option=option, exam=db_exam, question=db_question))
            db.flush() 

        auto_correct(submit=submit, db=db)
    
        submission = db.query(ExamSubmission).filter_by(user_id=db_exam.user_id, course_id=db_exam.course_id, module_id=db_exam.module_id, exam_id=db_exam.exam_id).first() 
        return ExamSubmissionResponse(user_id=submission.user_id, course_id=submission.course_id, module_id=submission.module_id, exam_id=submission.exam_id, submitted_date=submission.submitted_date)

    except IntegrityError as e:
        db.rollback()
        content = not_found_error(
            detail="Integrity error, check input.",
            instance=f"/courses/exams"
        )
        raise HTTPException(status_code=404, detail=content)
    except SQLAlchemyError as e:
        db.rollback()
        content = not_found_error(
            detail=f"Database error: {str(e)}",
            instance=f"/courses/exams"
        )
        raise HTTPException(status_code=500, detail=content)
    
    except Exception as e:
        db.rollback()
        logging.error(f"Uncatched error {str(e)}")
        content = not_found_error(
            detail=f"Database error: {str(e)}",
            instance=f"/courses/exams"
        )
        raise HTTPException(status_code=500, detail=content)
    
def auto_correct(submit: ExamSubmissionBase, db: Session):
    """
    Auto corrects questions of type != TEXT_ANSWER
    """
    logging.info(f"Exam correction in progress")
    db_exam = (
        db.query(Exam)
        .filter_by(course_id=submit.course_id, module_id=submit.module_id, id=submit.exam_id)
        .options(
            joinedload(Exam.questions).joinedload(Question.options)
        )
        .first()
    )

    db_submission = (  
        db.query(ExamSubmission)
        .filter_by(course_id=submit.course_id,module_id=submit.module_id,exam_id=submit.exam_id, user_id=submit.user_id)
        .options(
            joinedload(ExamSubmission.resolutions).joinedload(ExamQuestionResolution.resolution_options)
        )
        .first()
    )

    automatic_correction: bool = True
    for question in db_exam.questions:
        logging.info(f"Correction in progress: question {question.id}")
        resolution = next((r for r in db_submission.resolutions if r.question_id == question.id), None)

        if resolution:
            if question.questionType == QuestionType.TEXT_ANSWER: 
                logging.info(f"question {question.id} is TEXT ANSWER: Ignored")
                automatic_correction = False
            else:
                if is_resolution_correct(question=question,resolution=resolution):
                    logging.info(f"question {question.id} CORRECT")
                    resolution.points_earned = question.points
                    resolution.feedback = "OK"
                else:
                    logging.info(f"question {question.id} INCORRECT")
                    resolution.feedback = "NOK"

    if automatic_correction:
        db_submission.corrected_date = datetime.now()
        send_correction_notification(exam=db_exam,auto_correct=True,user_id=db_submission.user_id,db=db)
    else:
        send_submit_notification(submission=db_submission,db=db)
    db.commit()

def is_resolution_correct(question: Question, resolution: ExamQuestionResolution) -> bool:
    if question.questionType == QuestionType.MULTIPLE_CHOICE:
        correct_option = next((opt for opt in question.options if opt.is_correct), None)
        chosen_option = next((opt for opt in resolution.resolution_options), None)
        return correct_option and chosen_option and correct_option.id == chosen_option.option_id

    elif question.questionType == QuestionType.MULTIPLE_ANSWER:
        correct_ids = sorted([opt.id for opt in question.options if opt.is_correct])
        chosen_ids = sorted([opt.option_id for opt in resolution.resolution_options])
        return correct_ids == chosen_ids

    elif question.questionType == QuestionType.SINGLE_VALUE:
        return question.options[0].option_text.strip().lower() == resolution.answer.strip().lower()

    return False

def format_resolution_option(option: ResolutionOptionBase, exam: ExamSubmission, question: ExamQuestionResolution) -> ResolutionOption:
    model = option.model_dump()

    model['option_id'] = model.pop('id')
    model['user_id'] = exam.user_id
    model['course_id'] = question.course_id
    model['module_id'] = question.module_id
    model['exam_id'] = question.exam_id
    model['question_id'] = question.question_id

    db_question_option = ResolutionOption(**model)

    return db_question_option

def format_resolution(question: ExamQuestionResolutionBase, exam: ExamSubmission) -> ExamQuestionResolution:
    model = question.model_dump()
    model.pop("options_chosen")
    model['user_id'] = exam.user_id
    model['course_id'] = exam.course_id
    model['module_id'] = exam.module_id
    model['exam_id'] = exam.exam_id
    db_question = ExamQuestionResolution(**model)

    return db_question

def send_exam_notification(exam: Exam, db: Session):
    course = get_course_by_ID(id=exam.course_id,db=db)

    metadata = {
        "course_id": str(exam.course_id),
    }

    if exam.isExam is None:
        title: str = EXAM_CREATION_NOTIFICATION_TITLE
        message: str = f"The exam {exam.exam_name} was added to course {course.title}"
    elif exam.isExam == True:
        title: str = EXAM_CREATION_NOTIFICATION_TITLE
        message: str = f"The exam {exam.exam_name} was added to course {course.title}"
    else:
        title: str = ACTIVITY_CREATION_NOTIFICATION_TITLE
        message: str = f"The activity {exam.exam_name} was added to course {course.title}"

    if exam.submission_deadline:
        message += f" with due date {exam.submission_deadline}"
        
    send_notification(title=title, message=message, users=get_course_students(course_id=exam.course_id,db=db), metadata=metadata)

def send_submit_notification(submission: ExamSubmission, db: Session):
    course_title=db.query(Course.title).filter_by(id=submission.course_id).first()
    exam=db.query(Exam).filter_by(course_id=submission.course_id, module_id=submission.module_id, id=submission.exam_id ).first()

    metadata = {
        "course_id": str(submission.course_id),
    }

    if exam.isExam is None:
        title: str = EXAM_SUBMISSION_NOTIFICATION_TITLE
        message: str = f"Exam {exam.exam_name} pending correction for enrollment ID {submission.user_id} in course {course_title[0]}"
    elif exam.isExam == True:
        title: str = EXAM_SUBMISSION_NOTIFICATION_TITLE
        message: str = f"Exam {exam.exam_name} pending correction for enrollment ID {submission.user_id} in course {course_title[0]}"
    else:
        title: str = ACTIVITY_SUBMISSION_NOTIFICATION_TITLE
        message: str = f"Activity {exam.exam_name} pending correction for enrollment ID {submission.user_id} in course {course_title[0]}"

    send_notification(title=title, message=message, users=get_course_teachers(course_id=submission.course_id,db=db), metadata=metadata)

def send_correction_notification(exam: Exam, user_id: int, auto_correct: bool, db: Session):
    course_title=db.query(Course.title).filter_by(id=exam.course_id).first()
    user_id=db.query(Enrollment.user_id).filter_by(id=int(user_id), course_id=exam.course_id).first()

    metadata = {
        "course_id": str(exam.course_id),
    }

    if exam.isExam is None:
        title: str = EXAM_CORRECTION_NOTIFICATION_TITLE
        message: str = f"Exam {exam.exam_name} from course {course_title[0]} was corrected"
    elif exam.isExam == True:
        title: str = EXAM_CORRECTION_NOTIFICATION_TITLE
        message: str = f"Exam {exam.exam_name} from course {course_title[0]} was corrected"
    else:
        title: str = ACTIVITY_CORRECTION_NOTIFICATION_TITLE
        message: str = f"Activity {exam.exam_name} from course {course_title[0]} was corrected"

    message += " automatically" if auto_correct else " by the teaching staff"
    send_notification(title=title, message=message, users=[user for user in user_id], metadata=metadata)
