from database.data import SessionLocal


def get_db():  # no se si queda aca o en router
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
