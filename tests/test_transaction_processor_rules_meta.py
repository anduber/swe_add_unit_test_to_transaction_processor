import pytest
from functools import lru_cache
from pathlib import Path

pytest_plugins = ("pytester",)

BASE_PROCESSOR_PATH = Path(__file__).resolve().parents[1] / "repository_after" / "transaction_processor.py"
BROKEN_IMPL_DIR = Path(__file__).resolve().parent / "resources" / "transaction_processor"


@lru_cache(maxsize=None)
def _transaction_processor_text(variant: str) -> str:
    if variant == "correct":
        return BASE_PROCESSOR_PATH.read_text()
    resource_path = BROKEN_IMPL_DIR / variant
    return resource_path.read_text()


@pytest.fixture
def rules_suite_text() -> str:
    suite_path = (
        Path(__file__).resolve().parents[1] / "repository_after" / "tests" / "test_transaction_processor_rules.py"
    )
    return suite_path.read_text()


def _run_rules_suite(pytester, suite_text: str, impl_text: str):
    pytester.makepyfile(transaction_processor=impl_text, test_transaction_processor_rules=suite_text)
    return pytester.runpytest()


def _assert_suite_failed(result,minimum: int = 1) -> None:
    outcomes = result.parseoutcomes()
    assert outcomes.get("failed", 0) >= minimum


def _assert_suite_passed(result) -> None:
    outcomes = result.parseoutcomes()
    assert outcomes.get("failed", 0) == 0
    assert outcomes.get("passed", 0) >= 1


def test_rules_suite_fails_when_request_not_validated(pytester, rules_suite_text) -> None:
    impl = _transaction_processor_text("broken_missing_request_validation.py")
    result = _run_rules_suite(pytester, rules_suite_text, impl)
    _assert_suite_failed(result)


def test_rules_suite_detects_premium_mobile_discount_logic(pytester, rules_suite_text) -> None:
    if "\n    def test_premium_mobile_discount_applies_for_non_international" not in rules_suite_text:
        pytest.skip("Premium discount tests are not present in the rules suite.")
    impl = _transaction_processor_text("broken_premium_mobile_discount.py")
    result = _run_rules_suite(pytester, rules_suite_text, impl)
    _assert_suite_failed(result)


def test_rules_suite_detects_business_low_volume_logic(pytester, rules_suite_text) -> None:
    if "\n    def test_business_low_volume_fee_applies_below_100" not in rules_suite_text:
        pytest.skip("Business low-volume tests are not present in the rules suite.")
    impl = _transaction_processor_text("broken_business_low_volume_fee.py")
    result = _run_rules_suite(pytester, rules_suite_text, impl)
    _assert_suite_failed(result)


def test_rules_suite_detects_daily_limit_logic(pytester, rules_suite_text) -> None:
    if "\n    def test_daily_limit_exactly_equal_allows" not in rules_suite_text:
        pytest.skip("Daily limit tests are not present in the rules suite.")
    impl = _transaction_processor_text("broken_daily_limit_overdraft.py")
    result = _run_rules_suite(pytester, rules_suite_text, impl)
    _assert_suite_failed(result)


def test_rules_suite_passes_with_request_validation(pytester, rules_suite_text) -> None:
    impl = _transaction_processor_text("correct")
    result = _run_rules_suite(pytester, rules_suite_text, impl)
    _assert_suite_passed(result)
