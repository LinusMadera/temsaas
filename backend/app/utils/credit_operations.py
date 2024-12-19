from database import get_db
from fastapi import HTTPException


def check_and_deduct_credits(user_email: str, required_credits: float):
    db = get_db()
    user = db.users.find_one({"email": user_email})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("credits", 0) < required_credits:
        raise HTTPException(status_code=403, detail="Insufficient credits")

    db.users.update_one({"_id": user["_id"]}, {"$inc": {"credits": -required_credits}})

    return True
