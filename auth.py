import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import bcrypt
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv
from models import User, Role, AuditLog

# Load environment variables
load_dotenv()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-development-only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# In-memory user database (replace with a proper database in production)
USERS_FILE = "users.json"


def get_users() -> Dict[str, User]:
    if not os.path.exists(USERS_FILE):
        # Create default users if file doesn't exist
        default_users = {
            "admin": User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role=Role.EXECUTIVE,
                department="Management"
            ),
            "manager": User(
                username="manager",
                hashed_password=get_password_hash("manager123"),
                role=Role.MANAGER,
                department="HR"
            ),
            "employee": User(
                username="employee",
                hashed_password=get_password_hash("employee123"),
                role=Role.EMPLOYEE,
                department="Support"
            )
        }
        save_users(default_users)
        return default_users
    
    try:
        with open(USERS_FILE, "r") as f:
            users_data = json.load(f)
            users = {}
            for username, user_data in users_data.items():
                users[username] = User(**user_data)
            return users
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}


def save_users(users: Dict[str, User]):
    users_dict = {username: user.dict() for username, user in users.items()}
    with open(USERS_FILE, "w") as f:
        json.dump(users_dict, f, default=str)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str) -> Optional[User]:
    users = get_users()
    user = users.get(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    
    # Update last login time
    user.last_login = datetime.now()
    users[username] = user
    save_users(users)
    
    # Log the login action
    log_action(username, user.role, "login")
    
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def has_access_to_document(user_role: Role, document_access_roles: List[Role]) -> bool:
    """Check if a user with the given role can access a document"""
    if user_role == Role.EXECUTIVE:
        # Executives can access all documents
        return True
    
    # Other roles can only access documents if their role is in the access list
    return user_role in document_access_roles


def log_action(username: str, role: Role, action: str, details: Optional[Dict] = None):
    """Log user actions for audit purposes"""
    log = AuditLog(
        user_id=username,
        user_role=role,
        action=action,
        details=details
    )
    
    # In a real application, you would store this in a database
    # For now, we'll append to a log file
    with open("audit_log.json", "a") as f:
        f.write(json.dumps(log.dict(), default=str) + "\n")
    
    return log


def create_user(username: str, password: str, role: Role, department: str) -> User:
    """Create a new user"""
    users = get_users()
    if username in users:
        raise ValueError(f"User {username} already exists")
    
    new_user = User(
        username=username,
        hashed_password=get_password_hash(password),
        role=role,
        department=department
    )
    
    users[username] = new_user
    save_users(users)
    
    return new_user
