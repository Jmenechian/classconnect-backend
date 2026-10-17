from datetime import datetime
from typing import List, Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from controllers.enrollment_controller import get_user
from models.constants import STUDENT_ROLE
from models.course import Course
from models.enrollment import Enrollment
from models.exams.exam import Exam
from models.exams.question import Question
from models.exams.resolution import ExamQuestionResolution

def get_global_stats(db: Session):
    courses = db.query(Course).all()

    course_averages = []
    course_list = []
    total_average = [0, 0]
    best_student_data = {}
    global_performance = {
        "excellent": 0,
        "good": 0,
        "regular": 0,
        "bad": 0
    }

    for course in courses:
        stats = get_stats_by_course(course_id=course.id, date=datetime.now(), db=db)
        course_average = 0

        for item in stats:
            if "course_average" in item:
                course_average = item["course_average"]
            if "best_student" in item:
                name = item["best_student"]
                grade = item["best_student_grade"]
                best_student_data[name] = [
                    best_student_data.get(name, [0, 0])[0] + grade,
                    best_student_data.get(name, [0, 0])[1] + 1
                ]
            if "performance_distribution" in item:
                for category, count in item["performance_distribution"].items():
                    global_performance[category] += count

        course_averages.append(course_average)
        course_list.append({
            "course_name": course.title,
            "average_grade": course_average
        })
        total_average[0] += course_average
        total_average[1] += 1

    if total_average[1] == 0:
        return {}

    global_average = total_average[0] / total_average[1]

    best_global_student = None
    best_global_avg = -1
    worst_global_student = None
    worst_global_avg = float('inf')

    for name, (total, count) in best_student_data.items():
        avg = total / count
        if avg > best_global_avg:
            best_global_avg = avg
            best_global_student = name
        if avg < worst_global_avg:
            worst_global_avg = avg
            worst_global_student = name

    return {
        "global_average": global_average,
        "courses": course_list,
        "best_student": best_global_student,
        "best_student_average": best_global_avg,
        "worst_student": worst_global_student,
        "worst_student_average": worst_global_avg,
        "global_performance_distribution": global_performance
    }

def get_stats_by_course(course_id: int, date: datetime, db: Session):
    if date:
        exams = db.query(Exam).filter((Exam.course_id == course_id)&(Exam.submission_deadline <= date)).all()
    else:
        exams = db.query(Exam).filter(Exam.course_id == course_id).all()
    enrolled_students = db.query(Enrollment.id).filter(Enrollment.course_id == course_id, Enrollment.role == STUDENT_ROLE).all() #ID de enrollments no user_id

    student_ids = [user_id for (user_id,) in enrolled_students]

    result = []
    exam_averages = []

    student_exam_grades = {}  #notas por alumno
    student_exam_counts = {}  #extra info(?)
    for student_id in student_ids:
        student_exam_grades[student_id] = []
        student_exam_counts[student_id] = set()

    total_exams = len(exams)

    for exam in exams:
        exam_questions = db.query(Question).filter(Question.exam_id == exam.id).all()
        max_points = sum(q.points for q in exam_questions)
        # if max_points == 0: #definir si esto va o no, tareas como examen sin puntos?
        #     continue

        all_answers = db.query(ExamQuestionResolution).filter(ExamQuestionResolution.exam_id == exam.id).all()

        user_points = {}
        for answer in all_answers:
            user_points.setdefault(answer.user_id, 0)
            user_points[answer.user_id] += answer.points_earned
            student_exam_counts.setdefault(answer.user_id, set()).add(exam.id)

        grades = []
        for user_id in student_ids:
            points = user_points.get(user_id, 0)
            grade = (points / max_points) * 10
            grades.append(grade)
            student_exam_grades[user_id].append(grade)

        if grades:
            average_grade = sum(grades) / len(grades)
        else:
            average_grade = 0
        exam_averages.append(average_grade)
        result.append({"Exam_name": exam.exam_name, "average_grade": average_grade})

    course_average = sum(exam_averages) / len(exam_averages) if exam_averages else 0

    student_averages = {}
    for student_id, grades in student_exam_grades.items():
        student_averages[student_id] = sum(grades) / len(grades) if grades else 0

    if student_averages:
        best_student = max(student_averages, key=student_averages.get)
        worst_student = min(student_averages, key=student_averages.get)
        best_grade = student_averages[best_student]
        worst_grade = student_averages[worst_student]
    else:
        best_student = None
        worst_student = None
        best_grade = None
        worst_grade = None

    num_students = len(student_ids)
    students_all_exams = sum(1 for sid in student_ids if len(student_exam_counts.get(sid, set())) == total_exams)
    students_no_exams = sum(1 for sid in student_ids if len(student_exam_counts.get(sid, set())) == 0)
    students_some_exams = sum(1 for sid in student_ids if 0 < len(student_exam_counts.get(sid, set())) < total_exams)

    best_student_name = get_student_full_name(best_student, db)
    worst_student_name = get_student_full_name(worst_student, db)

    performance_distribution = {
        "excellent": 0,
        "good": 0,
        "regular": 0,
        "bad": 0
    }

    for avg in student_averages.values():
        if avg > 9:
            performance_distribution["excellent"] += 1
        elif avg > 7:
            performance_distribution["good"] += 1
        elif avg >= 4:
            performance_distribution["regular"] += 1
        else:
            performance_distribution["bad"] += 1

    if num_students > 0:
        result.append({
            "course_average": course_average,
            "num_students": num_students,
            "best_student": best_student_name,
            "best_student_grade": best_grade,
            "worst_student": worst_student_name,
            "worst_student_grade": worst_grade,
            "percentage_all_exams": students_all_exams / num_students,
            "percentage_no_exams": students_no_exams / num_students,
            "percentage_some_exams": students_some_exams / num_students,
            "performance_distribution": performance_distribution
        })
    else:
        result.append({
            "course_average": 0,
            "num_students": 0,
            "best_student": "No hay",
            "best_student_grade": 0,
            "worst_student": "No hay",
            "worst_student_grade": 0,
            "percentage_all_exams": 0,
            "percentage_no_exams": 0,
            "percentage_some_exams": 0,
            "performance_distribution": {
                "excellent": 0,
                "good": 0,
                "regular": 0,
                "bad": 0
            }
        })

    return result


def get_student_full_name(best_student, db):
    if not best_student:
        return "No student data"
        
    best_student_user_id = db.query(Enrollment.user_id).filter(
        Enrollment.id == best_student).scalar()
    
    if not best_student_user_id:
        return "Unknown Student"
        
    user = get_user(best_student_user_id)
    
    name = "Unknown"
    surname = "Student"
    
    if user and isinstance(user, dict):
        user_data = user.get("data", {})
        if isinstance(user_data, dict):
            name = user_data.get("name", "Unknown")
            surname = user_data.get("surname", "Student")
    
    return f"{name} {surname}"


def get_stats_by_student(course_id: int, user_id: int, db: Session):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return {"error": "Course not found"}
    user = db.query(Enrollment).filter(Enrollment.id == user_id).first()
    if not user:
        return {"error": "User not found"}
    exams = db.query(Exam).filter(Exam.course_id == course_id).all() #examenes de un curso
    if not exams:
        return {"error": "No exams found for this course"}

    grades = []
    for exam in exams:
        count = 0
        max_points = 0
        answers_to_exam = db.query(ExamQuestionResolution).filter(ExamQuestionResolution.exam_id == exam.id, ExamQuestionResolution.user_id == user_id).all()
        for answer in answers_to_exam:
            count += answer.points_earned

        exam_questions = db.query(Question).filter(Question.exam_id == exam.id).all()
        for question in exam_questions:
            max_points += question.points

        grade = (count / max_points) * 10 #nota de 0 a 10
        grades.append((exam.exam_name, grade))

    average_grade = sum(grade for _, grade in grades) / len(grades)
    result = [{"Exam_name": name, "grade": grade} for name, grade in grades]
    result.append({"average_grade": average_grade})
    return result
