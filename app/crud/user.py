from fastapi import HTTPException

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from passlib.context import CryptContext

from app.schemas import user as user_schemas
from app.models import user as user_models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_username(db: Session, username: str):
    """ Retrieve a user from the database by username """
    return db.query(user_models.User).filter(user_models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    """ Retrieve a user from the database by email """
    return db.query(user_models.User).filter(user_models.User.email == email).first()

def create_user(db: Session, user: user_schemas.UserCreate):
    """ Create a new user in the database with a hashed password """
    hashed_password = pwd_context.hash(user.password)
    db_user = user_models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except IntegrityError as err:
        db.rollback()
        raise ValueError("Username or email already exists") from err
    else:
        return db_user

def authenticate_user(db: Session, username: str, password: str):
    """ Authenticate a user by username and password, and check if email is verified """
    user = get_user_by_username(db, username)
    if not user:
        return HTTPException(status_code=404, detail="User not found")
    if not pwd_context.verify(password, user.hashed_password):
        return HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_email_verified:
        return HTTPException(status_code=403, detail="Email not verified")
    return user
