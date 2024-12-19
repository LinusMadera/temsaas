from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from utils.security import get_current_user

router = APIRouter()


@router.get(
    "/users/me",
    summary="Get user information",
    description="Returns the logged in user's information.",
)
async def get_user_info(current_user: str = Depends(get_current_user)):
    db = get_db()
    user = db.users.find_one({"email": current_user})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "email": user["email"],
        "username": user["username"],
        "created_at": user["created_at"].isoformat(),
        "credits": user.get("credits", 0),
        "email_verified": user.get("email_verified", False),
        "terms_accepted": user.get("terms_accepted", False),
    }


@router.get(
    "/usernames/availability",
    summary="Check username availability",
    description="Checks if a username is available for registration.\n\n"
    "Username must be 3-30 characters and can only contain letters, numbers and underscores. Usernames cannot be fully made up of numbers.\n\n"
    "A regular expression for this is: `^(?!^\d+$)(?=.{3,30}$)([a-zA-Z0-9_]+)$`",
)
async def check_username_availability(username: str):
    if len(username) < 3 or len(username) > 30:
        return {"available": False, "reason": "Username must be between 3 and 30 characters"}

    if not username.isascii():
        return {"available": False, "reason": "Username can only contain ASCII characters"}

    if not all(c.isalnum() or c == "_" for c in username):
        return {"available": False, "reason": "Username can only contain letters, numbers and underscores"}

    if username.replace("_", "").isdigit():
        return {"available": False, "reason": "Username cannot be made up of only numbers"}

    # If validation passes, check database
    db = get_db()
    existing_user = db.users.find_one({"username": username}, {"_id": 1})
    return {"available": existing_user is None}
