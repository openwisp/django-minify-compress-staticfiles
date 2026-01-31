# AGENTS.md

## Project Overview

Django Minify Compress Staticfiles: A Django package for minifying and compressing static files (CSS/JS)
with gzip and brotli support.

## Development Setup

- Install dependencies: `pip install -e .`
- For testing with all features: `pip install -e .[test]`

## Code Formatting

To format code, run:

```bash
openwisp-qa-format
```

## Testing

Run tests with:

```bash
python runtests.py
```

Coverage report:

```bash
coverage run runtests.py
coverage report
```

## QA Checks

Run QA checks with:

```bash
./run-qa-checks
```

This validates:

- Python code formatting (isort, black, flake8)
- Blank endline checks
- ReStructuredText syntax
- Commit message format

## General Guidelines

- **Avoid unnecessary blank lines** - they bloat the code with no benefit. Use blank lines sparingly, only where PEP 8 requires them (e.g., between class methods, between imports and code).
- **Keep test coverage above 90%** - every new feature must include tests.
- Avoid other arbitrary formatting changes.
- Run `./run-qa-checks` before committing to ensure compliance.

## Code Review Checklist

When reviewing changes, always watch out for:

- Missing tests (aim for >90% coverage).
- Unnecessary blank lines added.
- Performance penalties.
- Inconsistencies and duplication which can lead to maintenance overhead.
- Security issues (e.g., no secrets in code, safe file path validation).
- Path traversal vulnerabilities (ensure `is_safe_path()` is used).

## Contributing Guidelines

- [Follow OpenWISP contributing guidelines](https://openwisp.io/docs/dev/developer/contributing.html).
- Ensure commit messages follow the format: `[type] Description` (e.g., `[fix] Resolved compression issue`).

## Troubleshooting

- QA/format commands fail: Ensure Python virtualenv is active and dependencies are installed.
- Tests fail: Check that `pip install -e .` was run.
- Coverage issues: Run `coverage run runtests.py && coverage report` locally.
- CI issues: Refer to `.github/workflows/ci.yml`.
