# database/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
from models import course, enrollment, module, correlative
from models.exams import exam, question, questionOption
from models.exams import resolution, resolutionOption, submission

environment = os.environ["ENVIRONMENT"]
if environment == "development":
    dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    DB_USERNAME = os.environ["DB_USERNAME"]
    DB_PASSWORD = os.environ["DB_PASSWORD"]
    DB_URL = os.environ["DB_URL"]
    DATABASE_URL = f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_URL}"
elif environment == "solo":
    DATABASE_URL = os.environ["DB_URL"]
else: # "production"
    # Leer DATABASE_URL directamente desde Heroku
    DATABASE_URL = os.environ["DATABASE_URL"]
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)
