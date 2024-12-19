import os
import uuid
from datetime import datetime, timedelta

import bcrypt
import jwt
from bson import ObjectId
from config import JWT_ALGORITHM, JWT_SECRET
from database import get_db
from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from models.user import UserResponse
from ua_parser import user_agent_parser

security = HTTPBearer()


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash+salt string"""
    try:
        password_bytes = plain_password.encode("utf-8")
        stored_hash_bytes = stored_hash.encode("utf-8")
        return bcrypt.checkpw(password=password_bytes, hashed_password=stored_hash_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate a secure hash of the password with a unique salt"""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)

    # Hash password with salt
    hashed = bcrypt.hashpw(password=pwd_bytes, salt=salt)

    # Return string representation
    return hashed.decode("utf-8")


def parse_user_agent(user_agent_string: str) -> dict:
    """Parse user agent string into structured data"""
    if not user_agent_string:
        return {}

    parsed = user_agent_parser.Parse(user_agent_string)

    # Helper function to build version string without "None"
    def build_version_string(family: str, major: str = None, minor: str = None) -> str:
        version = family
        if major:
            version += f" {major}"
            if minor:
                version += f".{minor}"
        return version

    return {
        "raw": user_agent_string,
        "browser": {
            "family": parsed["user_agent"]["family"],
            "major": parsed["user_agent"]["major"],
            "minor": parsed["user_agent"]["minor"],
            "patch": parsed["user_agent"]["patch"],
            "full": build_version_string(
                parsed["user_agent"]["family"], parsed["user_agent"]["major"], parsed["user_agent"]["minor"]
            ),
        },
        "os": {
            "family": parsed["os"]["family"],
            "major": parsed["os"]["major"],
            "minor": parsed["os"]["minor"],
            "patch": parsed["os"]["patch"],
            "patch_minor": parsed["os"]["patch_minor"],
            "full": build_version_string(parsed["os"]["family"], parsed["os"]["major"], parsed["os"]["minor"]),
        },
        "device": {
            "family": parsed["device"]["family"],
            "brand": parsed["device"]["brand"],
            "model": parsed["device"]["model"],
        },
    }


def create_session_tokens(user_id: str, email: str, request: Request) -> tuple[str, str]:
    """Create access and refresh tokens for a user session

    Args:
        user_id: User's ID
        email: User's email
        request: FastAPI Request object for session info
    """
    invalidate_id = str(uuid.uuid4())
    db = get_db()

    access_expires = datetime.utcnow() + timedelta(hours=1)
    access_token = jwt.encode(
        {
            "user_id": str(user_id),
            "sub": email,
            "exp": access_expires,
            "type": "access",
            "invalidate_id": invalidate_id,
            "jti": str(uuid.uuid4()),
            "iat": datetime.utcnow(),
            "nbf": datetime.utcnow(),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    refresh_expires = datetime.utcnow() + timedelta(days=30)
    refresh_token = jwt.encode(
        {"user_id": str(user_id), "exp": refresh_expires, "type": "refresh", "invalidate_id": invalidate_id},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    session_data = {
        "invalidate_id": invalidate_id,
        "user_id": ObjectId(user_id),
        "created_at": datetime.utcnow(),
        "expires_at": refresh_expires,
        "last_used": datetime.utcnow(),
        "is_active": True,
        "ip_address": request.client.host,
        "client_info": parse_user_agent(request.headers.get("user-agent")),
    }

    db.sessions.insert_one(session_data)

    return access_token, refresh_token


def verify_token(token: str, token_type: str = "access"):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        if payload.get("type") != token_type:
            raise HTTPException(status_code=401, detail="Invalid token type")

        db = get_db()
        session = db.sessions.find_one({"invalidate_id": payload.get("invalidate_id")})
        if not session:
            raise HTTPException(status_code=401, detail="Invalid session")

        db.sessions.update_one(
            {"invalidate_id": payload.get("invalidate_id")}, {"$set": {"last_used": datetime.utcnow()}}
        )

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def invalidate_session(invalidate_id: str):
    db = get_db()
    db.sessions.delete_one({"invalidate_id": invalidate_id})


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key="access_token", value=access_token, httponly=True, secure=True, samesite="lax", max_age=3600  # 1 hour
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="lax", max_age=2592000  # 30 days
    )


def clear_auth_cookies(response: Response):
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")


async def get_current_user(request: Request):
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(access_token, "access")
    return payload.get("sub")


def create_user_response(user: dict, request: Request) -> dict:
    """Create a standardized user response with tokens

    Args:
        user: User document from database
        request: FastAPI Request object for session info
    """
    user_response = UserResponse(
        email=user["email"],
        username=user["username"],
        id=str(user["_id"]),
        credits=user.get("credits", 0),
        email_verified=user.get("email_verified", False),
        created_at=user.get("created_at", datetime.utcnow()),
        terms_accepted=user.get("terms_accepted", False),
    )

    access_token, refresh_token = create_session_tokens(str(user["_id"]), user["email"], request)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "data": user_response.dict(),
    }
