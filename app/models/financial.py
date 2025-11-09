"""
Financial models: Subscription, Payment, Refund, Chargeback, etc.

Complete Stripe integration for payments (Decision #66).
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, DECIMAL, CheckConstraint, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
import uuid


class SubscriptionPlan(Base):
    """
    Available subscription plans (monthly, annual, etc.)
    """
    __tablename__ = "subscription_plans"

    # Primary Key
    plan_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Key
    course_id = Column(String(36), ForeignKey('courses.course_id'), nullable=False)

    # Plan Details
    plan_name = Column(String(100), nullable=False)  # "CBAP Monthly", "CBAP Annual"
    plan_code = Column(String(50), unique=True, nullable=False)  # "cbap_monthly"
    description = Column(Text, nullable=True)

    # Pricing
    price_amount = Column(DECIMAL(10, 2), nullable=False)  # e.g., 49.99
    currency = Column(String(3), nullable=False, default='USD')
    billing_interval = Column(String(20), nullable=False)  # 'monthly' | 'annual' | 'lifetime'
    billing_interval_count = Column(Integer, nullable=False, default=1)

    # Stripe Integration
    stripe_price_id = Column(String(255), unique=True, nullable=True)
    stripe_product_id = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="subscription_plans")
    subscriptions = relationship("Subscription", back_populates="plan", cascade="all, delete-orphan")

    # Check Constraints
    __table_args__ = (
        CheckConstraint("billing_interval IN ('monthly', 'annual', 'lifetime')", name='chk_billing_interval'),
    )

    def __repr__(self):
        return f"<SubscriptionPlan {self.plan_name} - ${self.price_amount}/{self.billing_interval}>"


class Subscription(Base):
    """
    User subscriptions to courses.
    """
    __tablename__ = "subscriptions"

    # Primary Key
    subscription_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    plan_id = Column(String(36), ForeignKey('subscription_plans.plan_id'), nullable=False)

    # Stripe Integration
    stripe_subscription_id = Column(String(255), unique=True, nullable=True)

    # Subscription Status
    status = Column(String(20), nullable=False, default='active')  # 'active' | 'canceled' | 'past_due' | 'trialing'

    # Billing Cycle
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")

    # Check Constraints
    __table_args__ = (
        CheckConstraint("status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete')", name='chk_subscription_status'),
    )

    def __repr__(self):
        return f"<Subscription {self.subscription_id} - {self.status}>"


class Payment(Base):
    """
    Payment transactions via Stripe.
    """
    __tablename__ = "payments"

    # Primary Key
    payment_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    subscription_id = Column(String(36), ForeignKey('subscriptions.subscription_id'), nullable=True)

    # Stripe Integration
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=True)
    stripe_charge_id = Column(String(255), unique=True, nullable=True)

    # Payment Details
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    status = Column(String(20), nullable=False)  # 'succeeded' | 'failed' | 'pending' | 'refunded' | 'disputed'

    # Payment Method
    payment_method_type = Column(String(50), nullable=True)  # 'card' | 'bank_transfer'
    payment_method_brand = Column(String(50), nullable=True)  # 'visa', 'mastercard', etc.
    payment_method_last4 = Column(String(4), nullable=True)

    # Stripe Fees
    stripe_fee = Column(DECIMAL(10, 2), nullable=True)
    net_amount = Column(DECIMAL(10, 2), nullable=True)  # amount - stripe_fee

    # Failure Details
    failure_code = Column(String(50), nullable=True)
    failure_message = Column(Text, nullable=True)

    # Timestamps
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")
    refunds = relationship("Refund", back_populates="payment", cascade="all, delete-orphan")
    chargebacks = relationship("Chargeback", back_populates="payment", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="payment", cascade="all, delete-orphan")
    revenue_events = relationship("RevenueEvent", back_populates="payment", cascade="all, delete-orphan")

    # Check Constraints
    __table_args__ = (
        CheckConstraint("status IN ('succeeded', 'failed', 'pending', 'refunded', 'disputed', 'canceled')", name='chk_payment_status'),
    )

    def __repr__(self):
        return f"<Payment {self.payment_id} - ${self.amount} - {self.status}>"


class Refund(Base):
    """
    Refund transactions.
    """
    __tablename__ = "refunds"

    # Primary Key
    refund_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Key
    payment_id = Column(String(36), ForeignKey('payments.payment_id', ondelete='CASCADE'), nullable=False)

    # Stripe Integration
    stripe_refund_id = Column(String(255), unique=True, nullable=True)

    # Refund Details
    amount = Column(DECIMAL(10, 2), nullable=False)
    reason = Column(String(50), nullable=True)  # 'duplicate' | 'fraudulent' | 'requested_by_customer'
    status = Column(String(20), nullable=False)  # 'succeeded' | 'failed' | 'pending' | 'canceled'

    # Timestamps
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    payment = relationship("Payment", back_populates="refunds")

    # Check Constraints
    __table_args__ = (
        CheckConstraint("status IN ('succeeded', 'failed', 'pending', 'canceled')", name='chk_refund_status'),
    )

    def __repr__(self):
        return f"<Refund {self.refund_id} - ${self.amount}>"


class Chargeback(Base):
    """
    Chargeback disputes from customers.
    """
    __tablename__ = "chargebacks"

    # Primary Key
    chargeback_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    payment_id = Column(String(36), ForeignKey('payments.payment_id', ondelete='CASCADE'), nullable=False)

    # Stripe Integration
    stripe_dispute_id = Column(String(255), unique=True, nullable=True)

    # Chargeback Details
    amount = Column(DECIMAL(10, 2), nullable=False)
    reason = Column(String(100), nullable=True)
    status = Column(String(30), nullable=False)  # 'warning_needs_response' | 'warning_under_review' | 'won' | 'lost'

    # Evidence Submission
    evidence_due_by = Column(DateTime(timezone=True), nullable=True)
    evidence_submitted = Column(Boolean, nullable=False, default=False)

    # Timestamps
    disputed_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User")
    payment = relationship("Payment", back_populates="chargebacks")

    def __repr__(self):
        return f"<Chargeback {self.chargeback_id} - ${self.amount} - {self.status}>"


class PaymentMethod(Base):
    """
    Stored payment methods (tokenized via Stripe).
    """
    __tablename__ = "payment_methods"

    # Primary Key
    method_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Key
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)

    # Stripe Integration
    stripe_payment_method_id = Column(String(255), unique=True, nullable=False)

    # Payment Method Details (PCI compliant - no full card numbers)
    method_type = Column(String(50), nullable=False)  # 'card' | 'bank_account'
    card_brand = Column(String(50), nullable=True)  # 'visa', 'mastercard', etc.
    card_last4 = Column(String(4), nullable=True)
    card_exp_month = Column(Integer, nullable=True)
    card_exp_year = Column(Integer, nullable=True)

    # Status
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<PaymentMethod {self.method_id} - {self.card_brand} ****{self.card_last4}>"


class Invoice(Base):
    """
    Invoices generated for payments.
    """
    __tablename__ = "invoices"

    # Primary Key
    invoice_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    user_id = Column(String(36), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    subscription_id = Column(String(36), ForeignKey('subscriptions.subscription_id'), nullable=True)
    payment_id = Column(String(36), ForeignKey('payments.payment_id'), nullable=True)

    # Stripe Integration
    stripe_invoice_id = Column(String(255), unique=True, nullable=True)

    # Invoice Details
    invoice_number = Column(String(50), unique=True, nullable=False)
    amount_due = Column(DECIMAL(10, 2), nullable=False)
    amount_paid = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    status = Column(String(20), nullable=False)  # 'draft' | 'open' | 'paid' | 'void' | 'uncollectible'

    # Timestamps
    invoice_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User")
    subscription = relationship("Subscription")
    payment = relationship("Payment", back_populates="invoices")

    # Check Constraints
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'open', 'paid', 'void', 'uncollectible')", name='chk_invoice_status'),
    )

    def __repr__(self):
        return f"<Invoice {self.invoice_number} - ${self.amount_due} - {self.status}>"


class RevenueEvent(Base):
    """
    Immutable log of all revenue-impacting events.

    Used for financial reporting and analytics (Decision #66).
    """
    __tablename__ = "revenue_events"

    # Primary Key
    event_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    user_id = Column(String(36), ForeignKey('users.user_id'), nullable=True)
    subscription_id = Column(String(36), ForeignKey('subscriptions.subscription_id'), nullable=True)
    payment_id = Column(String(36), ForeignKey('payments.payment_id'), nullable=True)

    # Event Type
    event_type = Column(String(50), nullable=False)  # 'payment_succeeded' | 'refund_issued' | 'chargeback_lost'

    # Financial Impact
    amount = Column(DECIMAL(10, 2), nullable=False)  # Can be negative for refunds/chargebacks
    net_amount = Column(DECIMAL(10, 2), nullable=False)  # After fees
    currency = Column(String(3), nullable=False, default='USD')

    # Metadata (renamed from 'metadata' which is reserved in SQLAlchemy)
    event_metadata = Column(JSON, nullable=True)

    # Timestamps (immutable - no updated_at)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User")
    subscription = relationship("Subscription")
    payment = relationship("Payment", back_populates="revenue_events")

    def __repr__(self):
        return f"<RevenueEvent {self.event_id} - {self.event_type} - ${self.amount}>"
