"""MailApp V3 — Modèles de données (Pydantic)"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime

# ─── Users ───────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    display_name: Optional[str] = None

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError('3 caracteres minimum')
        if not all(c.isalnum() or c in '_-' for c in v):
            raise ValueError('Caracteres autorises : lettres, chiffres, _ et -')
        return v

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('8 caracteres minimum')
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: Optional[str] = None
    role: str
    is_active: bool
    avatar_url: Optional[str] = None
    last_login: Optional[str] = None
    created_at: Optional[str] = None

# ─── Invitations ─────────────────────────────────────────────────────────────
class InvitationCreate(BaseModel):
    email: str
    role: str = 'utilisateur'  # admin, manager, utilisateur

class InvitationAccept(BaseModel):
    token: str
    username: str
    password: str
    display_name: Optional[str] = None

# ─── Projets ─────────────────────────────────────────────────────────────────
class ProjectCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None

class ProjectMemberAdd(BaseModel):
    user_id: int
    role: str = 'lecteur'  # chef, collaborateur, lecteur

class ProjectMemberUpdate(BaseModel):
    role: Optional[str] = None
    can_create_tasks: Optional[bool] = None
    can_assign_tasks: Optional[bool] = None
    can_upload_docs: Optional[bool] = None
    can_validate_docs: Optional[bool] = None
    can_manage_members: Optional[bool] = None
    can_send_emails: Optional[bool] = None

# ─── API ─────────────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: UserResponse

class MessageResponse(BaseModel):
    message: str
    success: bool = True
