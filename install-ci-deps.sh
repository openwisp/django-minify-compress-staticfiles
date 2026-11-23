#!/usr/bin/env bash
# Install the dependencies used by CI and review experiments.
set -euo pipefail

python -m pip install --upgrade pip
if [ "${CI_QA:-0}" = 1 ]; then
  pip install -e '.[test]'
else
  pip install "${DJANGO_VERSION:?Set DJANGO_VERSION to the selected CI matrix value}"
  pip install coverage
  pip install -e .
fi
