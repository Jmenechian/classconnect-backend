import logging
from sqlalchemy.orm import Session, joinedload
from fastapi.exceptions import HTTPException
from models.correlative import Correlative
from models.error import not_found_error, subject_wrong_error
from models.subject import Subject, SubjectBase

# Extra logger in case FastAPI is not enough
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

def create_a_subject(subject_body: SubjectBase, db: Session):

    model = subject_body.model_dump()
    correlatives = model.pop("correlatives", None)

    if correlatives:    
        for correlative in correlatives:
            if not db.query(Subject).filter(correlative== Subject.id).first():
                logging.info(f"Correlative subject {correlative} doesn´t exists")
                raise HTTPException(status_code=404, detail=subject_wrong_error())

    db_subject = Subject(**model)
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)

    if correlatives:    
        for correlative in correlatives:
            correlative_model = {'subject_id': db_subject.id, 'correlative_id': correlative}
            db_correlative = Correlative(**correlative_model)
            db.add(db_correlative)

    db.commit()
    db.refresh(db_subject)

    return db_subject

def search_subject_by_name(subject_name: str, db: Session):
    result = db.query(Subject).options(joinedload(Subject.correlatives)).\
        filter(Subject.title.ilike(f"{subject_name}%")).limit(10).all()
    if not result:
        logging.info(f"Subject with title {subject_name} NOT FOUND")
        content = not_found_error(
            detail="The requested subject was not found on the server.",
            instance=f"/courses/subjects"
        )
        raise HTTPException(status_code=404,detail=content)
    return [serialize_subject(subject) for subject in result]

def search_subject_by_id(subject_id: int, db: Session):
    result = db.query(Subject).options(joinedload(Subject.correlatives))\
        .filter(Subject.id == subject_id).order_by(Subject.id.asc()).first()
    if not result:
        logging.info(f"Subject {subject_id} NOT FOUND")
        content = not_found_error(
            detail="The requested subject was not found on the server.",
            instance=f"/courses/subjects/{subject_id}"
        )
        raise HTTPException(status_code=404,detail=content)
    return result

def search_all_subjects(db: Session):
    result = db.query(Subject).options(joinedload(Subject.correlatives)).order_by(Subject.id.asc()).all()
    return [serialize_subject(subject) for subject in result]
    
def serialize_subject(subject: Subject) -> dict:
    return {
        "id": subject.id,
        "title": subject.title,
        "credits": subject.credits,
        "minimum_credits": subject.minimum_credits,
        "correlatives": [c.correlative_id for c in subject.correlatives],
    }
