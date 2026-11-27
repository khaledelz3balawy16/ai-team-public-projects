#!/usr/bin/env bash
# Runs lms.js against BASE_URL with the account from ../loadtest.env
# (LOADTEST_EMAIL=..., LOADTEST_PASSWORD=...). Values are never printed.
#   BASE_URL=https://lms.kentbusinesscollege.org ./run.sh
set -euo pipefail
cd "$(dirname "$0")"

: "${BASE_URL:?set BASE_URL}"
set -a; source ../loadtest.env; set +a

name=$(echo "$BASE_URL" | sed -E 's#https?://##; s#[/.]#_#g')
stamp=$(date +%Y%m%d-%H%M%S)
mkdir -p results
k6 run --quiet --summary-export "results/${name}-${stamp}.json" lms.js 2>&1 | tee "results/${name}-${stamp}.txt"
