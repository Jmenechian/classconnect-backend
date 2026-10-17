from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship

from models.base import Base
from models.constants import CORRELATIVE_TABLE_NAME, SUBJECT_TABLE_NAME

from sqlalchemy import Column, ForeignKey
from typing import List

class Correlative(Base):
    """
    Subject model to be stored in the database
    """

    __tablename__ = CORRELATIVE_TABLE_NAME

    subject_id: Mapped[int] = Column(ForeignKey(f"{SUBJECT_TABLE_NAME}.id", ondelete="CASCADE"), primary_key=True)
    correlative_id: Mapped[int] = Column(ForeignKey(f"{SUBJECT_TABLE_NAME}.id", ondelete="CASCADE"), primary_key=True)

    subject: Mapped["Subject"] = relationship(
        "Subject",
        foreign_keys=[subject_id],
        back_populates="correlatives"
    )

    correlative: Mapped["Subject"] = relationship(
        "Subject",
        foreign_keys=[correlative_id],
        back_populates="required_by"
    )