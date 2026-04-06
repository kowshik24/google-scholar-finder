#!/bin/bash

set -e

source venv/bin/activate

# Free-proxy friendly defaults (override by exporting before running this script)
export USE_FREE_PROXY_ONLY="${USE_FREE_PROXY_ONLY:-true}"
export LOCAL_PROXY_URL="${LOCAL_PROXY_URL:-http://127.0.0.1:8000}"
export MAX_DIRECT_RETRIES="${MAX_DIRECT_RETRIES:-4}"
export MIN_REQUEST_DELAY="${MIN_REQUEST_DELAY:-2.0}"
export MAX_REQUEST_DELAY="${MAX_REQUEST_DELAY:-5.0}"
export DIRECT_TIMEOUT="${DIRECT_TIMEOUT:-40}"

nohup streamlit run app.py --server.port 8502 > streamlit.log 2>&1 &
echo $! > app.pid
