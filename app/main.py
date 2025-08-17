from fastapi import FastAPI, Depends, status, HTTPException
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .schemas import user as user_schemas
from .crud import user as user_crud

app: FastAPI = FastAPI()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Library Management")

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

@app.post("/login", response_model=user_schemas.UserOut, tags=["user"])
def login_user(user: user_schemas.UserLogin, db: Session = Depends(get_db)):
    """ Authenticate user and return user info if credentials are valid """
    db_user = user_crud.authenticate_user(db, user.username, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return db_user

@app.post("/logout", tags=["user"])
def logout():
    """ Log out the user by deleting the session cookie """
    response = JSONResponse(content={"msg": "Logout successful"})
    response.delete_cookie(key="session")
    return response
