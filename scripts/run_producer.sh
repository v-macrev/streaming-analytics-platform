#!/usr/bin/env bash

set -euo pipefail

echo "Starting local event producer..."

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export PYTHONPATH="${REPO_ROOT}/producer/src"

echo "Repository root: ${REPO_ROOT}"
echo "PYTHONPATH set to: ${PYTHONPATH}"

echo "Launching producer..."

python -m main