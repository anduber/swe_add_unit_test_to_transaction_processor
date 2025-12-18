import sys
import unittest
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import threading
from unittest.mock import patch

_THIS_DIR = Path(__file__).resolve().parent
for candidate in {_THIS_DIR, _THIS_DIR.parent}:
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

import transaction_processor as m


class _FixedUtcNow:
    now = datetime(2024, 1, 1, 12, 0, 0)

    @classmethod
    def utcnow(cls):
        return cls.now


def _freeze_utcnow(dt: datetime):
    _FixedUtcNow.now = dt
    return patch.object(m, "datetime", _FixedUtcNow)


def _mk_customer(
    *,
    id=1,
    account_type=m.AccountType.STANDARD,
    daily_limit=Decimal("10000"),
    has_overdraft_protection=False,
    overdraft_limit=Decimal("500"),
    average_transaction=Decimal("250"),
    home_location="US",
    last_login_location="US",
    monthly_transaction_count=0,
    loyalty_score=Decimal("0"),
    frequent_travel_locations=None,
):
    return m.CustomerProfile(
        id=id,
        account_type=account_type,
        daily_limit=daily_limit,
        has_overdraft_protection=has_overdraft_protection,
        overdraft_limit=overdraft_limit,
        average_transaction=average_transaction,
        home_location=home_location,
        last_login_location=last_login_location,
        monthly_transaction_count=monthly_transaction_count,
        loyalty_score=loyalty_score,
        frequent_travel_locations=list(frequent_travel_locations or []),
    )


def _mk_request(
    *,
    amount=Decimal("1000"),
    transaction_type=m.TransactionType.DOMESTIC,
    channel=m.Channel.MOBILE_APP,
    location="",
    currency="USD",
    timestamp=datetime(2024, 1, 1, 10, 0, 0),
):
    return m.TransactionRequest(
        amount=Decimal(amount),
        transaction_type=transaction_type,
        channel=channel,
        location=location,
        currency=currency,
        timestamp=timestamp,
    )


def _q2(x: Decimal) -> Decimal:
    return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class TestTransactionProcessorRulesTest(unittest.TestCase):
    def setUp(self):
        self.p = m.TransactionProcessor()
        
    # -------------------------
    # Input validation & basics
    # -------------------------
    def test_missing_request_raises(self):
        c = _mk_customer()
        with self.assertRaises(ValueError) as ex:
            self.p.process_transaction(None, c)
        self.assertEqual("request is required", str(ex.exception))

    def test_missing_customer_raises(self):
        r = _mk_request()
        with self.assertRaises(ValueError) as ex:
            self.p.process_transaction(r, None)
        self.assertEqual("customer is required", str(ex.exception))
    
    def test_amount_zero_raises(self):
        r = _mk_request(amount=Decimal("0"))
        c = _mk_customer()
        with self.assertRaises(ValueError) as ex:
            self.p.process_transaction(r, c)
        self.assertEqual("Transaction amount must be positive.", str(ex.exception))

    # -------------------------
    # Premium rules
    # -------------------------

    def test_premium_mobile_discount_applies_for_non_international(self):
        r = _mk_request(
            amount=Decimal("1000"),
            transaction_type=m.TransactionType.DOMESTIC,
            channel=m.Channel.MOBILE_APP,
        )
        c = _mk_customer(id=10, account_type=m.AccountType.PREMIUM)
        with _freeze_utcnow(datetime(2024, 1, 1, 12, 0, 0)):
            res = self.p.process_transaction(r, c)

        discount = _q2(Decimal("1000") * Decimal("0.001"))
        self.assertEqual(res.processed_amount, _q2(Decimal("1000") - discount))
        self.assertIn("Premium mobile discount applied.", res.messages)

    def test_premium_international_fee_takes_precedence_over_mobile_discount(self):
        '''
        1. IF transaction is INTERNATIONAL → Add international fee (NO mobile discount)
        2. ELIF (only if NOT international) AND channel is MOBILE_APP → Apply mobile discount
        '''
        r = _mk_request(
            amount=Decimal("1000"),
            transaction_type=m.TransactionType.INTERNATIONAL,
            channel=m.Channel.MOBILE_APP,
            currency="USD",
        )
        c = _mk_customer(id=12, account_type=m.AccountType.PREMIUM, loyalty_score=Decimal("0"))
        with _freeze_utcnow(datetime(2024, 1, 1, 12, 0, 0)):
            res = self.p.process_transaction(r, c)

        self.assertNotIn("Premium mobile discount applied.", res.messages)

        factor = Decimal("1.0")
        fx_fee = Decimal("1000") * Decimal("0.005") * factor
        network_fee = Decimal("0.50")
        expected_fee = (fx_fee + network_fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.assertEqual(res.processed_amount, _q2(Decimal("1000") + expected_fee))


if __name__ == "__main__":
    unittest.main(verbosity=2)
