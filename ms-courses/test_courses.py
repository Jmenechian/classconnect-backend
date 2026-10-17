from datetime import datetime
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from controllers.utils import get_db
from database.data import engine
from models.constants import STUDENT_ROLE, MAIN_TEACHER_ROLE
from models.course import Base
from main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.error import ErrorResponse
from controllers.token_verifier import verify_token
import os

DB_USERNAME = os.environ["DB_USERNAME"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_URL = os.environ["DB_URL"]
TEST_SQLALCHEMY_DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_URL}"
)
engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)  # Session, check later for autocommit thing


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db  # use test instead of main

Base.metadata.create_all(bind=engine)  # create tables

client = TestClient(app)

# Mock user data for testing
MOCK_USER = {
    "id": "test_user_id",
    "uid": "test_uid",
    "token": "test_token",
    "subject_id": "test_subject_id",
    "name": "Test User",
    "surname": "Test Surname",
    "email": "test@example.com",
    "country": "Test Country"
}

# Mock the user service responses
@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_create_course(mock_get_user, mock_check_user_exists):
    """
    Testing a normal POST
    status code of 201
    Returns the course with now it's ID
    """
    # Setup mocks
    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER

    response = client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0})
    response = client.get(f"/courses/subjects/{response.json()["data"]["id"]}")
    assert response.status_code == 200
    response = client.get(f"/courses/subjects/?title={response.json()["data"]["title"]}")
    assert response.status_code == 200
    response = client.get(f"/courses/subjects/")
    assert len(response.json()["data"]) > 0

    course_data = curso_ejemplo()
    response = client.post("/courses/", json=course_data)

    assert response.status_code == 201
    response_data = response.json()
    course = response_data["data"]
    assert course["description"] == course_data["description"]
    assert course["title"] == course_data["title"]
    assert course["quota"] == course_data["quota"]
    assert course["date_start"] == course_data["date_start"]
    assert course["date_finish"] == course_data["date_finish"]
    assert "id" in course

@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_enroll(mock_get_user, mock_check_user_exists):
    """
    Testing a normal POST
    status code of 201
    Returns the course with now it's ID
    """
    # Setup mocks
    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER

    subject1 = client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0 }).json()["data"]["id"]
    subject2 = client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":10}).json()["data"]["id"]
    course_data = curso_ejemplo()
    course_data["subject_id"] = subject1
    response = client.post("/courses/", json=course_data)
    assert response.status_code == 201
    course_id_1 = response.json()["data"]["id"]
    course_data["subject_id"] = subject2
    response = client.post("/courses/", json=course_data)
    assert response.status_code == 201
    course_id_2 = response.json()["data"]["id"]

    response = client.post("/courses/enrollment", json={"user_id":MOCK_USER["uid"],"course_id":course_id_1, "role":STUDENT_ROLE, "status":"In Progress"})
    assert response.status_code == 200
    response = client.post("/courses/enrollment", json={"user_id":MOCK_USER["uid"],"course_id":course_id_2, "role":STUDENT_ROLE, "status":"In Progress"})
    assert response.status_code == 409

    response = client.get(f"/courses/{course_id_1}/enrollments")
    assert response.status_code == 200
    assert len(response.json()) == 2 

    response = client.get(f"/courses/{course_id_2}/enrollments")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.request(
        "DELETE",
        "/courses/enrollment/delete",
        json={"user_id": MOCK_USER["uid"], "course_id": course_id_1}
    )
    assert response.status_code == 200
    response = client.get(f"/courses/{course_id_1}/enrollments")
    assert response.status_code == 200
    assert len(response.json()) == 1


def curso_ejemplo():
    course_data = {
        "title": "Curso de prueba",
        "description": "Descripcion de prueba",
        "quota": 94,
        "subject_id": 1,  # This will be overridden in the test
        "date_start": "2026-06-08T00:00:00",
        "date_finish": "2026-10-08T00:00:00",
        "user_id": "test_user_id"
    }
    return course_data

@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_create_course_with_extra_data(mock_get_user, mock_check_user_exists):
    """
    Testing a POST with extra data in it's body
    Status code of 201
    Returns a correct course, ignoring the extra data
    """
    # Setup mocks
    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER

    course_data = {
        "title": "Curso de prueba",
        "description": "Descripcion de prueba",
        "quota": 94,
        "subject_id": 1,
        "date_start": "2026-06-08T00:00:00",
        "date_finish": "2026-10-08T00:00:00",
        "user_id": "test_user_id",
        "comida": "Pollo",
    }
    client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0})
    response = client.post("/courses/", json=course_data)

    assert response.status_code == 201
    response_data = response.json()
    course = response_data["data"]
    assert course["description"] == course_data["description"]
    assert course["title"] == course_data["title"]
    assert course["quota"] == course_data["quota"]
    assert course["date_start"] == course_data["date_start"]
    assert course["date_finish"] == course_data["date_finish"]
    assert "id" in course


@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_create_course_with_different_id(mock_get_user, mock_check_user_exists):
    """
    Testing a POST trying to change ID (primary key) and checking that it ignored it
    Status code of 201
    Returns a correct course, ignoring the change in ID
    """
    # Setup mocks
    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER

    course_data = {
        "title": "Curso de prueba",
        "description": "Descripcion de prueba",
        "quota": 94,
        "subject_id": 1,
        "date_start": "2026-06-08T00:00:00",
        "date_finish": "2026-10-08T00:00:00",
        "user_id": "test_user_id",
        "id": 999,
    }
    client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0})
    response = client.post("/courses/", json=course_data)

    assert response.status_code == 201
    response_data = response.json()
    course = response_data["data"]
    assert course["description"] == course_data["description"]
    assert course["title"] == course_data["title"]
    assert course["quota"] == course_data["quota"]
    assert course["date_start"] == course_data["date_start"]
    assert course["date_finish"] == course_data["date_finish"]
    assert "id" in course
    assert course["id"] != course_data["id"]


@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_get_all_courses(mock_get_user, mock_check_user_exists):
    """
    Testing getting all courses
    Status code of 200
    Returns a list of courses
    """
    # Setup mocks
    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER

    response = client.get("/courses/")

    assert response.status_code == 200
    courses = response.json()["data"]
    assert isinstance(courses, list)


@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_get_course_by_id(mock_get_user, mock_check_user_exists):
    """
    Testing getting a course by a given ID
    Status code of 200
    Returns a course
    """
    # Setup mocks
    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER

    course_data = curso_ejemplo()
    client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0})
    create_response = client.post("/courses/", json=course_data)
    created_course = create_response.json()["data"]

    response = client.get(f"/courses/{created_course['id']}")

    assert response.status_code == 200
    assert response.json() == created_course

@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_error_get_course_by_id(mock_get_user, mock_check_user_exists):
    """
    Testing getting a course by an ID of a course that doesn't exist
    Status code of 404
    Returns an ErrorResponse
    """

    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER
    course_data = curso_ejemplo()
    client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0})
    create_response = client.post("/courses/", json=course_data)
    created_course = create_response.json()["data"]

    response = client.get(f"/courses/{created_course['id'] + 999}")
    error_details = response.json().get("detail")
    assert error_details is not None

    assert response.status_code == 404
    assert ErrorResponse.model_validate(error_details)

@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_modify_course_by_id(mock_get_user, mock_check_user_exists):
    """
    Testing modifying a course by a given ID
    Status code of 200
    Returns a course modified
    """

    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER
    course_data = curso_ejemplo()
    client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0})

    to_mod = {
        "quota": 1
    }
    create_response = client.post("/courses/", json=course_data)
    created_course = create_response.json()["data"]

    response = client.put(f"/courses/{created_course['id']}", json=to_mod)

    assert response.status_code == 200

@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_delete_course_by_id(mock_get_user, mock_check_user_exists):
    """
    Testing deleting a course by a given ID
    Status code of 200
    Returns a message of success

    Then test deleting the same course again
    Status code of 404
    Returns an ErrorResponse
    """

    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER
    course_data = curso_ejemplo()
    client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0})

    create_response = client.post("/courses/", json=course_data)
    created_course = create_response.json()["data"]

    delete_response = client.delete(f"/courses/{created_course['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Course deleted successfully"}

    response = client.get(f"/courses/{created_course['id']}")
    assert response.status_code == 404
    error_details = response.json().get("detail")
    assert error_details is not None

    assert ErrorResponse.model_validate(error_details)

def test_update_nonexistent_course():
    response = client.put("/courses/99999", json={"title": "New Title"})
    assert response.status_code == 404


def test_delete_nonexistent_course():
    response = client.delete("/courses/99999")
    assert response.status_code == 404


# Tests for module_controller.py
def test_get_nonexistent_module():
    response = client.get("/courses/99999/modules/1")
    assert response.status_code == 404

def test_delete_nonexistent_module():
    response = client.delete("/courses/99999/modules/1")
    assert response.status_code == 404

@patch('router.router.verify_token')
@patch('router.router.valid_permission')
@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_add_module(mock_get_user, mock_check_user_exists, mock_verify_token, mock_valid_permission):
    # Add course

    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER
    mock_verify_token.return_value = "123"
    mock_valid_permission.return_value = MAIN_TEACHER_ROLE

    course_data = curso_ejemplo()
    client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0} )

    response = client.post("/courses/", json=course_data)

    assert response.status_code == 201
    response_data = response.json()
    course = response_data["data"]
    assert course["description"] == course_data["description"]
    assert course["title"] == course_data["title"]
    assert course["quota"] == course_data["quota"]
    assert course["date_start"] == course_data["date_start"]
    assert course["date_finish"] == course_data["date_finish"]
    assert "id" in course

    # Add module
    module_data = {
        "course_id": course["id"],
        "module_name": "Modulo de prueba",
        "module_description": "Modulo de prueba",
    }

    response = client.post("/courses/modules", json=module_data, headers={"Token": "algo"})
    assert response.status_code == 201
    response_data = response.json()
    course = response_data["data"]
    assert course["course_id"] == module_data["course_id"]
    assert course["module_name"] == module_data["module_name"]
    assert course["module_description"] == module_data["module_description"]
    assert "id" in course

# Tests for enrollment_controller.py 
@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_enroll_user(mock_get_user, mock_check_user_exists):
    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER

    # --- Step 0: Create course and module (preconditions) ---
    client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0})
    course_data = curso_ejemplo()

    courses = []
    for i in range(3):    
        response = client.post("/courses/", json=course_data)
        assert response.status_code == 201
        courses.append(response.json()["data"])

    enrollments = []
    for i in range(2):    
        response = client.post("/courses/enrollment", json={"user_id":MOCK_USER["uid"],"course_id":courses[i]["id"], "role":STUDENT_ROLE, "status":"In Progress"})
        assert response.status_code == 200
        enrollments.append(response.json()["data"])
       

    response = client.get(f"/courses/?user_id={MOCK_USER["uid"]}")
    assert response.status_code == 200
    enrolled_ids = [c["id"] for c in response.json()["data"]]

    assert courses[0]["id"] in enrolled_ids
    assert courses[1]["id"] in enrolled_ids
    assert courses[2]["id"] not in enrolled_ids

# Tests for exam_controller.py
def test_get_nonexistent_exam():
    response = client.get("/courses/99999/modules/1/exams/1")
    assert response.status_code == 404

def test_delete_nonexistent_exam():
    response = client.delete("/courses/99999/modules/1/exams/1")
    assert response.status_code == 404

def test_creat_exam_in_non_existent_course():
    response = client.post("/courses/exams", json={"course_id":123456,"module_id":123456,"exam_name":"doesnt exist","exam_description":"doesnt exist"})
    assert response.status_code == 422

@patch('router.router.verify_token')
@patch('router.router.valid_permission')
@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_create_and_retrieve_exam(mock_get_user, mock_check_user_exists, mock_verify_token, mock_valid_permission):
    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER
    mock_verify_token.return_value = "123"
    mock_valid_permission.return_value = MAIN_TEACHER_ROLE

    # --- Step 0: Create course and module (preconditions) ---
    course_data = curso_ejemplo()
    response = client.post("/courses/", json=course_data)
    course = response.json()["data"]
    response = client.post("/courses/modules", json={
        "course_id": course["id"],
        "module_name": "Modulo de prueba",
        "module_description": "Modulo de prueba",
    } , headers={"Token": "algo"})
    module = response.json()["data"]

    # --- Step 1: Create Exam ---
    exam_body = {
        "course_id": course["id"],
        "module_id": module["id"],
        "exam_name": "Test Exam",
        "exam_description": "Test Desc",
        "questions": [
            {
                "question": "Capital of Argentina?",
                "questionType": "MULTIPLE_CHOICE",
                "points": 3,
                "options": [
                    {"option_text": "Buenos Aires", "is_correct": True},
                    {"option_text": "Cordoba", "is_correct": False}
                ]
            },
            {
                "question": "Select programming languages",
                "questionType": "MULTIPLE_ANSWER",
                "points": 5,
                "options": [
                    {"option_text": "Python", "is_correct": True},
                    {"option_text": "HTML", "is_correct": False},
                    {"option_text": "Java", "is_correct": True}
                ]
            },
            {
                "question": "Answer with a single number",
                "questionType": "SINGLE_VALUE",
                "points": 2,
                "options": [
                    {"option_text": "42", "is_correct": True}
                ]
            },
            {
                "question": "Explain the Big Bang theory",
                "questionType": "TEXT_ANSWER",
                "points": 4
            }
        ]
    }

    response = client.post("/courses/exams", json=exam_body, headers={"Token": "algo"})
    assert response.status_code == 200
    exam_data = response.json()["data"]
    assert exam_data["exam_name"] == "Test Exam"
    assert exam_data["module_id"] == module["id"]
    assert exam_data["course_id"] == course["id"]
    exam_id = exam_data["id"]

    # --- Step 2: Get list of exams for the course ---
    list_response = client.get(f"/courses/{course["id"]}/exams")
    assert list_response.status_code == 200
    exams = list_response.json()["data"]
    assert any(e["id"] == exam_id for e in exams)

    list_response = client.get(f"/courses/{course["id"]}/activities")
    assert list_response.status_code == 200
    exams = list_response.json()["data"]
    assert not any(e["id"] == exam_id for e in exams)

    # --- Step 3: Get list of exams for the course and module ---
    list_response = client.get(f"/courses/{course["id"]}/exams?module_id={module["id"]}")
    assert list_response.status_code == 200
    exams = list_response.json()["data"]
    assert any(e["id"] == exam_id for e in exams)

    list_response = client.get(f"/courses/{course["id"]}/activities?module_id={module["id"]}")
    assert list_response.status_code == 200
    exams = list_response.json()["data"]
    assert not any(e["id"] == exam_id for e in exams)

    # --- Step 3: Get full exam with questions/options ---
    full_response = client.get(f"/courses/{course["id"]}/exams?module_id={module["id"]}&exam_id={exam_id}")
    assert full_response.status_code == 200
    exam = full_response.json()["data"][0]
    assert exam["exam_name"] == "Test Exam"
    assert len(exam["questions"]) == 4

    mc_question = exam["questions"][0]
    assert mc_question["questionType"] == "MULTIPLE_CHOICE" 
    assert len(mc_question["options"]) == 2

    full_response = client.get(f"/courses/{course["id"]}/activities?module_id={module["id"]}&exam_id={exam_id}")
    assert full_response.status_code == 404

@patch('router.router.verify_token')
@patch('router.router.valid_permission')
@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_submit_and_correct_exam(mock_get_user, mock_check_user_exists, mock_verify_token=None,
                                 mock_valid_permission=None):
    mock_check_user_exists.return_value = True
    mock_get_user.return_value = {"data": MOCK_USER}
    mock_valid_permission.return_value = MAIN_TEACHER_ROLE
    mock_verify_token.return_value = "123"
    # --- Step 0: Create course and module (preconditions) ---
    client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0})
    course_data = curso_ejemplo()
    response = client.post("/courses/", json=course_data)
    course = response.json()["data"]
    module_data = {
        "course_id": course["id"],
        "module_name": "Modulo de prueba",
        "module_description": "Modulo de prueba",
    }
    response = client.post("/courses/modules", json=module_data, headers = {"Token": "algo"})
    module = response.json()["data"]

    response = client.post("/courses/enrollment", json={"user_id":MOCK_USER["uid"],"course_id":course["id"], "role":STUDENT_ROLE, "status":"In Progress"})
    assert response.status_code == 200
    enrollment_id = response.json()["data"]["id"]

    # --- Step 1: Create Exam ---
    exam_body = {
        "course_id": course["id"],
        "module_id": module["id"],
        "exam_name": "Test Exam",
        "exam_description": "Test Desc",
        "questions": [
            {
                "question": "Capital of Argentina?",
                "questionType": "MULTIPLE_CHOICE",
                "points": 3,
                "options": [
                    {"option_text": "Buenos Aires", "is_correct": True},
                    {"option_text": "Cordoba", "is_correct": False}
                ]
            },
            {
                "question": "Select programming languages",
                "questionType": "MULTIPLE_ANSWER",
                "points": 5,
                "options": [
                    {"option_text": "Python", "is_correct": True},
                    {"option_text": "HTML", "is_correct": False},
                    {"option_text": "Java", "is_correct": True}
                ]
            },
            {
                "question": "Remainder of 92 % 50",
                "questionType": "SINGLE_VALUE",
                "points": 2,
                "options": [
                    {"option_text": "42", "is_correct": True}
                ]
            },
            {
                "question": "Explain the Big Bang theory",
                "questionType": "TEXT_ANSWER",
                "points": 4
            }
        ]
    }

    response = client.post("/courses/exams", json=exam_body, headers = {"Token": "algo"})
    assert response.status_code == 200
    exam_id = response.json()["data"]["id"]

    response = client.get(f"/courses/{course["id"]}/exams?module_id={module["id"]}&exam_id={exam_id}")
    assert response.status_code == 200
    exam_data = response.json()["data"][0]

    # Build answers dynamically based on question type
    answered_questions = []
    for question in exam_data["questions"]:
        q_type = question["questionType"]
        q_id = question["id"]

        if q_type == "MULTIPLE_CHOICE":
            # Pick the first option as chosen (example)
            option_id = question["options"][0]["id"]
            answered_questions.append({
                "question_id": q_id,
                "answer": "",  # Could be optional for MC
                "options_chosen": [{"id": option_id}]
            })
        elif q_type == "MULTIPLE_ANSWER":
            # Pick all options as chosen (example)
            option_ids = [{"id": opt["id"]} for opt in question["options"]]
            answered_questions.append({
                "question_id": q_id,
                "answer": "",
                "options_chosen": option_ids
            })
        elif q_type == "SINGLE_VALUE":
            # Just pick the first one (simulate form submission)
#            option_id = question["options"][0]["id"]
            answered_questions.append({
                "question_id": q_id,
                "answer": "41",
                "options_chosen": []
            })
        elif q_type == "TEXT_ANSWER":
            # Provide a manual answer
            answered_questions.append({
                "question_id": q_id,
                "answer": "The Big Bang theory is a cosmological model...",
                "options_chosen": []
            })

    # Submit the exam
    submit_body = {
        "user_id": enrollment_id,
        "course_id": course["id"],
        "module_id": module["id"],
        "exam_id": exam_id,
        "answered_questions": answered_questions
    }

    submit_response = client.post("/courses/submission", json=submit_body)
    assert submit_response.status_code == 200

    response = client.get(f"/courses/{course["id"]}/module/{module["id"]}/exam/{exam_id}/submission/{enrollment_id}")
    assert submit_response.status_code == 200

    submission_data = response.json()
    exam_submission_data = submission_data["exam"]
    submission_data = submission_data["submission"]

#    print(exam_submission_data)
#    print(submission_data)

    resolutions = submission_data["resolutions"]

    # Track any text answers that need correction
    text_answers_to_correct = []

    for resolution in resolutions:
        question_id = resolution["question_id"]
        answer = resolution["answer"]
        feedback = resolution["feedback"]
        points_earned = resolution["points_earned"]

        # Match question type from exam metadata
        question = next(q for q in exam_submission_data["questions"] if q["id"] == question_id)
        q_type = question["questionType"]

        if q_type != "TEXT_ANSWER":
            assert feedback is not None, f"Missing feedback on question {question_id}"
            assert points_earned is not None, f"Missing points_earned on question {question_id}"
        else:
            # Store question for correct
            text_answers_to_correct.append({
                "question_id": question_id,
                "points_earned": 3,  # Arbitrary value for test
                "feedback": "Good explanation!"
            })

    # Manually correct all text answers
    correction = {
        "user_id": submission_data["user_id"],
        "course_id": submission_data["course_id"],
        "module_id": submission_data["module_id"],
        "exam_id": submission_data["exam_id"],
        "general_feedback":"Teacher Feedback",
        "questions_feedback": text_answers_to_correct
    }

    correction_response = client.post("/courses/corrections", json=correction, headers = {"Token": "algo"})
    correction_result = correction_response.json()
    assert correction_response.status_code == 200, f"Correction failed: {correction_result}"

    response = client.get(f"/courses/{course["id"]}/module/{module["id"]}/exam/{exam_id}/submission/{enrollment_id}")
    assert submit_response.status_code == 200

    submission_data = response.json()["submission"]
    print(submission_data)
    assert submission_data["corrected_date"] is not None and submission_data["corrected_date"] is not None
    submitted_date = datetime.fromisoformat(submission_data["submitted_date"])
    corrected_date = datetime.fromisoformat(submission_data["corrected_date"])

    assert submitted_date < corrected_date and corrected_date < datetime.now()

    for resolution in submission_data["resolutions"]:
        question_id = resolution["question_id"]
        feedback = resolution["feedback"]
        points_earned = resolution["points_earned"]

        assert feedback != None, f"Missing feedback on question {question_id}"
        assert points_earned != None, f"Missing points_earned on question {question_id}"

@patch('router.router.verify_token')
@patch('router.router.valid_permission')
@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
@patch('controllers.exam_controller.call_ai_model')
def test_submit_and_correct_exam_with_ai(mock_call_ai_model, mock_get_user, mock_check_user_exists,
                                         mock_verify_token, mock_valid_permission):
    mock_check_user_exists.return_value = True
    mock_get_user.return_value = {"data": MOCK_USER}
    mock_call_ai_model.side_effect = [
        "{'points_earned': 3, 'feedback': 'Buena respuesta'}",  # For question correction
        "Buen trabajo general, segui asi."                      # For general feedback
    ]
    mock_valid_permission.return_value = MAIN_TEACHER_ROLE
    mock_verify_token.return_value = "123"

    # --- Step 0: Create course and module (preconditions) ---
    client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0})
    course_data = curso_ejemplo()
    response = client.post("/courses/", json=course_data)
    course = response.json()["data"]
    module_data = {
        "course_id": course["id"],
        "module_name": "Modulo de prueba",
        "module_description": "Modulo de prueba",
    }
    response = client.post("/courses/modules", json=module_data, headers={"Token": "algo"})
    module = response.json()["data"]

    response = client.post("/courses/enrollment", json={"user_id":MOCK_USER["uid"],"course_id":course["id"], "role":STUDENT_ROLE, "status":"In Progress"})
    assert response.status_code == 200
    enrollment_id = response.json()["data"]["id"]

    # --- Step 1: Create Exam ---
    exam_body = {
        "course_id": course["id"],
        "module_id": module["id"],
        "exam_name": "Test Exam",
        "exam_description": "Test Desc",
        "questions": [
            {
                "question": "Capital of Argentina?",
                "questionType": "MULTIPLE_CHOICE",
                "points": 3,
                "options": [
                    {"option_text": "Buenos Aires", "is_correct": True},
                    {"option_text": "Cordoba", "is_correct": False}
                ]
            },
            {
                "question": "Select programming languages",
                "questionType": "MULTIPLE_ANSWER",
                "points": 5,
                "options": [
                    {"option_text": "Python", "is_correct": True},
                    {"option_text": "HTML", "is_correct": False},
                    {"option_text": "Java", "is_correct": True}
                ]
            },
            {
                "question": "Remainder of 92 % 50",
                "questionType": "SINGLE_VALUE",
                "points": 2,
                "options": [
                    {"option_text": "42", "is_correct": True}
                ]
            },
            {
                "question": "Explain the Big Bang theory",
                "questionType": "TEXT_ANSWER",
                "points": 4
            }
        ]
    }

    response = client.post("/courses/exams", json=exam_body, headers={"Token": "algo"})
    assert response.status_code == 200
    exam_id = response.json()["data"]["id"]

    response = client.get(f"/courses/{course["id"]}/exams?module_id={module["id"]}&exam_id={exam_id}")
    assert response.status_code == 200
    exam_data = response.json()["data"][0]

    # Build answers dynamically based on question type
    answered_questions = []
    for question in exam_data["questions"]:
        q_type = question["questionType"]
        q_id = question["id"]

        if q_type == "MULTIPLE_CHOICE":
            # Pick the first option as chosen (example)
            option_id = question["options"][0]["id"]
            answered_questions.append({
                "question_id": q_id,
                "answer": "",  # Could be optional for MC
                "options_chosen": [{"id": option_id}]
            })
        elif q_type == "MULTIPLE_ANSWER":
            # Pick all options as chosen (example)
            option_ids = [{"id": opt["id"]} for opt in question["options"]]
            answered_questions.append({
                "question_id": q_id,
                "answer": "",
                "options_chosen": option_ids
            })
        elif q_type == "SINGLE_VALUE":
            # Just pick the first one (simulate form submission)
#            option_id = question["options"][0]["id"]
            answered_questions.append({
                "question_id": q_id,
                "answer": "41",
                "options_chosen": []
            })
        elif q_type == "TEXT_ANSWER":
            # Provide a manual answer
            answered_questions.append({
                "question_id": q_id,
                "answer": "The Big Bang theory is a cosmological model...",
                "options_chosen": []
            })

    # Submit the exam
    submit_body = {
        "user_id": enrollment_id,
        "course_id": course["id"],
        "module_id": module["id"],
        "exam_id": exam_id,
        "answered_questions": answered_questions
    }

    submit_response = client.post("/courses/submission", json=submit_body)
    assert submit_response.status_code == 200

    response = client.get(f"/courses/{course["id"]}/module/{module["id"]}/exam/{exam_id}/submission/{enrollment_id}")
    assert submit_response.status_code == 200

    submission_data = response.json()["submission"]

    # Manually correct all text answers
    correction = {
        "user_id": submission_data["user_id"],
        "course_id": submission_data["course_id"],
        "module_id": submission_data["module_id"],
        "exam_id": submission_data["exam_id"],
        "general_feedback":"Teacher Feedback",
        "questions_feedback": []
    }

    correction_response = client.post("/courses/corrections/ai", json=correction)
    correction_result = correction_response.json()
    assert correction_response.status_code == 200, f"Correction failed: {correction_result}"

    response = client.get(f"/courses/{course["id"]}/module/{module["id"]}/exam/{exam_id}/submission/{enrollment_id}")
    assert submit_response.status_code == 200

    submission_data = response.json()["submission"]
    print(submission_data)
    assert submission_data["corrected_date"] is not None and submission_data["corrected_date"] is not None
    submitted_date = datetime.fromisoformat(submission_data["submitted_date"])
    corrected_date = datetime.fromisoformat(submission_data["corrected_date"])

    assert submitted_date < corrected_date and corrected_date < datetime.now()

    for resolution in submission_data["resolutions"]:
        question_id = resolution["question_id"]
        feedback = resolution["feedback"]
        points_earned = resolution["points_earned"]

        assert feedback != None, f"Missing feedback on question {question_id}"
        assert points_earned != None, f"Missing points_earned on question {question_id}"

@patch('router.router.verify_token')
@patch('router.router.valid_permission')
@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_create_and_retrieve_activity(mock_get_user, mock_check_user_exists, mock_valid_permission,
                                      mock_verify_token):
    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER
    mock_valid_permission.return_value = MAIN_TEACHER_ROLE
    mock_verify_token.return_value = "123"

    # --- Step 0: Create course and module (preconditions) ---
    client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0})
    course_data = curso_ejemplo()
    response = client.post("/courses/", json=course_data)
    course = response.json()["data"]
    module_data = {
        "course_id": course["id"],
        "module_name": "Modulo de prueba",
        "module_description": "Modulo de prueba",
    }
    response = client.post("/courses/modules", json=module_data, headers={"Token": "algo"})
    module = response.json()["data"]

    # --- Step 1: Create Exam ---
    exam_body = {
        "course_id": course["id"],
        "module_id": module["id"],
        "exam_name": "Test Exam",
        "exam_description": "Test Desc",
        "isExam": False,
        "questions": [
            {
                "question": "Capital of Argentina?",
                "questionType": "MULTIPLE_CHOICE",
                "points": 3,
                "options": [
                    {"option_text": "Buenos Aires", "is_correct": True},
                    {"option_text": "Cordoba", "is_correct": False}
                ]
            },
            {
                "question": "Select programming languages",
                "questionType": "MULTIPLE_ANSWER",
                "points": 5,
                "options": [
                    {"option_text": "Python", "is_correct": True},
                    {"option_text": "HTML", "is_correct": False},
                    {"option_text": "Java", "is_correct": True}
                ]
            },
            {
                "question": "Answer with a single number",
                "questionType": "SINGLE_VALUE",
                "points": 2,
                "options": [
                    {"option_text": "42", "is_correct": True}
                ]
            },
            {
                "question": "Explain the Big Bang theory",
                "questionType": "TEXT_ANSWER",
                "points": 4
            }
        ]
    }

    response = client.post("/courses/exams", json=exam_body, headers={"Token": "algo"})
    assert response.status_code == 200
    exam_data = response.json()["data"]
    assert exam_data["exam_name"] == "Test Exam"
    assert exam_data["module_id"] == module["id"]
    assert exam_data["course_id"] == course["id"]
    exam_id = exam_data["id"]

    # --- Step 2: Get list of exams for the course ---
    list_response = client.get(f"/courses/{course["id"]}/activities")
    assert list_response.status_code == 200
    exams = list_response.json()["data"]
    assert any(e["id"] == exam_id for e in exams)

    list_response = client.get(f"/courses/{course["id"]}/exams")
    assert list_response.status_code == 200
    exams = list_response.json()["data"]
    assert not any(e["id"] == exam_id for e in exams)

    # --- Step 3: Get list of exams for the course and module ---
    list_response = client.get(f"/courses/{course["id"]}/activities?module_id={module["id"]}")
    assert list_response.status_code == 200
    exams = list_response.json()["data"]
    assert any(e["id"] == exam_id for e in exams)

    list_response = client.get(f"/courses/{course["id"]}/exams?module_id={module["id"]}")
    assert list_response.status_code == 200
    exams = list_response.json()["data"]
    assert not any(e["id"] == exam_id for e in exams)

    # --- Step 3: Get full exam with questions/options ---
    full_response = client.get(f"/courses/{course["id"]}/activities?module_id={module["id"]}&exam_id={exam_id}")
    assert full_response.status_code == 200
    exam = full_response.json()["data"][0]
    assert exam["exam_name"] == "Test Exam"
    assert len(exam["questions"]) == 4

    mc_question = exam["questions"][0]
    assert mc_question["questionType"] == "MULTIPLE_CHOICE"
    assert len(mc_question["options"]) == 2

    full_response = client.get(f"/courses/{course["id"]}/exams?module_id={module["id"]}&exam_id={exam_id}")
    assert full_response.status_code == 404


# Documents TESTS
@patch('router.router.verify_token')
@patch('router.router.valid_permission')
@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
def test_create_get_delete_resources(mock_get_user, mock_check_user_exists, mock_valid_permission,
                                     mock_verify_token):
    mock_check_user_exists.return_value = True
    mock_get_user.return_value = MOCK_USER
    mock_valid_permission.return_value = MAIN_TEACHER_ROLE
    mock_verify_token.return_value = "123"

    # --- Step 0: Create course and module (preconditions) ---
    client.post("/courses/subjects/", json={"title": "Test Subject","credits":3,"minimum_credits":0})
    course_data = curso_ejemplo()
    response = client.post("/courses/", json=course_data)
    course = response.json()["data"]
    module_data = {
        "course_id": course["id"],
        "module_name": "Modulo de prueba",
        "module_description": "Modulo de prueba",
    }
    response = client.post("/courses/modules", json=module_data, headers={"Token": "algo"})
    module = response.json()["data"]

    # --- Step 1: Create Document ---
    body = {
        "course_id":course["id"],
        "module_id":module["id"],
        "documents":{"doc1":"url1","doc2":"url2"}
    }
    response = client.post("/courses/resources/", json=body, headers={"Token": "algo"})
    assert response.status_code == 200
    assert response.json()["data"] == {"doc1":"url1","doc2":"url2"}

    response2 = client.get(f"/courses/{course["id"]}/module/{module["id"]}/resources")
    assert response2.status_code == 200
    assert response2.json() == response.json()

    body = {
        "course_id":course["id"],
        "module_id":module["id"],
        "documents":{"doc1":"url3","doc4":"url4"}       # Replace doc1 and create doc4
    }
    response = client.post("/courses/resources/", json=body, headers={"Token": "algo"})
    assert response.status_code == 200

    response = client.get(f"/courses/{course["id"]}/module/{module["id"]}/resources")
    assert response.status_code == 200
    assert response.json()["data"] == {"doc1":"url3","doc2":"url2","doc4":"url4"}

    response = client.delete(f"/courses/{course["id"]}/module/{module["id"]}/resources/doc1", headers={"Token": "algo"})
    assert response.status_code == 200

    response = client.get(f"/courses/{course["id"]}/module/{module["id"]}/resources")
    assert response.status_code == 200
    assert response.json()["data"] == {"doc2":"url2","doc4":"url4"}


@patch('router.router.verify_token')
@patch('router.router.valid_permission')
@patch('controllers.enrollment_controller.check_user_exists')
@patch('controllers.enrollment_controller.get_user')
@patch('controllers.stats_controller.get_user')
def test_course_stats(mock_get_user_stats, mock_get_user, mock_check_user_exists, mock_verify_token, mock_valid_permission):
    mock_check_user_exists.return_value = True
    mock_get_user_stats.return_value = MOCK_USER
    mock_get_user.return_value = MOCK_USER
    mock_verify_token.return_value = "123"
    mock_valid_permission.return_value = MAIN_TEACHER_ROLE

    # --- Step 0: Create course and module (preconditions) ---
    course_data = curso_ejemplo()
    response = client.post("/courses/", json=course_data)
    course = response.json()["data"]
    response = client.post("/courses/modules", json={
        "course_id": course["id"],
        "module_name": "Modulo de prueba",
        "module_description": "Modulo de prueba",
    } , headers={"Token": "algo"})
    module = response.json()["data"]

    # --- Step 1: Create Exam ---
    exam_body = {
        "course_id": course["id"],
        "module_id": module["id"],
        "exam_name": "Test Exam",
        "exam_description": "Test Desc",
        "questions": [
            {
                "question": "Capital of Argentina?",
                "questionType": "MULTIPLE_CHOICE",
                "points": 3,
                "options": [
                    {"option_text": "Buenos Aires", "is_correct": True},
                    {"option_text": "Córdoba", "is_correct": False}
                ]
            },
            {
                "question": "Select programming languages",
                "questionType": "MULTIPLE_ANSWER",
                "points": 5,
                "options": [
                    {"option_text": "Python", "is_correct": True},
                    {"option_text": "HTML", "is_correct": False},
                    {"option_text": "Java", "is_correct": True}
                ]
            }
        ]
    }

    # Create exam
    response = client.post("/courses/exams", json=exam_body, headers={"Token": "algo"})
    assert response.status_code == 200
    exam = response.json()["data"]
    response = client.get(f"/courses/{exam["course_id"]}/exams?module_id={exam["module_id"]}&exam_id={exam["id"]}")
    assert response.status_code == 200
    exam = response.json()["data"][0]

    # Inscripciones
    enrollments_ids = []
    for i in range(3):
        response = client.post("/courses/enrollment", json={"user_id":str(i),"course_id":course["id"], "role":STUDENT_ROLE, "status":"In Progress"})
        assert response.status_code == 200
        enrollments_ids.append(response.json()["data"]["id"])

    # Rendir examenes
    # 0: Acierta las dos, 1: Acierta la primera, 2: No acierta
    for i in range(3):
        answered_questions = [
            {
                "question_id": exam["questions"][0]["id"],
                "answer":"answer",
                "options_chosen": [ {"id":exam["questions"][0]["options"][0 if i < 2 else 1]["id"] }],
            },
            {
                "question_id": exam["questions"][1]["id"],
                "answer":"answer",
                "options_chosen": [ { "id": exam["questions"][1]["options"][0]["id"]},{"id": exam["questions"][1]["options"][2]} ] 
                    if id == 0 else [ { "id": exam["questions"][1]["options"][i]["id"] } for i in range(3)],
            }
        ]

        submit_body = {
            "user_id": enrollments_ids[i],
            "course_id": course["id"],
            "module_id": module["id"],
            "exam_id": exam["id"],
            "answered_questions": answered_questions
        }

        submit_response = client.post("/courses/submission", json=submit_body)
        assert submit_response.status_code == 200


    # GET STATS 
    response = client.get(f"/courses/{course["id"]}/stats")
    assert response.status_code == 200
    assert response.json() == [{'Exam_name': 'Test Exam', 'average_grade': 2.5}, {'course_average': 2.5, 'num_students': 3, 'best_student': 'Unknown Student', 'best_student_grade': 3.75, 'worst_student': 'Unknown Student', 'worst_student_grade': 0.0, 'percentage_all_exams': 1.0, 'percentage_no_exams': 0.0, 'percentage_some_exams': 0.0, 'performance_distribution': {'excellent': 0, 'good': 0, 'regular': 0, 'bad': 3}}]

    response = client.get(f"/courses/stats/global")
    assert response.status_code == 200
