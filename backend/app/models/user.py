from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserChangePassword(BaseModel):
    old_password: str
    new_password: str

class UserResponse(BaseModel):
    email: EmailStr
    username: str
    id: str
    credits: float
    email_verified: bool
    created_at: datetime
    terms_accepted: bool

class UserAddCredits(BaseModel):
    amount: float
    payment_method: str  # 'credit_card' or 'pix'

class GoogleLogin(BaseModel):
    token: str

class UserAcceptTerms(BaseModel):
    accept: bool

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    data: UserResponse

class User(BaseModel):
    email: EmailStr
    hashed_password: str
    credits: float = 0
    subscription_status: Optional[str] = None
    subscription_id: Optional[str] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False