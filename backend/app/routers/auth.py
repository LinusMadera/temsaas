import asyncio
from datetime import datetime, timedelta

import jwt
from bson import ObjectId
from config import JWT_ALGORITHM, JWT_SECRET
from database import get_db
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from models.user import UserCreate, UserLogin
from utils.email_utils import create_verification_token, send_verification_email, verify_email_token
from utils.security import (
    clear_auth_cookies,
    create_session_tokens,
    create_user_response,
    get_current_user,
    get_password_hash,
    invalidate_session,
    set_auth_cookies,
    verify_password,
    verify_token,
)

router = APIRouter()
security = HTTPBearer()


async def send_email_async(to_email: str, token: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, send_verification_email, to_email, token)


@router.post(
    "/users",
    summary="Register a new user",
    description="Registers a new user and sends a verification email.",
)
async def register(user: UserCreate, background_tasks: BackgroundTasks, request: Request, response: Response):
    db = get_db()
    existing_user = db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = {
        "email": user.email,
        "username": user.username,
        "password": hashed_password,
        "credits": 0,
        "email_verified": False,
        "created_at": datetime.utcnow(),
        "terms_accepted": False,
    }
    result = db.users.insert_one(new_user)
    new_user["_id"] = result.inserted_id

    verification_token = create_verification_token(user.email)
    background_tasks.add_task(send_email_async, user.email, verification_token)

    user_response = create_user_response(new_user, request)
    set_auth_cookies(response, user_response["access_token"], user_response["refresh_token"])

    return {"data": user_response["data"]}


@router.post(
    "/sessions",
    summary="Login with email and password",
    description="""
Logs in a user with their email and password.\n
If successful, HTTPOnly cookies are set for access and refresh tokens.\n
The user must have their email verified to login.
""",
)
async def login(response: Response, request: Request, user: UserLogin):
    db = get_db()
    db_user = db.users.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not db_user.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified")

    user_response = create_user_response(db_user, request)
    set_auth_cookies(response, user_response["access_token"], user_response["refresh_token"])

    return {"data": user_response["data"]}


@router.post(
    "/sessions/refresh",
    summary="Refresh access token",
    description="Refreshes the access token using the refresh token.",
)
async def refresh_token(response: Response, request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        payload = verify_token(refresh_token, "refresh")
        user_id = payload.get("user_id")
        invalidate_id = payload.get("invalidate_id")

        db = get_db()
        user = db.users.find_one({"_id": ObjectId(user_id)})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        access_token = jwt.encode(
            {
                "user_id": str(user["_id"]),
                "sub": user["email"],
                "exp": datetime.utcnow() + timedelta(hours=1),
                "type": "access",
                "invalidate_id": invalidate_id,
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )

        set_auth_cookies(response, access_token, refresh_token)
        return {"message": "Token refreshed successfully"}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.delete(
    "/sessions",
    summary="Logout a user",
    description="Logs out a user by invalidating the access token and clearing auth cookies.",
)
async def logout(response: Response, request: Request):
    access_token = request.cookies.get("access_token")
    if access_token:
        try:
            payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            invalidate_id = payload.get("invalidate_id")

            if invalidate_id:
                invalidate_session(invalidate_id)
        except jwt.InvalidTokenError:
            pass

    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.put(
    "/users/email/verify",
    summary="Verify email address",
    description="""
Verifies the email address using a verification token.\n
The verification token is sent via email to the user in the registration process.
""",
)
async def verify_email(token: str):
    email = verify_email_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    db = get_db()
    result = db.users.update_one({"email": email}, {"$set": {"email_verified": True}})

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Email verified successfully"}


@router.post(
    "/users/email/verify/resend",
    summary="Resend verification email",
    description="If the user's email was not verified, triggers a new verification email to be sent.",
)
async def resend_verification(email: str, background_tasks: BackgroundTasks):
    db = get_db()
    user = db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("email_verified", False):
        raise HTTPException(status_code=400, detail="Email already verified")

    verification_token = create_verification_token(email)
    background_tasks.add_task(send_email_async, email, verification_token)

    return {"message": "Verification email resent"}
