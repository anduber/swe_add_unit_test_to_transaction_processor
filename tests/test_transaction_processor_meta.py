import pytest
from functools import lru_cache
from pathlib import Path

pytest_plugins = ("pytester",)


BASE_PROCESSOR_PATH = Path(__file__).resolve().parents[1] / "repository_after" / "transaction_processor.py"


@lru_cache(maxsize=None)
def _base_transaction_processor_text() -> str:
    return BASE_PROCESSOR_PATH.read_text()


def _transaction_processor_text(*, remove_request_validation: bool) -> str:
    text = _base_transaction_processor_text()
    if remove_request_validation:
        text = text.replace(
            "        if request is None:\n            raise ValueError(\"request is required\")\n",
            "",
            1,
        )
    return text


@pytest.fixture
def rules_suite_text() -> str:
    suite_path = (
        Path(__file__).resolve().parents[1] / "repository_after" / "tests" / "test_transaction_processor_rules.py"
    )
    return suite_path.read_text()


def _run_rules_suite(pytester, suite_text: str, impl_text: str):
    pytester.makepyfile(transaction_processor=impl_text, test_transaction_processor_rules=suite_text)
    return pytester.runpytest()


def _assert_suite_failed(result) -> None:
    outcomes = result.parseoutcomes()
    assert outcomes.get("failed", 0) >= 1

def _assert_min_failed(result, minimum: int = 1) -> None:
    outcomes = result.parseoutcomes()
    print("meta outcomes:", outcomes.get("failed", 0))  
    assert outcomes.get("failed", 0) >= minimum

def _assert_suite_passed(result) -> None:
    outcomes = result.parseoutcomes()
    assert outcomes.get("failed", 0) == 0
    assert outcomes.get("passed", 0) >= 1


def test_rules_suite_fails_when_request_not_validated(pytester, rules_suite_text) -> None:
    impl = _transaction_processor_text(remove_request_validation=True)
    result = _run_rules_suite(pytester, rules_suite_text, impl)
    _assert_min_failed(result)


def test_rules_suite_passes_with_request_validation(pytester, rules_suite_text) -> None:
    impl = _transaction_processor_text(remove_request_validation=False)
    result = _run_rules_suite(pytester, rules_suite_text, impl)
    _assert_suite_passed(result)
