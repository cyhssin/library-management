import secrets
import random

from fastapi import HTTPException

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from passlib.context import CryptContext

from datetime import datetime, timedelta

from fastapi_mail import FastMail, MessageSchema

from app.schemas import user as user_schemas
from app.models import user as user_models
from app.config.email import conf

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_username(db: Session, username: str):
    """ Retrieve a user from the database by username """
    return db.query(user_models.User).filter(user_models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    """ Retrieve a user from the database by email """
    return db.query(user_models.User).filter(user_models.User.email == email).first()

def create_user(db: Session, user: user_schemas.UserCreate):
    """ Create a new user in the database with a hashed password and verification token """
    hashed_password = pwd_context.hash(user.password)
    verification_token = secrets.token_urlsafe(32)
    db_user = user_models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        verification_token=verification_token,
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

async def request_password_reset(db: Session, email: str):
    user = db.query(user_models.User).filter(user_models.User.email == email).first()
    if not user:
        return False
    code = str(random.randint(10000, 99999))
    user.reset_code = code
    user.reset_code_expiry = datetime.now() + timedelta(minutes=15)
    db.commit()
    # Send email
    message = MessageSchema(
        subject="Your Password Reset Code",
        recipients=[user.email],
        body=f"Your password reset code is: {code}",
        subtype="plain",
    )
    fm = FastMail(conf)
    await fm.send_message(message)
    return True

def reset_password(db: Session, email: str, code: str, new_password: str):
    user = db.query(user_models.User).filter(user_models.User.email == email).first()
    if not user or user.reset_code != code or user.reset_code_expiry < datetime.now():
        return False
    user.hashed_password = pwd_context.hash(new_password)
    user.reset_code = None
    user.reset_code_expiry = None
    db.commit()
    return True

def delete_user(db: Session, user_id: int):
    user = db.query(user_models.User).filter(user_models.User.id == user_id).first()
    if not user:
        return "There is no user with such an id"
    db.delete(user)
    db.commit()
    return True

def deactivate_user(db: Session, user_id: int):
    user = db.query(user_models.User).filter(user_models.User.id == user_id).first()
    if not user:
        return "There is no user with such an id"
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
