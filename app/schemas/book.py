import enum

from pydantic import BaseModel
from datetime import datetime

class AssignmentType(str, enum.Enum):
    loan = "loan"
    salon = "salon"
    sale = "sale"

class BookBase(BaseModel):
    title: str
    author: str
    description: str | None = None
    isbn: str | None = None
    assignment_type: AssignmentType
    total_count: int
    category_id: int
    tags: list[int] | None = None

class CategoryOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class TagOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: str | None
    author: str | None
    description: str | None
    isbn: str | None
    assignment_type: AssignmentType | None
    total_count: int | None
    category_id: int | None
    tags: list[int] | None = None

class BookAssignmentBase(BaseModel):
    user_id: int
    assignment_type: AssignmentType
    quantity: int

class BookAssignmentCreate(BookAssignmentBase):
    pass

class BookAssignmentOut(BookAssignmentBase):
    id: int
    assigned_at: datetime
    returned_at: datetime | None

    class Config:
        from_attributes = True

class BookOut(BookBase):
    id: int
    available_count: int
    created_at: datetime
    category: CategoryOut
    tags: list[TagOut]
    class Config:
        from_attributes = True
