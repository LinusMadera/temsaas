from database import get_db
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from models.user import UserChangePassword, UserResetPassword
from utils.email_utils import create_password_reset_token, send_password_reset_email, verify_password_reset_token
from utils.security import get_current_user, get_password_hash, verify_password

router = APIRouter()


@router.post(
    "/password/reset-requests",
    summary="Request password reset",
    description="Sends a password reset email to the user's email address.",
)
async def forgot_password(email: str, background_tasks: BackgroundTasks):
    db = get_db()
    user = db.users.find_one({"email": email})
    if not user:
        # Return success even if email doesn't exist to prevent email enumeration
        return {"message": "If the email exists, a password reset link will be sent"}

    reset_token = create_password_reset_token(email)
    background_tasks.add_task(send_password_reset_email, email, reset_token)

    return {"message": "If the email exists, a password reset link will be sent"}


@router.put(
    "/password/reset",
    summary="Reset password using token",
    description="Resets the user's password using a valid reset token. Works for both local and Google users.",
)
async def reset_password(token: str, user_data: UserResetPassword):
    email = verify_password_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    db = get_db()
    user = db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Set the password - this works for both Google users (adding local auth)
    # and local users (changing existing password)
    new_hashed_password = get_password_hash(user_data.new_password)
    db.users.update_one({"email": email}, {"$set": {"password": new_hashed_password}})

    return {"message": "Password set successfully"}


@router.put(
    "/users/password",
    summary="Change user password",
    description="Changes the user's password if the old password is correct. Only works for users with local passwords.",
)
async def change_password(user_data: UserChangePassword, current_user: str = Depends(get_current_user)):
    db = get_db()
    db_user = db.users.find_one({"email": current_user})

    # Check if user exists and has a local password
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # If user is Google-only (no password field), don't allow password change
    if "password" not in db_user:
        raise HTTPException(
            status_code=400,
            detail="Cannot change password for Google account. Please use 'Forgot Password' to set up a password.",
        )

    # Verify old password for local users
    if not verify_password(user_data.old_password, db_user["password"]):
        raise HTTPException(status_code=400, detail="Incorrect password")

    new_hashed_password = get_password_hash(user_data.new_password)
    db.users.update_one({"email": current_user}, {"$set": {"password": new_hashed_password}})
    return {"message": "Password changed successfully"}
