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

    # -------------------------
    # Business rules
    # -------------------------

    def test_business_low_volume_fee_applies_below_100(self):
        r = _mk_request(amount=Decimal("500"), channel=m.Channel.WEB)
        c = _mk_customer(id=30, account_type=m.AccountType.BUSINESS, monthly_transaction_count=99)
        with _freeze_utcnow(datetime(2024, 1, 1, 12, 0, 0)):
            res = self.p.process_transaction(r, c)
        self.assertEqual(res.processed_amount, _q2(Decimal("502.50")))
        self.assertIn("Business low-volume fee applied.", res.messages)

    def test_business_low_volume_fee_not_applied_at_100(self):
        r = _mk_request(amount=Decimal("500"), channel=m.Channel.WEB)
        c = _mk_customer(id=31, account_type=m.AccountType.BUSINESS, monthly_transaction_count=100)
        with _freeze_utcnow(datetime(2024, 1, 1, 12, 0, 0)):
            res = self.p.process_transaction(r, c)
        self.assertEqual(res.processed_amount, _q2(Decimal("500")))
        self.assertNotIn("Business low-volume fee applied.", res.messages)
        
    # -----------------------------------
    # Daily limit & overdraft (boundaries)
    # -----------------------------------

    def test_daily_limit_exactly_equal_allows(self):
        tx_ts = datetime(2024, 1, 2, 10, 0, 0)
        r = _mk_request(amount=Decimal("200"), timestamp=tx_ts, channel=m.Channel.ATM)
        c = _mk_customer(id=40, daily_limit=Decimal("1000"), has_overdraft_protection=False)

        self.p._daily_totals[(c.id, tx_ts.date())] = Decimal("800")
        with _freeze_utcnow(datetime(2024, 1, 2, 12, 0, 0)):
            res = self.p.process_transaction(r, c)

        self.assertEqual(res.processed_amount, _q2(Decimal("200")))
        self.assertEqual(self.p._get_daily_total(c.id, tx_ts.date()), Decimal("1000"))

    def test_daily_limit_exceeded_no_overdraft_raises_and_does_not_update_totals(self):
        tx_ts = datetime(2024, 1, 2, 10, 0, 0)
        r = _mk_request(amount=Decimal("201"), timestamp=tx_ts, channel=m.Channel.ATM)
        c = _mk_customer(id=41, daily_limit=Decimal("1000"), has_overdraft_protection=False)

        self.p._daily_totals[(c.id, tx_ts.date())] = Decimal("800")
        before = self.p._get_daily_total(c.id, tx_ts.date())

        with _freeze_utcnow(datetime(2024, 1, 2, 12, 0, 0)):
            with self.assertRaises(m.DailyLimitExceededException) as ex:
                self.p.process_transaction(r, c)

        self.assertEqual("Daily limit exceeded.", str(ex.exception))
        self.assertEqual(self.p._get_daily_total(c.id, tx_ts.date()), before)




if __name__ == "__main__":
    unittest.main(verbosity=2)
