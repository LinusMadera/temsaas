from datetime import datetime, timedelta

from database import get_db
from fastapi import HTTPException


def get_paid_user(current_user: str, days: int):
    db = get_db()
    user = db.users.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    recent_payment = db.payments.find_one(
        {
            "user_id": user["_id"],
            "status": "approved",
            "payment_date": {"$gte": datetime.utcnow() - timedelta(days=days)},
        }
    )

    if not recent_payment:
        raise HTTPException(status_code=403, detail=f"Paid feature: No payment found in the last {days} days")

    return True
