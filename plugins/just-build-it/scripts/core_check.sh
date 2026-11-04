#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# exit 0 = unchanged, 1 = frozen core changed, 2 = verification error.
set -eu
exec python3 "$(dirname "$0")/core_check.py" "$@"
