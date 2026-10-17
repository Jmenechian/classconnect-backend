from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.constants import FAVOURITES_TABLE_NAME, COURSE_TABLE_NAME


class Favourite(Base):
    """
    Favourite model to be stored in the database

    """
    __tablename__ = FAVOURITES_TABLE_NAME

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True, unique=True)
    course_id: Mapped[int] = Column(ForeignKey(f"{COURSE_TABLE_NAME}.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(primary_key=True)   # From ms-users

    course: Mapped["Course"] = relationship(back_populates="favourites")
