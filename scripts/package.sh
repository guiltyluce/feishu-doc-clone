#!/usr/bin/env bash
set -euo pipefail

# Validate and rebuild skill/<name>/<name>.zip for upload-style platforms
# (claude.ai Skills, WorkBuddy).

cd "$(dirname "$0")/.."
python3 scripts/validate_skill_package.py --zip "$@"
