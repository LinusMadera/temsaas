from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from models.user import UserAcceptTerms
from utils.security import get_current_user

router = APIRouter()


@router.post(
    "/accept-terms",
    summary="Accept Terms and Conditions",
    description="Updates the user's acceptance status for terms and conditions.",
)
async def accept_terms(terms: UserAcceptTerms, current_user: str = Depends(get_current_user)):
    db = get_db()
    user = db.users.find_one({"email": current_user})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.users.update_one({"email": current_user}, {"$set": {"terms_accepted": terms.accept}})

    return {"message": "Terms and conditions acceptance status updated", "terms_accepted": terms.accept}
