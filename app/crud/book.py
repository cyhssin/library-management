from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.models.book import Book, BookAssignment, Category, Tag
from app.schemas.book import BookCreate, BookUpdate, BookAssignmentCreate

def create_book(db: Session, book: BookCreate):
    db_category = db.query(Category).filter(Category.id == book.category_id).first()
    db_tags = db.query(Tag).filter(Tag.id.in_(book.tags)).all()
    db_book = Book(
        title = book.title,
        author = book.author,
        description = book.description,
        isbn = book.isbn,
        assignment_type = book.assignment_type,
        total_count = book.total_count,
        available_count = book.total_count,
        category=db_category,
        tags=db_tags,
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

def get_book(db: Session, book_id: int):
    return db.query(Book).filter(Book.id == book_id).first()

def get_books(db:Session, skip: int = 0, limit: int = 100):
    return db.query(Book).offset(skip).limit(limit).all()

def update_book(db: Session, book_id: int, book: BookUpdate):
    db_book = get_book(db, book_id)
    if not db_book:
        return "There is no such book"
    for filed, value in book.dict(exclude_unset=True).items():
        setattr(db_book, filed, value)
    db.commit()
    db.refresh(db_book)
    return db_book

def assign_book(db: Session, book_id: int, assignment: BookAssignmentCreate):
    db_book = get_book(db, book_id)
    if not db_book or db_book.available_count < assignment.quantity:
        return None
    db_assignment = BookAssignment(
        book_id=book_id,
        user_id=assignment.user_id,
        assignment_type=assignment.assignment_type,
        quantity=assignment.quantity,
        due_date=datetime.now() + timedelta(days=14),
    )
    db_book.available_count -= assignment.quantity
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    return db_assignment

def return_book(db: Session, assignment_id: int):
    db_assignment = db.query(BookAssignment).filter(BookAssignment.id == assignment_id).first()
    if not db_assignment or db_assignment.returned_at is not None:
        return None
    db_assignment.returned_at = datetime.now(tz=timezone.utc)
    db_assignment.book.available_count += db_assignment.quantity
    db.commit()
    db.refresh(db_assignment)
    return db_assignment

def create_category(db: Session, name: str):
    category = Category(name=name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

def create_tag(db: Session, name: str):
    tag = Tag(name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag
