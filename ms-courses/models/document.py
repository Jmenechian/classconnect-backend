from pydantic import BaseModel

class DocumentBase(BaseModel):
    course_id: int
    module_id: int
    documents: dict[str,str]

# Wrapper for the POST
class DocumentsResponseWrapper(BaseModel):
    """
    A full document with a wrapper for the POST
    """

    data: DocumentBase


