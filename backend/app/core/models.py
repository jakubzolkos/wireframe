from typing import Any, Literal
from pydantic import BaseModel


class StripeSessionMetadata(BaseModel):
    user_id: str | None = None
    organization_id: str | None = None
    request_id: str
    email: str
    billing_cycle: str | None = None

class StripeSessionStatus(BaseModel):
    status: str
    metadata: StripeSessionMetadata


class CheckoutSessionRequest(BaseModel):
    price_id: str


class SubscriptionOrderInfo(BaseModel):
    customer_email: str
    purchaser_id: str
    is_org_purchase: bool
    billing_cycle: str
    price_id: str
    workspace_name: str 
    seat_count: int = 1  
    promo_code: str | None = None  

class CompletedSubscriptionInfo(BaseModel):
    customer_email: str
    purchaser_id: str
    is_org_purchase: bool
    billing_cycle: str
    status: str
    request_id: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    seat_count: int = 1

class DiscountInfo(BaseModel):
    type: str 
    value: int | float 
    amount_off: int 
    coupon_id: str
    coupon_name: str | None = None

class SubscriptionResponse(BaseModel):
    id: str
    status: str
    current_period_start: int
    current_period_end: int
    customer: str
    quantity: int
    plan_id: str
    plan_name: str
    amount: int
    base_amount: int
    currency: str
    cancel_at_period_end: bool
    discount: DiscountInfo | None = None
    billing_interval: str

class CustomerResponse(BaseModel):
    id: str
    email: str
    name: str | None = None
    created: int

class PaymentMethodResponse(BaseModel):
    id: str
    type: str
    card: dict[str, Any] | None = None
    created: int

class InvoiceResponse(BaseModel):
    id: str
    amount_paid: int
    amount_due: int
    currency: str
    status: str
    created: int
    hosted_invoice_url: str | None = None
    invoice_pdf: str | None = None

class ProductResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    metadata: dict[str, str] | None = None
    active: bool

class PriceResponse(BaseModel):
    id: str
    product: str
    unit_amount: int | None = None
    currency: str
    recurring: dict[str, Any] | None = None
    metadata: dict[str, str] | None = None
    active: bool


class UpdateSeatsRequest(BaseModel):
    seat_count: int

class PromoCodeValidation(BaseModel):
    promo_code: str

class PromoCodeResponse(BaseModel):
    valid: bool
    coupon_id: str | None = None
    discount_type: str | None = None  
    discount_value: int | None = None 
    currency: str | None = None
    error_message: str | None = None

class CheckoutSessionResponse(BaseModel):
    checkout_url: str

class PortalSessionResponse(BaseModel):
    portal_url: str

class SubscriptionCancelResponse(BaseModel):
    message: str
    subscription_id: str
    cancel_at: str

class UpdateSeatsResponse(BaseModel):
    message: str
    seat_count: int
    subscription_id: str

class SubscriptionValidationResponse(BaseModel):
    valid: bool
    subscription_id: str | None = None
    status: str | None = None
    error_message: str | None = None

class ChipSubcategoryInfo(BaseModel):
    name: str
    component_count: int
    category_id: str | None = None

class ChipCategory(BaseModel):
    name: str
    subcategories: list[ChipSubcategoryInfo]


class ChipFilter(BaseModel):
    type: Literal['physical_unit_range', 'multichoice']
    name: str
    alias: str
    product_count: int
    unique_value_count: int


class ChipFilterPhysicalUnitRange(ChipFilter):
    type: Literal['physical_unit_range']
    available_units: list[str]


class ChipFilterMultichoiceValue(BaseModel):
    value: str | int | float
    num_chips_with_value: int


class ChipFilterMultichoice(ChipFilter):
    type: Literal['multichoice']
    default: str
    available_values: list[ChipFilterMultichoiceValue]
