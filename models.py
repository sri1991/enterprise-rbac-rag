from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class Role(str, Enum):
    EXECUTIVE = "Executive"
    MANAGER = "Manager"
    EMPLOYEE = "Employee"


class User(BaseModel):
    username: str
    hashed_password: str
    role: Role
    department: str
    created_at: datetime = datetime.now()
    last_login: Optional[datetime] = None


class Document(BaseModel):
    id: str
    title: str
    content: str
    metadata: Dict[str, Any]
    access_roles: List[Role]
    uploaded_by: str
    uploaded_at: datetime = datetime.now()
    last_modified: datetime = datetime.now()


class AuditLog(BaseModel):
    user_id: str
    user_role: Role
    action: str
    timestamp: datetime = datetime.now()
    details: Optional[Dict[str, Any]] = None
