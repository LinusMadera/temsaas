from datetime import datetime
from math import ceil
from typing import Optional

import stripe
from bson import ObjectId
from config import (
    CANCEL_URL,
    COMPANY_NAME,
    CREDIT_VALUE,
    PAYMENT_MODE,
    SOFTWARE_NAME,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    SUBSCRIPTION_PRICE_ID,
    SUCCESS_URL,
)
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from models.payment import PaginatedPaymentResponse, PaymentCreate, PaymentResponse, PaymentType, SubscriptionStatus
from utils.security import get_current_user

router = APIRouter()
stripe.api_key = STRIPE_SECRET_KEY


@router.post(
    "/checkout",
    response_model=PaymentResponse,
    summary="Create Checkout Session",
    description="""
Creates a checkout session for the user\n
The parameter payment_type can be either `subscription` or `credit`\n
If payment_type is `credit`, the parameter amount is required\n
""",
)
async def create_checkout_session(payment: PaymentCreate, current_user: str = Depends(get_current_user)):
    db = get_db()
    user = db.users.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # print PAYMENT_MODE
    print(PAYMENT_MODE)

    if payment.payment_type == PaymentType.SUBSCRIPTION and PAYMENT_MODE.upper() != "SUBSCRIPTION":
        raise HTTPException(status_code=400, detail="Subscription payments are not enabled")

    if payment.payment_type == PaymentType.CREDIT and PAYMENT_MODE.upper() != "CREDIT":
        raise HTTPException(status_code=400, detail="Credit payments are not enabled")

    try:
        if payment.payment_type == PaymentType.SUBSCRIPTION:
            session = stripe.checkout.Session.create(
                customer_email=user["email"],
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": SUBSCRIPTION_PRICE_ID,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=SUCCESS_URL,
                cancel_url=CANCEL_URL,
                metadata={"user_id": str(user["_id"]), "payment_type": "subscription"},
            )
        else:  # CREDIT payment
            if not payment.amount:
                raise HTTPException(status_code=400, detail="Amount is required for credit payments")

            credits = float(payment.amount) / CREDIT_VALUE
            session = stripe.checkout.Session.create(
                customer_email=user["email"],
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"{COMPANY_NAME} | {SOFTWARE_NAME}",
                            },
                            "unit_amount": int(float(payment.amount) * 100),  # Convert to cents
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=SUCCESS_URL,
                cancel_url=CANCEL_URL,
                metadata={"user_id": str(user["_id"]), "payment_type": "credit", "credits": str(credits)},
            )

        # Store payment intent in database
        db.payments.insert_one(
            {
                "user_id": user["_id"],
                "session_id": session.id,
                "status": "pending",
                "amount": float(payment.amount) if payment.amount else None,
                "payment_type": payment.payment_type,
                "payment_date": datetime.utcnow(),
                "credits_added": False,
            }
        )

        return PaymentResponse(
            id=session.id,
            status="pending",
            amount=float(payment.amount) if payment.amount else None,
            payment_type=payment.payment_type,
            checkout_url=session.url,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/webhooks/stripe",
    summary="Stripe Webhook",
    description="Receives verified webhook events from Stripe. Should not be called manually.",
)
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    db = get_db()

    if event.type == "checkout.session.completed":
        session = event.data.object
        payment_type = session.metadata.get("payment_type")
        user_id = ObjectId(session.metadata.get("user_id"))

        if payment_type == "credit":
            credits = float(session.metadata.get("credits", 0))
            db.users.update_one({"_id": user_id}, {"$inc": {"credits": credits}})
            db.payments.update_one({"session_id": session.id}, {"$set": {"status": "completed", "credits_added": True}})
        elif payment_type == "subscription":
            subscription = stripe.Subscription.retrieve(session.subscription)

            db.users.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "subscription_status": "active",
                        "subscription_id": session.subscription,
                        "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
                    }
                },
            )
            db.payments.update_one({"session_id": session.id}, {"$set": {"status": "completed"}})

    elif event.type == "customer.subscription.deleted":
        subscription = event.data.object
        db.users.update_one(
            {"subscription_id": subscription.id},
            {"$set": {"subscription_status": "inactive", "subscription_id": None, "current_period_end": None}},
        )

    return {"status": "success"}


@router.get(
    "/users/subscription",
    response_model=SubscriptionStatus,
    summary="Get Subscription Status",
    description="Returns the subscription status of the user and the current period end date.",
)
async def get_subscription_status(current_user: str = Depends(get_current_user)):
    db = get_db()
    user = db.users.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current_period_end = None
    if user.get("current_period_end"):
        current_period_end = user["current_period_end"].isoformat()

    return SubscriptionStatus(
        is_active=user.get("subscription_status") == "active",
        current_period_end=current_period_end,
        cancel_at_period_end=user.get("cancel_at_period_end", False),
    )


@router.get(
    "/users/payments",
    response_model=PaginatedPaymentResponse,
    summary="Get Payments",
    description="Returns a list of past payments for the logged in user.",
)
async def get_payments(
    current_user: str = Depends(get_current_user), page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100)
):
    db = get_db()
    user = db.users.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    filter_query = {"user_id": user["_id"]}

    total = db.payments.count_documents(filter_query)
    total_pages = ceil(total / size)
    skip = (page - 1) * size

    payments = db.payments.find(filter_query).skip(skip).limit(size)

    items = [
        PaymentResponse(
            id=str(payment["session_id"]),
            status=payment["status"],
            amount=payment.get("amount"),
            payment_type=payment["payment_type"],
            checkout_url="",
        )
        for payment in payments
    ]

    return PaginatedPaymentResponse(items=items, total=total, page=page, size=size, pages=total_pages)


@router.get(
    "/users/credits",
    summary="Get User Credits",
    description="""
Returns the current number of credits the user has.\n
If the user has no credits or subscription mode is enabled, 0 credits are returned.
""",
)
async def get_user_credits(current_user: str = Depends(get_current_user)):
    db = get_db()
    user = db.users.find_one({"email": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"credits": user.get("credits", 0)}
