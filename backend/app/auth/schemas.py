import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth.models import UserRole, UserStatus

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email_format(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_REGEX.match(email):
        raise ValueError("invalid email format")
    return email


class UserRegister(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.WORKER

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_format(v)


class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_format(v)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: uuid.UUID
    exp: int
    type: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: UserRole
    status: UserStatus
    created_at: datetime
