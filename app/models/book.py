import enum

from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class AssignmentType(str, enum.Enum):
    loan = "loan"
    salon = "salon"
    sale = "sale"

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    description = Column(String)
    isbn = Column(String, unique=True, index=True)
    assignment_type = Column(Enum(AssignmentType), nullable=False)
    total_count = Column(Integer, nullable=False, default=1)
    available_count = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    assignments = relationship("BookAssignment", back_populates="book")

class BookAssignment(Base):
    __tablename__ = "book_assignments"
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignment_type = Column(Enum(AssignmentType), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    returned_at = Column(DateTime, nullable=True)
    quantity = Column(Integer, nullable=False, default=1)

    book = relationship("Book", back_populates="assignments")
    user = relationship("User")