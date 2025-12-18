from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import threading
import uuid
from typing import Dict, List, Optional, Tuple


class AccountType(Enum):
    STANDARD = "Standard"
    PREMIUM = "Premium"
    BUSINESS = "Business"


class TransactionType(Enum):
    DOMESTIC = "Domestic"
    INTERNATIONAL = "International"
    INSTANT = "Instant"


class Channel(Enum):
    BRANCH = "Branch"
    MOBILE_APP = "MobileApp"
    WEB = "Web"
    ATM = "ATM"


@dataclass
class TransactionRequest:
    amount: Decimal
    transaction_type: TransactionType
    channel: Channel
    location: str = ""
    currency: str = "USD"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CustomerProfile:
    id: int
    account_type: AccountType
    daily_limit: Decimal = Decimal("10000")
    has_overdraft_protection: bool = False
    overdraft_limit: Decimal = Decimal("500")
    average_transaction: Decimal = Decimal("250")
    home_location: str = "UNKNOWN"
    last_login_location: str = "UNKNOWN"
    monthly_transaction_count: int = 0
    loyalty_score: Decimal = Decimal("0")
    frequent_travel_locations: List[str] = field(default_factory=list)


@dataclass
class TransactionResult:
    processed_amount: Decimal = Decimal("0")
    requires_review: bool = False
    reference_number: str = ""
    messages: List[str] = field(default_factory=list)

    def add_message(self, message: str) -> None:
        if message and message.strip():
            self.messages.append(message.strip())


class DailyLimitExceededException(Exception):
    pass


class NightTimeLimitException(Exception):
    pass


class TransactionProcessor:
    _currency_adjustment_factors: Dict[str, Decimal] = {
        "USD": Decimal("1.0"),
        "EUR": Decimal("1.02"),
        "GBP": Decimal("1.01"),
        "JPY": Decimal("0.007"),
    }

    def __init__(self) -> None:
        self._daily_totals: Dict[Tuple[int, date], Decimal] = {}
        self._lock = threading.Lock()

    def process_transaction(self, request: TransactionRequest, customer: CustomerProfile) -> TransactionResult:
        if request is None:
            raise ValueError("request is required")
        if customer is None:
            raise ValueError("customer is required")
        if request.amount <= 0:
            raise ValueError("Transaction amount must be positive.")

        result = TransactionResult()
        final_amount = Decimal(request.amount)

        if customer.account_type == AccountType.PREMIUM:
            if request.transaction_type == TransactionType.INTERNATIONAL:
                final_amount += self._calculate_international_fee(request, customer)
            elif request.channel == Channel.MOBILE_APP:
                discount = (final_amount * Decimal("0.001")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                final_amount -= discount
                result.add_message("Premium mobile discount applied.")
        elif customer.account_type == AccountType.BUSINESS:
            if customer.monthly_transaction_count < 100:
                final_amount += Decimal("2.50")
                result.add_message("Business low-volume fee applied.")

        tx_date = request.timestamp.date()
        daily_total = self._get_daily_total(customer.id, tx_date)
        if daily_total + final_amount > customer.daily_limit:
            if customer.has_overdraft_protection and request.amount <= customer.overdraft_limit:
                final_amount += Decimal("25.00")
                result.add_message("Overdraft processing fee added.")
            else:
                raise DailyLimitExceededException("Daily limit exceeded.")

        requires_review = False
        if request.amount > Decimal("10000") and customer.average_transaction < Decimal("1000"):
            requires_review = True
            result.add_message("High-value transaction flagged for review.")

        if (
            request.location
            and request.location.lower() != customer.home_location.lower()
            and customer.last_login_location.lower() == request.location.lower()
        ):
            if not self._is_expected_travel(customer, request.location):
                requires_review = True
                result.add_message("Unexpected travel pattern detected.")

        utc_now = datetime.utcnow()
        if utc_now.hour >= 20 or utc_now.hour < 6:
            final_amount += Decimal("1.00")
            if request.amount > Decimal("5000"):
                raise NightTimeLimitException("Night-time limit exceeded.")

        if utc_now.weekday() >= 5 and request.transaction_type == TransactionType.INSTANT:
            weekend_fee = (final_amount * Decimal("0.015")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            final_amount += weekend_fee
            result.add_message("Weekend instant processing fee applied.")

        self._update_daily_total(customer.id, tx_date, final_amount)

        result.processed_amount = final_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        result.requires_review = requires_review
        result.reference_number = self._generate_reference_number()
        return result

    def _calculate_international_fee(self, request: TransactionRequest, customer: CustomerProfile) -> Decimal:
        factor = self._currency_adjustment_factors.get(request.currency.upper(), Decimal("1.05"))
        fx_fee = request.amount * Decimal("0.005") * factor
        network_fee = Decimal("0.50") if request.channel == Channel.MOBILE_APP else Decimal("1.00")

        if customer.loyalty_score >= Decimal("80"):
            fx_fee *= Decimal("0.85")

        return (fx_fee + network_fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _is_expected_travel(self, customer: CustomerProfile, location: str) -> bool:
        if not location:
            return True
        if location.lower() == customer.home_location.lower():
            return True
        return any(loc.lower() == location.lower() for loc in customer.frequent_travel_locations)

    def _generate_reference_number(self) -> str:
        return f"TX-{datetime.utcnow():%Y%m%d%H%M%S}-{uuid.uuid4().hex}".upper()

    def _get_daily_total(self, customer_id: int, tx_date: date) -> Decimal:
        key = (customer_id, tx_date)
        with self._lock:
            return self._daily_totals.get(key, Decimal("0"))

    def _update_daily_total(self, customer_id: int, tx_date: date, processed_amount: Decimal) -> None:
        key = (customer_id, tx_date)
        with self._lock:
            self._daily_totals[key] = self._daily_totals.get(key, Decimal("0")) + processed_amount
