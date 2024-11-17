from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, HttpUrl

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

class Project(BaseModel):
    title: str
    description: str

class Experience(BaseModel):
    company: str
    years: float

class Certificate(BaseModel):
    title: str
    link: HttpUrl
    completion_date: datetime

class UserProfile(BaseModel):
    bio: Optional[str]
    personal_website: Optional[HttpUrl]
    linkedin: Optional[HttpUrl]
    years_of_experience: Optional[float]
    skills: Optional[List[str]]
    projects: Optional[List[Project]]
    experiences: Optional[List[Experience]]
    timezone: Optional[str]
    education: Optional[List[str]]
    certificates: Optional[List[Certificate]]
    availability: Optional[str]
    pfp_url: Optional[HttpUrl]
    onboarding_completed: Optional[bool] = False

class UserResponse(BaseModel):
    email: EmailStr
    username: str
    id: str
    credits: int
    email_verified: bool
    created_at: datetime
    terms_accepted: bool
    profile: Optional[UserProfile]