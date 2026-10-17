from fastapi.exceptions import HTTPException
from controllers.course_controller import get_course_by_ID 
from models.course import CourseUpdate
from models.document import DocumentBase
from models.module import ModuleBase, Module
from models.error import not_found_error

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
import logging

# Extra logger in case FastAPI is not enough
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


def add_module(module: ModuleBase, db: Session):  # search how to detect invalid course
    """
    Adds module to the database
    """
    try:
        db_module = Module(**module.model_dump())
        db.add(db_module)
        db.commit()
        db.refresh(db_module)
        return {"data": db_module}
    except IntegrityError as e:
        db.rollback()
        content = not_found_error(
            detail="Integrity error, check input.",
            instance=f"/courses/modules"
        )
        raise HTTPException(status_code=404, detail=content)

def get_modules(course_id: int, db: Session):
    logging.info(f"Retrieving all modules for course {course_id}")
    if not get_course_by_ID(id=course_id,db=db):
        logging.info(f"Course {course_id} doesn´t exist")
        content = not_found_error(
            detail="The requested Course was not found on the server.",
            instance=f"/courses/{course_id}/modules"
        )
        raise HTTPException(status_code=404, detail=content)

    return db.query(Module).filter_by(course_id=course_id).order_by(Module.id.asc()).all()

def get_module_by_ID(module_id: int, course_id: int, db: Session):
    """
    Get module by course_id, module_id, return if found, 404 error if not
    """
    if not get_course_by_ID(id=course_id,db=db):
        logging.info(f"Course {course_id} doesn´t exist")
        content = not_found_error(
            detail="The requested Course was not found on the server.",
            instance=f"/courses/{course_id}/modules/{module_id}"
        )
        raise HTTPException(status_code=404, detail=content)

    db_module = db.query(Module).filter_by(course_id=course_id, id=module_id).first()
    if not db_module:
        logging.info(f"Module {module_id} of course {course_id} not found")
        content = not_found_error(
            detail="The requested Module was not found on the server.",
            instance=f"/courses/{course_id}/modules/{module_id}"
        )
        raise HTTPException(status_code=404, detail=content)

    logging.info(f"Module with id: {module_id} found")
    return db_module


def update_module_by_ID(module_id: int, course_id: int, course_update: CourseUpdate, db: Session):
    db_module = db.query(Module).filter_by(course_id=course_id, id=module_id).first()
    if not db_module:
        logging.info(f"Module {module_id} of course {course_id} not found")
        content = not_found_error(
            detail="The requested Module was not found on the server.",
            instance=f"/courses/{course_id}/modules/{module_id}"
        )
        raise HTTPException(status_code=404, detail=content)

    module_data = course_update.model_dump(exclude_unset=True)

    for field, value in module_data.items():
        setattr(db_module, field, value)

    db.commit()
    db.refresh(db_module)
    return {"data": db_module}


def delete_module_by_ID(module_id: int, course_id: int, db: Session):
    """
    Deletes module by ID, return success message if found, 404 error if not
    """
    db_module = db.query(Module).filter_by(course_id=course_id, id=module_id).first()
    if not db_module:
        logging.info(f"Module {module_id} of course {course_id} not found")
        content = not_found_error(
            detail="The requested Module was not found on the server.",
            instance=f"/courses/{course_id}/modules/{module_id}"
        )
        raise HTTPException(status_code=404, detail=content)

    db.delete(db_module)
    db.commit()

    logging.info(f"Module {module_id} of course {course_id} deleted")
    return {"message": "Module deleted successfully"}

def get_documents(course_id: int, module_id: int, db: Session):
    db_module = get_module_by_ID(course_id=course_id,module_id=module_id, db=db)    
    return db_module.educational_material or {}

def get_document(course_id: int, module_id: int, document_name: str, db: Session):
    documents: dict[str,str] = get_documents(course_id=course_id,module_id=module_id,db=db)
    document = documents.get(document_name)
    if not document:
        logging.info(f"Doc {document_name} module {module_id} course {course_id} not found")
        content = not_found_error(
            detail="The requested document was not found on the server.",
            instance=f"/courses/{course_id}/module/{module_id}/resources"
        )
        raise HTTPException(status_code=404, detail=content)
    return { document_name: document }

def create_documents(document_body: DocumentBase, db: Session):
    course_id = document_body.course_id
    module_id = document_body.module_id

    db_module = db.query(Module).filter_by(course_id=course_id, id=module_id).first()
    if not db_module:
        logging.info(f"Module {module_id} of course {course_id} not found")
        content = not_found_error(
            detail="The requested Module was not found on the server.",
            instance=f"/courses/{course_id}/modules/{module_id}"
        )
        raise HTTPException(status_code=404, detail=content)
    
    new_doc_keys = document_body.documents.keys()
            
    if db_module.educational_material:
        for key, value in db_module.educational_material.items():
            if key not in new_doc_keys:
                document_body.documents[key] = value
    
    db_module.educational_material = document_body.documents
    db.commit()
    db.refresh(db_module)
    return db_module.educational_material

def delete_resource_by_name(resource_name: str, course_id: int, module_id: int, db: Session):
    db_module = db.query(Module).filter_by(course_id=course_id, id=module_id).first()
    if not db_module:
        logging.info(f"Module {module_id} of course {course_id} not found")
        content = not_found_error(
            detail="The requested Module was not found on the server.",
            instance=f"/courses/{course_id}/modules/{module_id}/resources/{resource_name}"
        )
        raise HTTPException(status_code=404, detail=content)

    try:    
        resources = db_module.educational_material 
        resources.pop(resource_name)
        db_module.educational_material = resources
        db.commit()
        db.refresh(db_module)
        return {"data":db_module.educational_material}

    except SQLAlchemyError as e:
        db.rollback()
        content = not_found_error(
            detail=f"Database error: {str(e)}",
            instance=f"/courses/{course_id}/modules/{module_id}/resources/{resource_name}"
        )
        raise HTTPException(status_code=500, detail=content)

    except: 
        db.rollback()
        logging.info(f"Resource {resource_name} of course {course_id} module {module_id} of not found")
        content = not_found_error(
            detail="The requested resource was not found on the server.",
            instance=f"/courses/{course_id}/modules/{module_id}/resources/{resource_name}"
        )
        raise HTTPException(status_code=404, detail=content)




 