from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from models.user import UserProfile, UserResponse
from utils.security import get_current_user
from utils.s3 import upload_file, delete_file
from database import get_db
from datetime import datetime
import uuid

router = APIRouter()

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: str = Depends(get_current_user)):
    db = get_db()
    user = db.users.find_one({"email": current_user})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        email=user["email"],
        username=user["username"],
        id=str(user["_id"]),
        credits=user.get("credits", 0),
        email_verified=user.get("email_verified", False),
        created_at=user.get("created_at", datetime.utcnow()),
        terms_accepted=user.get("terms_accepted", False),
        profile=user.get("profile", {})
    )

@router.put("/profile")
async def update_profile(profile: UserProfile, current_user: str = Depends(get_current_user)):
    db = get_db()
    result = db.users.update_one(
        {"email": current_user},
        {
            "$set": {
                "profile": profile.dict(exclude_unset=True),
                "onboarding_completed": True
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Profile update failed")
    
    return {"message": "Profile updated successfully"}

@router.post("/profile/picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    db = get_db()
    user = db.users.find_one({"email": current_user})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete old profile picture if it exists
    if user.get("profile", {}).get("pfp_url"):
        old_file_name = user["profile"]["pfp_url"].split("/")[-1]
        try:
            delete_file(old_file_name)
        except:
            pass  # Ignore errors when deleting old file

    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    file_name = f"pfp/{user['_id']}/{uuid.uuid4()}.{file_extension}"
    
    # Read and upload file
    contents = await file.read()
    pfp_url = upload_file(contents, file_name, file.content_type)
    
    # Update user profile with new URL
    db.users.update_one(
        {"email": current_user},
        {"$set": {"profile.pfp_url": pfp_url}}
    )
    
    return {"message": "Profile picture uploaded successfully", "url": pfp_url}

@router.get("/onboarding-status")
async def get_onboarding_status(current_user: str = Depends(get_current_user)):
    db = get_db()
    user = db.users.find_one({"email": current_user})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "onboarding_completed": user.get("onboarding_completed", False)
    }
