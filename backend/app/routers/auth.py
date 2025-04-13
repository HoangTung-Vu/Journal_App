# --- START OF FILE backend/app/routers/auth.py ---
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Annotated # Use Annotated for Depends

# Use relative imports
from .. import schemas, crud
from ..db import database, models
from ..core import security
from ..core.hashing import verify_password
from ..core.config import settings
# Import the type alias for dependency clarity
from ..core.security import DbSession, CurrentUser

router = APIRouter(
    prefix="/api/v1/auth", # Consistent prefix for all auth routes
    tags=["Authentication"],
    responses={401: {"description": "Unauthorized"}}, # Default response for this router
)

@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def register_user(user: schemas.UserCreate, db: DbSession):
    """
    Đăng ký người dùng mới.
    Kiểm tra xem email đã tồn tại chưa.
    """
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    created_user = crud.create_user(db=db, user=user)
    return created_user

# Use Annotated for Depends with OAuth2PasswordRequestForm
OAuth2Form = Annotated[OAuth2PasswordRequestForm, Depends()]

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2Form, db: DbSession):
    """
    Xác thực người dùng và trả về access token.
    FastAPI tự động lấy 'username' và 'password' từ form data.
    """
    user = crud.get_user_by_email(db, email=form_data.username) # OAuth2 form uses 'username' field for email
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}, # Required for 401 status code
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, # 'sub' (subject) is standard claim for user identifier
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: CurrentUser):
    """
    Lấy thông tin của người dùng hiện tại đã đăng nhập.
    Sử dụng dependency `get_current_active_user`.
    """
    # current_user đã được xác thực bởi dependency
    return current_user
# --- END OF FILE backend/app/routers/auth.py ---