#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Arthur Wang
# Validate removal in an isolated snapshot; never move the real feature or flags.
set -eu
exec "${HOARD_PYTHON:-python3}" "$(dirname "$0")/removability_check.py" "$@"
