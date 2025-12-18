import unittest
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import threading
from unittest.mock import patch

import transaction_processor as m  # replace with your actual module name


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
