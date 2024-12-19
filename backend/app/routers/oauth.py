from datetime import datetime
from urllib.parse import unquote_plus

from database import get_db
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from models.user import GoogleUsernameSetup
from utils.google_auth import get_google_auth_url, get_google_token, verify_google_token
from utils.security import create_user_response, set_auth_cookies

router = APIRouter()


@router.get(
    "/auth/google",
    summary="Initiate Google Sign-In process",
    description="Initiates the Google Sign-In process by redirecting to Google's authorization page.",
)
async def login_google(request: Request):
    """Initiate Google Sign-In process"""
    redirect_uri = str(request.url_for("google_auth_callback"))
    return RedirectResponse(get_google_auth_url(redirect_uri))


@router.get(
    "/auth/google/callback",
    summary="Handle Google Sign-In callback",
    description="Handles the Google Sign-In callback by verifying the authorization code. Creates new user if needed.",
)
async def google_auth_callback(request: Request, response: Response):
    """Handle Google Sign-In callback"""
    try:
        params = dict(request.query_params)

        if "code" not in params:
            raise HTTPException(status_code=400, detail="Missing authorization code")

        code = unquote_plus(params["code"])
        redirect_uri = str(request.url_for("google_auth_callback"))

        token = get_google_token(code, redirect_uri)
        idinfo = verify_google_token(token)

        db = get_db()
        user = db.users.find_one({"email": idinfo["email"]})

        if not user:
            # Create new user without username
            new_user = {
                "email": idinfo["email"],
                "google_id": idinfo["sub"],
                "credits": 0,
                "email_verified": True,  # Google emails are pre-verified
                "created_at": datetime.utcnow(),
                "terms_accepted": False,
                "needs_username": True,  # Flag to indicate username needs to be set
            }
            result = db.users.insert_one(new_user)
            new_user["_id"] = result.inserted_id

            return JSONResponse({"needs_registration": True, "google_id": idinfo["sub"]})  # Only return google_id
        elif "google_id" not in user:
            db.users.update_one({"_id": user["_id"]}, {"$set": {"google_id": idinfo["sub"]}})

        if user.get("needs_username", False):  # Check if user needs to set username
            return JSONResponse({"needs_registration": True, "google_id": user["google_id"]})  # Only return google_id

        user_response = create_user_response(user, request)
        set_auth_cookies(response, user_response["access_token"], user_response["refresh_token"])

        return {"data": user_response["data"]}

    except Exception as e:
        print(f"Error in google_auth_callback: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error processing Google callback: {str(e)}")


@router.put(
    "/users/google",
    summary="Complete Google account setup",
    description="Sets the username for a Google-authenticated account.",
)
async def register_google(user: GoogleUsernameSetup, request: Request, response: Response):
    db = get_db()

    # Find the Google user using only google_id
    google_user = db.users.find_one({"google_id": user.google_id, "needs_username": True})

    if not google_user:
        raise HTTPException(status_code=404, detail="Google user not found")

    # Check if username already exists
    existing_username = db.users.find_one({"username": user.username})
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")

    # Set the username
    db.users.update_one(
        {"_id": google_user["_id"]}, {"$set": {"username": user.username}, "$unset": {"needs_username": ""}}
    )

    completed_user = db.users.find_one({"_id": google_user["_id"]})
    user_response = create_user_response(completed_user, request)
    set_auth_cookies(response, user_response["access_token"], user_response["refresh_token"])

    return {"data": user_response["data"]}  # Only return user data
