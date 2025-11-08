"""
Financial and subscription Pydantic schemas.

Includes Stripe integration for payments (Decision #66).
"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas import BaseSchema, TimestampMixin


class SubscriptionPlanResponse(BaseSchema, TimestampMixin):
    """
    Subscription plan response.

    Decision #55: Pricing strategy (monthly/annual tiers).
    """
    plan_id: UUID
    course_id: UUID
    plan_name: str
    plan_code: str
    description: Optional[str]
    billing_interval: str  # 'monthly' | 'annual' | 'lifetime'
    billing_interval_count: int
    price_amount: Decimal
    currency: str
    stripe_price_id: Optional[str]
    is_active: bool


class SubscriptionCreateRequest(BaseModel):
    """
    Create subscription request.

    User selects a plan and provides payment method.
    """
    plan_id: UUID
    payment_method_id: Optional[str] = None  # Stripe payment method ID


class SubscriptionResponse(BaseSchema, TimestampMixin):
    """
    Subscription response.

    Decision #66: Financial infrastructure with Stripe.
    """
    subscription_id: UUID
    user_id: UUID
    plan_id: UUID
    stripe_subscription_id: Optional[str]
    status: str  # 'active' | 'canceled' | 'past_due' | 'trialing' | 'incomplete'
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    started_at: datetime
    canceled_at: Optional[datetime]
    ended_at: Optional[datetime]


class SubscriptionCancelRequest(BaseModel):
    """
    Cancel subscription request.

    Can cancel immediately or at period end.
    """
    cancel_at_period_end: bool = True
    cancellation_reason: Optional[str] = None


class PaymentMethodCreate(BaseModel):
    """
    Payment method creation (Stripe token).

    Decision #66: PCI compliant storage (tokenized only).
    """
    stripe_payment_method_id: str


class PaymentMethodResponse(BaseSchema, TimestampMixin):
    """
    Payment method response (masked for security).

    Never returns full card number.
    """
    method_id: UUID
    user_id: UUID
    stripe_payment_method_id: str
    method_type: str  # 'card' | 'bank_account'
    card_brand: Optional[str]  # 'visa', 'mastercard', etc.
    card_last4: Optional[str]
    card_exp_month: Optional[int]
    card_exp_year: Optional[int]
    is_default: bool
    is_active: bool


class PaymentResponse(BaseSchema):
    """
    Payment response.

    Tracks individual payment transactions.
    """
    payment_id: UUID
    user_id: UUID
    subscription_id: Optional[UUID]
    stripe_payment_intent_id: Optional[str]
    stripe_charge_id: Optional[str]
    amount: Decimal
    currency: str
    status: str  # 'succeeded' | 'failed' | 'pending' | 'refunded' | 'disputed'
    payment_method_type: Optional[str]
    payment_method_brand: Optional[str]
    payment_method_last4: Optional[str]
    stripe_fee: Optional[Decimal]
    net_amount: Optional[Decimal]
    failure_code: Optional[str]
    failure_message: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime


class RefundCreateRequest(BaseModel):
    """
    Refund creation request (admin only).
    """
    payment_id: UUID
    amount: Optional[Decimal] = None  # Full refund if None
    reason: Optional[str] = Field(None, pattern="^(duplicate|fraudulent|requested_by_customer)$")


class RefundResponse(BaseSchema):
    """
    Refund response.
    """
    refund_id: UUID
    payment_id: UUID
    stripe_refund_id: Optional[str]
    amount: Decimal
    reason: Optional[str]
    status: str  # 'succeeded' | 'failed' | 'pending' | 'canceled'
    refunded_at: Optional[datetime]
    created_at: datetime


class ChargebackResponse(BaseSchema):
    """
    Chargeback (dispute) response.

    Tracks credit card chargebacks from customers.
    """
    chargeback_id: UUID
    user_id: UUID
    payment_id: UUID
    stripe_dispute_id: Optional[str]
    amount: Decimal
    reason: Optional[str]
    status: str  # 'warning_needs_response' | 'warning_under_review' | 'won' | 'lost'
    evidence_due_by: Optional[datetime]
    evidence_submitted: bool
    disputed_at: datetime
    resolved_at: Optional[datetime]
    created_at: datetime


class InvoiceResponse(BaseSchema):
    """
    Invoice response.

    Generated invoices for payments.
    """
    invoice_id: UUID
    user_id: UUID
    subscription_id: Optional[UUID]
    payment_id: Optional[UUID]
    stripe_invoice_id: Optional[str]
    invoice_number: str
    amount_due: Decimal
    amount_paid: Decimal
    status: str  # 'draft' | 'open' | 'paid' | 'void' | 'uncollectible'
    invoice_date: datetime
    due_date: Optional[datetime]
    paid_at: Optional[datetime]
    created_at: datetime


class RevenueEventResponse(BaseSchema):
    """
    Revenue event response (immutable audit trail).

    Decision #66: Immutable financial events for reporting.
    """
    event_id: UUID
    user_id: Optional[UUID]
    subscription_id: Optional[UUID]
    payment_id: Optional[UUID]
    event_type: str  # 'payment_succeeded' | 'refund_issued' | 'chargeback_lost'
    amount: Decimal  # Can be negative for refunds/chargebacks
    net_amount: Decimal  # After fees
    currency: str
    occurred_at: datetime
    created_at: datetime


class StripeWebhookEvent(BaseModel):
    """
    Stripe webhook event payload.

    Decision #66: Asynchronous webhook processing.
    """
    event_id: str
    event_type: str
    data: dict
