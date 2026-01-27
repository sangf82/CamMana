from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from backend.schemas import User, UserCreate, UserLogin, Token, UserUpdate
from backend.data_process.user.logic import UserLogic

# Config for JWT
SECRET_KEY = "cam-mana-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

user_router = APIRouter(prefix="/api/user", tags=["user"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/login")
user_logic = UserLogic()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = user_logic.get_user_by_username(username)
    if user is None:
        raise credentials_exception
        
    # Filter None keys and convert string booleans
    clean_user = {k: v for k, v in user.items() if k is not None}
    if "can_manage_cameras" in clean_user: clean_user["can_manage_cameras"] = str(clean_user["can_manage_cameras"]).lower() == "true"
    if "can_add_vehicles" in clean_user: clean_user["can_add_vehicles"] = str(clean_user["can_add_vehicles"]).lower() == "true"
    
    return User(**clean_user)

@user_router.post("/register", response_model=User)
async def register(user_in: UserCreate):
    try:
        return user_logic.create_user(user_in)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@user_router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
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
    
    # Filter None keys and convert string booleans
    clean_user = {k: v for k, v in user.items() if k is not None}
    if "can_manage_cameras" in clean_user: clean_user["can_manage_cameras"] = str(clean_user["can_manage_cameras"]).lower() == "true"
    if "can_add_vehicles" in clean_user: clean_user["can_add_vehicles"] = str(clean_user["can_add_vehicles"]).lower() == "true"

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": User(**clean_user)
    }

@user_router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@user_router.get("", response_model=List[User])
async def list_users(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    users = user_logic.get_users()
    # Filter and clean users for response
    cleaned = []
    for u in users:
        clean_u = {k: v for k, v in u.items() if k is not None}
        if "can_manage_cameras" in clean_u: clean_u["can_manage_cameras"] = str(clean_u["can_manage_cameras"]).lower() == "true"
        if "can_add_vehicles" in clean_u: clean_u["can_add_vehicles"] = str(clean_u["can_add_vehicles"]).lower() == "true"
        cleaned.append(User(**clean_u))
    return cleaned

@user_router.delete("/{username}")
async def delete_user(username: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete super-admin")
    
    # Need to add delete_user to user_logic
    success = user_logic.delete_user(username)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}

@user_router.put("/{username}", response_model=User)
async def update_user(
    username: str, 
    update_in: UserUpdate, 
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
        
    updated = user_logic.update_user(username, update_in.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Filter and clean user data
    clean_u = {k: v for k, v in updated.items() if k is not None}
    if "can_manage_cameras" in clean_u: clean_u["can_manage_cameras"] = str(clean_u["can_manage_cameras"]).lower() == "true"
    if "can_add_vehicles" in clean_u: clean_u["can_add_vehicles"] = str(clean_u["can_add_vehicles"]).lower() == "true"
    
    return User(**clean_u)
