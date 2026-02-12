#!/usr/bin/env bash
# Run all frontend code quality checks (Prettier + ESLint)
set -e

# Resolve to the frontend directory regardless of where the script is called from
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Prettier (format check) ==="
npx prettier --check .

echo ""
echo "=== ESLint ==="
npx eslint .

echo ""
echo "All checks passed!"
