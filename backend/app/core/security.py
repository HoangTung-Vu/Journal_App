# --- START OF FILE backend/app/core/security.py ---
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated # Use Annotated for Depends

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# Use relative imports within the same package level
from .config import settings
from ..db import database, models
from ..schemas import schemas as user_schemas # Rename to avoid conflict
from ..crud import crud

# OAuth2PasswordBearer yêu cầu tokenUrl là đường dẫn tương đối đến endpoint token
# Đảm bảo nó khớp với prefix của auth router + đường dẫn của token endpoint
# Nếu auth router có prefix="/api/v1/auth", thì tokenUrl="api/v1/auth/token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                           db: Annotated[Session, Depends(database.get_db)]) -> models.User:
    """Giải mã token, xác thực và trả về user hiện tại."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
        # Use the renamed import for Pydantic schema
        token_data = user_schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    except Exception as e: # Catch potential Pydantic validation errors too
         print(f"Error decoding token or validating schema: {e}")
         raise credentials_exception


    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: Annotated[models.User, Depends(get_current_user)]) -> models.User:
    """
    Dependency để lấy user hiện tại và kiểm tra xem có active không (nếu cần).
    Hiện tại chỉ trả về user nếu token hợp lệ.
    """
    # Thêm logic kiểm tra user active nếu cần (ví dụ: if current_user.is_active:)
    # if not current_user.is_active: # Giả sử có trường is_active trong model User
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Type alias for dependency injection clarity
CurrentUser = Annotated[models.User, Depends(get_current_active_user)]
DbSession = Annotated[Session, Depends(database.get_db)]
# --- END OF FILE backend/app/core/security.py ---