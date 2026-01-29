"""
User API Endpoints

Provides endpoints for:
- User registration and login
- JWT authentication
- User management (CRUD)
"""

from datetime import datetime, timedelta
from typing import Optional, List
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import httpx

from backend.schemas import User, UserCreate, UserLogin, Token, UserUpdate
from backend.data_process.user.logic import UserLogic
from backend.settings import settings

logger = logging.getLogger(__name__)

# JWT Configuration from settings
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_access_token_expire_minutes

user_router = APIRouter(prefix="/api/user", tags=["user"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/login")
user_logic = UserLogic()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Dependency to get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username or not isinstance(username, str):
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = user_logic.get_user_by_username(username)
    if user is None:
        raise credentials_exception
        
    # Filter None keys and convert string booleans
    clean_user = {k: v for k, v in user.items() if k is not None}
    if "can_manage_cameras" in clean_user:
        clean_user["can_manage_cameras"] = str(clean_user["can_manage_cameras"]).lower() == "true"
    if "can_add_vehicles" in clean_user:
        clean_user["can_add_vehicles"] = str(clean_user["can_add_vehicles"]).lower() == "true"
    
    return User(**clean_user)


def _clean_user_response(user_data: dict) -> User:
    """Clean user data for API response."""
    clean_u = {k: v for k, v in user_data.items() if k is not None}
    if "can_manage_cameras" in clean_u:
        clean_u["can_manage_cameras"] = str(clean_u["can_manage_cameras"]).lower() == "true"
    if "can_add_vehicles" in clean_u:
        clean_u["can_add_vehicles"] = str(clean_u["can_add_vehicles"]).lower() == "true"
    return User(**clean_u)


@user_router.post("/register", response_model=User)
async def register(user_in: UserCreate):
    """Register a new user."""
    try:
        return user_logic.create_user(user_in)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@user_router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return JWT token."""
    from backend.sync_process.sync.proxy import is_client_mode, get_master_url
    
    # If in Client mode, proxy login to Master
    if is_client_mode():
        master_url = get_master_url()
        if master_url:
            try:
                logger.info(f"[Login] Proxying login request to Master: {master_url}")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{master_url}/api/user/login",
                        data={
                            "username": form_data.username,
                            "password": form_data.password
                        }
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"[Login] Successfully authenticated via Master")
                        return response.json()
                    else:
                        error_detail = "Incorrect username or password"
                        try:
                            error_data = response.json()
                            error_detail = error_data.get("detail", error_detail)
                        except:
                            pass
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=error_detail,
                            headers={"WWW-Authenticate": "Bearer"},
                        )
            except httpx.RequestError as e:
                logger.error(f"[Login] Failed to reach Master: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Không thể kết nối đến Master tại {master_url}",
                )
    
    # Local authentication (Master mode or fallback)
    user = user_logic.get_user_by_username(form_data.username)
    if not user or not user_logic.verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": _clean_user_response(user)
    }


@user_router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return current_user


@user_router.get("", response_model=List[User])
async def list_users(request: Request, current_user: User = Depends(get_current_user)):
    """List all users (admin only). Proxies to Master in Client mode."""
    # Proxy to master if in client mode
    from backend.sync_process.sync.proxy import is_client_mode, proxy_get
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info("[User] Client mode: Proxying list_users to Master")
        result = await proxy_get("/api/user", token=token)
        if result is not None:
             return result

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    users = user_logic.get_users()
    return [_clean_user_response(u) for u in users]


@user_router.delete("/{username}")
async def delete_user(request: Request, username: str, current_user: User = Depends(get_current_user)):
    """Delete a user (admin only). Proxies to Master in Client mode."""
    from backend.sync_process.sync.proxy import is_client_mode, proxy_delete
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info(f"[User] Client mode: Proxying delete_user({username}) to Master")
        success = await proxy_delete(f"/api/user/{username}", token=token)
        if success:
            return {"message": "User deleted"}
        raise HTTPException(status_code=503, detail="Cannot connect to master node")

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete super-admin")
    
    success = user_logic.delete_user(username)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}


@user_router.put("/{username}", response_model=User)
async def update_user(
    request: Request,
    username: str, 
    update_in: UserUpdate, 
    current_user: User = Depends(get_current_user)
):
    """Update a user (admin only). Proxies to Master in Client mode."""
    from backend.sync_process.sync.proxy import is_client_mode, proxy_put
    if is_client_mode():
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        logger.info(f"[User] Client mode: Proxying update_user({username}) to Master")
        result = await proxy_put(f"/api/user/{username}", update_in.model_dump(exclude_unset=True), token=token)
        if result is not None:
             return result
        raise HTTPException(status_code=503, detail="Cannot connect to master node")

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
        
    updated = user_logic.update_user(username, update_in.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
        
    return _clean_user_response(updated)
