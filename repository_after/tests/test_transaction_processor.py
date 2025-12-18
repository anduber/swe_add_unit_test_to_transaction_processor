import unittest
from decimal import Decimal
from datetime import datetime as real_datetime
from unittest.mock import patch

from transaction_processor import (
    AccountType,
    Channel,
    CustomerProfile,
    TransactionProcessor,
    TransactionRequest,
    TransactionType,
)


class TransactionProcessorBasicTest(unittest.TestCase):
    def test_standard_domestic_transaction_processes_without_adjustments(self) -> None:
        processor = TransactionProcessor()
        customer = CustomerProfile(
            id=1,
            account_type=AccountType.STANDARD,
            daily_limit=Decimal("5000"),
            home_location="NYC",
            last_login_location="NYC",
        )
        request = TransactionRequest(
            amount=Decimal("100.00"),
            transaction_type=TransactionType.DOMESTIC,
            channel=Channel.BRANCH,
            location="NYC",
            timestamp=real_datetime(2023, 6, 14, 12, 0, 0),
        )
        current_time = real_datetime(2023, 6, 14, 12, 0, 0)

        with patch("transaction_processor.datetime") as mock_datetime, patch.object(
            TransactionProcessor, "_generate_reference_number", return_value="TEST-REF"
        ):
            mock_datetime.utcnow.return_value = current_time

            result = processor.process_transaction(request, customer)

        self.assertEqual(Decimal("100.00"), result.processed_amount)
        self.assertFalse(result.requires_review)
        self.assertEqual([], result.messages)
        self.assertEqual("TEST-REF", result.reference_number)


if __name__ == "__main__":
    unittest.main()
