import csv
import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict
from passlib.context import CryptContext
from backend.config import DATA_DIR
from backend.schemas import User, UserCreate

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserLogic:
    USERS_FILE = DATA_DIR / "user.csv"
    HEADERS = [
        "id", "username", "hashed_password", "full_name", "role", 
        "allowed_gates", "can_manage_cameras", "can_add_vehicles", 
        "vehicle_add_code", "created_at"
    ]

    def __init__(self):
        self._ensure_file()

    def _ensure_file(self):
        if not self.USERS_FILE.parent.exists():
            self.USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not self.USERS_FILE.exists():
            with open(self.USERS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.HEADERS)
                writer.writeheader()
                # Create default admin user: admin / admin
                admin_user = {
                    "id": str(uuid.uuid4()),
                    "username": "admin",
                    "hashed_password": pwd_context.hash("admin"),
                    "full_name": "Administrator",
                    "role": "admin",
                    "allowed_gates": "*",
                    "can_manage_cameras": "True",
                    "can_add_vehicles": "True",
                    "vehicle_add_code": "ADMIN123",
                    "created_at": datetime.now().isoformat()
                }
                writer.writerow(admin_user)

    def get_users(self) -> List[Dict]:
        users = []
        if not self.USERS_FILE.exists():
            return users
        with open(self.USERS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                users.append(row)
        return users

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        users = self.get_users()
        for user in users:
            if user["username"] == username:
                return user
        return None

    def create_user(self, user_in: UserCreate) -> User:
        if self.get_user_by_username(user_in.username):
            raise Exception("Username already exists")
        
        user_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        new_user_data = {
            "id": user_id,
            "username": user_in.username,
            "hashed_password": pwd_context.hash(user_in.password),
            "full_name": user_in.full_name or "",
            "role": user_in.role,
            "allowed_gates": user_in.allowed_gates or "*",
            "can_manage_cameras": str(user_in.can_manage_cameras),
            "can_add_vehicles": str(user_in.can_add_vehicles),
            "vehicle_add_code": user_in.vehicle_add_code or "",
            "created_at": timestamp
        }
        
        with open(self.USERS_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.HEADERS)
            writer.writerow(new_user_data)
        
        return User(
            id=user_id,
            username=user_in.username,
            full_name=user_in.full_name,
            role=user_in.role,
            allowed_gates=new_user_data["allowed_gates"],
            can_manage_cameras=user_in.can_manage_cameras,
            can_add_vehicles=user_in.can_add_vehicles,
            vehicle_add_code=new_user_data["vehicle_add_code"],
            created_at=timestamp
        )

    def verify_password(self, plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    def delete_user(self, username: str) -> bool:
        users = self.get_users()
        found = False
        new_users = []
        for user in users:
            if user["username"] == username:
                found = True
                continue
            new_users.append(user)
        
        if not found:
            return False
            
        with open(self.USERS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.HEADERS)
            writer.writeheader()
            writer.writerows(new_users)
        return True

    def update_user(self, username: str, update_data: dict) -> Optional[dict]:
        users = self.get_users()
        found_idx = -1
        for i, u in enumerate(users):
            if u["username"] == username:
                found_idx = i
                break
        
        if found_idx == -1:
            return None
            
        user = users[found_idx]
        
        # Mapping frontend/schema keys to CSV headers if necessary, 
        # but here they match except for password -> hashed_password
        if "password" in update_data and update_data["password"]:
            user["hashed_password"] = pwd_context.hash(update_data["password"])
            del update_data["password"]
            
        for key, value in update_data.items():
            if key in self.HEADERS and key != "id" and key != "username":
                user[key] = str(value)
        
        users[found_idx] = user
        
        with open(self.USERS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.HEADERS)
            writer.writeheader()
            writer.writerows(users)
            
        return user

    def save_user(self, user_data: dict) -> bool:
        """Directly save/update user data from a synced payload."""
        users = self.get_users()
        username = user_data.get("username")
        if not username:
            return False
            
        found_idx = -1
        for i, u in enumerate(users):
            if u["username"] == username:
                found_idx = i
                break
        
        # Ensure all headers exist in the incoming data, or use defaults
        data_to_save = {h: user_data.get(h, "") for h in self.HEADERS}
        
        if found_idx >= 0:
            users[found_idx] = data_to_save
        else:
            users.append(data_to_save)
            
        with open(self.USERS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.HEADERS)
            writer.writeheader()
            writer.writerows(users)
        return True
