import os

from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from sqlalchemy.orm import Session
from starlette_authlib.middleware import AuthlibMiddleware as SessionMiddleware

from fastapi_sso.sso.google import GoogleSSO

from apscheduler.schedulers.background import BackgroundScheduler

from app.auth.jwt import create_access_token
from app.crud import user as user_crud
from app.database import Base, engine, get_db
from app.schemas import user as user_schemas
from fastapi_mail import FastMail, MessageSchema
from app.schemas.book import BookCreate, BookUpdate, BookOut, BookAssignmentCreate, BookAssignmentOut
from app.crud import book as book_crud
from app.config.email import conf
from app.utils.reminder import send_due_soon_reminders

load_dotenv()

app = FastAPI(title="Library Management")

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY"))

Base.metadata.create_all(bind=engine)

# Google SSO configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

sso = GoogleSSO(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    redirect_uri="http://127.0.0.1:8000/auth/callback",
    allow_insecure_http=True,
)

# HTTP Basic authentication dependency for profile
basic_auth = HTTPBasic()

def get_current_user_basic(credentials: HTTPBasicCredentials = Depends(basic_auth), db: Session = Depends(get_db)):
    user = user_crud.get_user_by_username(db, credentials.username)
    if user is None or not user_crud.pwd_context.verify(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return user

def require_admin_basic(current_user=Depends(get_current_user_basic)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@app.post("/register", response_model=user_schemas.UserOut, status_code=status.HTTP_201_CREATED, tags=["user"])
async def register_user(user: user_schemas.UserCreate, db: Session = Depends(get_db)):
    """ Register a new user if username and email are not already taken, and send verification email """
    db_user = user_crud.get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user = user_crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = user_crud.create_user(db, user)
    if not new_user:
        raise HTTPException(status_code=400, detail="User creation failed")
    # Send verification email
    verification_link = f"http://127.0.0.1:8000/verify-email?token={new_user.verification_token}"
    message = MessageSchema(
        subject="Verify your email",
        recipients=[new_user.email],
        body=f"Please verify your email by clicking the following link: {verification_link}",
        subtype="plain",
    )
    fm = FastMail(conf)
    await fm.send_message(message)
    return new_user

# Email verification endpoint
@app.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(user_crud.user_models.User).filter(user_crud.user_models.User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user.is_email_verified = True
    user.verification_token = None
    db.commit()
    return {"message": "Email verified successfully"}

@app.post("/login", tags=["user"])
def login_user(user: user_schemas.UserLogin, db: Session = Depends(get_db)):
    """ Authenticate user and return JWT token if credentials are valid """
    db_user = user_crud.authenticate_user(db, user.username, user.password)
    if not db_user or isinstance(db_user, HTTPException):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    """ Generate JWT token """
    token_data = {"sub": db_user.username}
    access_token = create_access_token(token_data)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/login")
async def auth_init():
    """ Initialize Google SSO and redirect to Google login """
    async with sso:
        return await sso.get_login_redirect(params={"prompt": "consent", "access_type": "offline"})

@app.get("/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """ Handle Google SSO callback, create/update user, and return JWT token """
    async with sso:
        user = await sso.verify_and_process(request)
    username = user.email
    db_user = user_crud.get_user_by_username(db, username)
    if not db_user:
        new_user = user_schemas.UserCreate(
            username=username,
            email=username,
            password=os.urandom(16).hex(),
        )
        db_user = user_crud.create_user(db, new_user)
    token_data = {"sub": db_user.username}
    access_token = create_access_token(token_data)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/logout", tags=["user"])
def logout():
    """ Log out the user by deleting the session cookie """
    response = JSONResponse(content={"msg": "Logout successful"})
    response.delete_cookie(key="session")
    return response

# User profile endpoint (HTTP Basic Auth)
@app.get("/profile", response_model=user_schemas.UserOut, tags=["user"])
def get_profile(current_user=Depends(get_current_user_basic)):
    """Get the current user's profile information using username and password authentication."""
    return current_user

@app.post("/books/", response_model=BookOut, tags=["book"])
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    """ Create a new book """
    return book_crud.create_book(db, book)

@app.get("/books/{book_id}", response_model=BookOut, tags=["book"])
def read_book(book_id: int, db: Session = Depends(get_db)):
    """ Get a book by ID """
    db_book = book_crud.get_book(db, book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book

@app.get("/books/", response_model=list[BookOut], tags=["book"])
def read_books(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """ Get a list of books with pagination """
    return book_crud.get_books(db, skip=skip, limit=limit)

@app.patch("/books/{book_id}", response_model=BookOut, tags=["book"])
def update_book(book_id: int, book: BookUpdate, db: Session = Depends(get_db)):
    """ Update a book by ID """
    db_book = book_crud.update_book(db, book_id, book)
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book

@app.post("/books/{book_id}/assign", response_model=BookAssignmentOut, tags=["book"])
def assign_book(book_id: int, assignment: BookAssignmentCreate, db: Session = Depends(get_db)):
    """ Assign a book to a user """
    db_assignment = book_crud.assign_book(db, book_id, assignment)
    if not db_assignment:
        raise HTTPException(status_code=400, detail="Not enough books available or book not found")
    return db_assignment

@app.post("/books/assignment/{assignment_id}/return", response_model=BookAssignmentOut, tags=["book"])
def return_book(assignment_id: int, db: Session = Depends(get_db)):
    """ Return a book assignment """
    db_assignment = book_crud.return_book(db, assignment_id)
    if not db_assignment:
        raise HTTPException(status_code=404, detail="Assignment not found or already returned")
    return db_assignment

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_due_soon_reminders, "interval", days=1, args=[next(get_db())])
    scheduler.start()

start_scheduler()

@app.post("/password-reset/request")
async def password_reset_request(data: user_schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    success = await user_crud.request_password_reset(db, data.email)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Password reset code sent to your email."}

@app.post("/password-reset/confirm")
def password_reset_confirm(data: user_schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    success = user_crud.reset_password(db, data.email, data.code, data.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid code or code expired")
    return {"message": "Password has been reset successfully."}

@app.delete("/user/{user_id}", status_code=204, tags=["user"])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    success = user_crud.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

@app.patch("/users/{user_id}/deactivate", response_model=user_schemas.UserOut, tags=["user"])
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    user = user_crud.deactivate_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.patch("/users/{username}/role", response_model=user_schemas.UserOut)
def change_user_role(
    username: str,
    new_role: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin_basic),
):
    """ Change user role """
    user = user_crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if new_role not in ["admin", "librarian", "member"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    user.role = new_role
    db.commit()
    db.refresh(user)
    return user
