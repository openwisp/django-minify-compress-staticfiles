# AGENTS.md

## Project Overview

`django-minify-compress-staticfiles` is a Django package for minifying and compressing static files with gzip and brotli support.

Core code lives in `django_minify_compress_staticfiles/`:

- Package modules implement static file minification, compression, storage helpers, and path safety checks.
- Tests live in `tests/` and `test_staticfiles/`.

## Source of Truth

- Use `README.rst` for setup and package usage.
- Use `.github/workflows/ci.yml` for CI-tested dependencies, QA/test commands, env vars, and supported Python/Django versions.
- Use GitHub issue/PR templates when asked to open issues or PRs.

Follow the DRY principle: do not duplicate information or code across files.

If instructions conflict, repository config and CI workflows win first, docs next, and this file is supplemental.

## Development Notes

- Keep changes focused. Avoid unrelated refactors and formatting churn.
- Preserve public APIs, storage behavior, compression outputs, and path safety checks unless explicitly required.
- Place imports at the top of the file. Only defer imports when necessary (e.g., Django model imports inside functions or methods where the app registry is not yet ready).
- Avoid unnecessary blank lines inside function and method bodies.
- Update docs when behavior, settings, public APIs, setup steps, or supported versions change.

## Testing and QA

- Add or update tests for every behavior change.
- For bug fixes, write the regression test first, run it against the unfixed code, confirm it fails for the expected reason, then implement the fix.
- Run tests with `python runtests.py`; use `coverage run runtests.py && coverage report` when checking coverage.
- Run `openwisp-qa-format` after editing.
- Run `./run-qa-checks` before considering the change complete. Treat failures as blocking unless confirmed unrelated and reported.
- Keep coverage above the repository threshold.

## Security Notes

- Watch for path traversal, unsafe file handling, malformed static file paths, and secrets in code.
- Preserve validation around safe paths, minified output paths, compressed file creation, and static file discovery.
- Write comments and docstrings only when they explain why code is shaped a certain way. Put comments before the relevant code block instead of scattering them inside it.

## Troubleshooting

- If setup, QA, or tests fail, check docs first, then compare with CI. If commands diverge, follow CI.
