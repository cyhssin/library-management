import os

from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session
from starlette_authlib.middleware import AuthlibMiddleware as SessionMiddleware

from fastapi_sso.sso.google import GoogleSSO

from app.auth.jwt import create_access_token
from app.crud import user as user_crud
from app.database import Base, engine, get_db
from app.schemas import user as user_schemas

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

@app.post("/register", response_model=user_schemas.UserOut, status_code=status.HTTP_201_CREATED, tags=["user"])
def register_user(user: user_schemas.UserCreate, db: Session = Depends(get_db)):
    """ Register a new user if username and email are not already taken """
    db_user = user_crud.get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user = user_crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = user_crud.create_user(db, user)
    if not new_user:
        raise HTTPException(status_code=400, detail="User creation failed")
    return new_user

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
