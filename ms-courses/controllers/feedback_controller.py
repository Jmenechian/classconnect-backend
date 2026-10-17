from controllers.enrollment_controller import get_user
from controllers.exam_controller import call_ai_model
from models.course import Course
from models.error import not_found_error
from models.feedback import Feedback
from fastapi.exceptions import HTTPException

COURSE = "Course"
STUDENT = "Student"
def give_feedback_to_course_as_student(feedback, db):
    db_feedback = Feedback(**feedback.model_dump())

    course = db.query(Course).filter(Course.id == db_feedback.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if db_feedback.score < 1 or db_feedback.score > 5:
        raise HTTPException(status_code=409, detail="Score out of range")

    db_feedback.target = COURSE
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)

    return db_feedback

def give_feedback_to_student_as_teacher(feedback, db):
    db_feedback = Feedback(**feedback.model_dump())

    course = db.query(Course).filter(Course.id == db_feedback.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if db_feedback.score < 1 or db_feedback.score > 5:
        raise HTTPException(status_code=400, detail="Score out of range")

    if not feedback.teacher_id:
        raise HTTPException(status_code=422, detail="Teacher_id missing")
    db_feedback.target = STUDENT
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)

    return db_feedback

def get_all_feedback_from_course(course_id: int, db) -> list[dict]: #fancy, lento como tortuga
    reviews = db.query(Feedback).filter((Feedback.course_id == course_id) & (Feedback.target == "Course")).all()

    result = []

    for r in reviews:
        user = get_user(r.user_id)
        course = db.query(Course).filter(Course.id == r.course_id).first()
        name = "Unknown"
        surname = "User"

        if user and isinstance(user, dict):
            user_data = user.get("data", {})
            if isinstance(user_data, dict):
                name = user_data.get("name", "Unknown")
                surname = user_data.get("surname", "User")
        full_name = f"{name} {surname}"
        result.append({
            "course_name": course.title,
            "full_name": full_name,
            "comment": r.comment,
            "score": r.score
        })

    return result

def get_all_feedback_from_course_summary(course_id: int, db):
    reviews = db.query(Feedback).filter((Feedback.course_id == course_id)&(Feedback.target == COURSE)).all()
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    course_name = course.title
    if not reviews:
        return {
            "course_name": course_name,
            "average_score": 0,
            "summary": "Falta feedback"
        }

    comments = [r.comment.strip() for r in reviews if r.comment]
    average_score = round(sum(r.score for r in reviews) / len(reviews), 2)

    prompt = (
        f"Resumi brevemente en maximo 100 caracteres los siguientes comentarios de un curso:\n"
        f"{'; '.join(comments)}"
    )
    summary = call_ai_model(prompt)

    return {
        "course_name": course_name,
        "average_score": average_score,
        "summary": summary,
    }


def get_all_feedback_from_student(user_id, score, db):
    reviews = db.query(Feedback).filter((Feedback.user_id == user_id) & (Feedback.target == "Student") & (Feedback.score >= score)).all()
    name = "Unknown"
    surname = "User"
    user = get_user(user_id)
    if user and isinstance(user, dict):
        user_data = user.get("data", {})
        if isinstance(user_data, dict):
            name = user_data.get("name", "Unknown")
            surname = user_data.get("surname", "User")

    full_name = f"{name} {surname}"

    reviews_data = []
    for r in reviews:
        teacher_name = "Unknown"
        teacher_surname = "User"
        teacher = get_user(r.teacher_id)
        if teacher and isinstance(teacher, dict):
            teacher_data = teacher.get("data", {})
            if isinstance(teacher_data, dict):
                teacher_name = teacher_data.get("name", "Unknown")
                teacher_surname = teacher_data.get("surname", "User")
        teacher_name = f"{teacher_name} {teacher_surname}"
        course = db.query(Course).filter(Course.id == r.course_id).first()
        course_name = course.title

        reviews_data.append({
            "course_name": course_name,
            "teacher_name": teacher_name,
            "comment": r.comment,
            "score": r.score
        })

    return {"full_name": full_name, "reviews": reviews_data}

def get_all_feedback_from_student_summary(user_id, db) -> dict:
    reviews = db.query(Feedback).filter((Feedback.user_id == user_id) & (Feedback.target == "Student")).all()

    name = "Unknown"
    surname = "User"
    user = get_user(user_id)
    if user and isinstance(user, dict):
        user_data = user.get("data", {})
        if isinstance(user_data, dict):
            name = user_data.get("name", "Unknown")
            surname = user_data.get("surname", "User")
    full_name = f"{name} {surname}"

    if not reviews:
        return {
            "full_name": full_name,
            "average_score": 0,
            "summary": "No hay comentarios disponibles."
        }

    comments = [r.comment.strip() for r in reviews if r.comment]
    average_score = round(sum(r.score for r in reviews) / len(reviews), 2)

    prompt = (
        f"Resumí en una frase de máximo 100 caracteres los siguientes comentarios de docentes "
        f"sobre un estudiante llamado {full_name}:\n"
        f"{'; '.join(comments)}"
    )

    summary = call_ai_model(prompt)

    return {
        "full_name": full_name,
        "average_score": average_score,
        "summary": summary
    }
