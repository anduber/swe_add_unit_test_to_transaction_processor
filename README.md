# Transaction Processor Meta-Testing Sandbox

This repo hosts a SWE-Bench–style scenario focused on keeping unit-test suites effective. Our current emphasis is the transaction rules engine in `repository_after/transaction_processor.py`, plus optional division-guard tests in `repository_after/mathoperation`.

Meta tests in `tests/` feed both correct and intentionally broken implementations into the *real* suites to verify they detect regressions.

## Project Layout

```
repository_after/
  transaction_processor.py
  tests/test_transaction_processor_rules.py
tests/
  test_transaction_processor_rules_meta.py
  resources/transaction_processor/*.py
Dockerfile, docker-compose.yml
```

## Running Tests Locally

```bash
# Meta suite (detects broken implementations)
pytest tests/test_transaction_processor_rules_meta.py

# Real unit tests
pytest repository_after/tests/test_transaction_processor_rules.py
```

If `tests/test_division_meta.py` exists in your copy, you can run it the same way.

## Running via Docker

```bash
docker compose run --rm tests
```

The `tests` service builds the repo with Python 3.12 and runs `pytest -q tests/test_transaction_processor_rules_meta.py`. To include additional suites, edit the `command` in `docker-compose.yml`.

## Adding New Meta Variants

Broken implementations live under `tests/resources/transaction_processor/`. To add a new scenario:

1. Copy `repository_after/transaction_processor.py` into a new file in that folder.
2. Introduce the bug (e.g., remove a guard, skip a fee).
3. Reference the new file in `tests/test_transaction_processor_rules_meta.py` so the meta suite ensures the real tests fail for that variant.

This keeps the canonical implementation as the single source of truth while guaranteeing the regression tests stay sharp.
