from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class PaymentType(str, Enum):
    CREDIT = "credit"
    SUBSCRIPTION = "subscription"

class PaymentCreate(BaseModel):
    amount: Optional[Decimal] = Field(None, decimal_places=2)
    payment_type: PaymentType

class PaymentResponse(BaseModel):
    id: str
    status: str
    amount: Optional[float]
    payment_type: PaymentType
    checkout_url: str

    class Config:
        json_encoders = {
            Decimal: float
        }

class PaginatedPaymentResponse(BaseModel):
    items: List[PaymentResponse]
    total: int
    page: int
    size: int
    pages: int

class SubscriptionStatus(BaseModel):
    is_active: bool
    current_period_end: Optional[str]
    cancel_at_period_end: bool