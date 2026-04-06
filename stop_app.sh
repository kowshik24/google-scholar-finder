#!/bin/bash

set -e

APP_STOPPED=false

if [ -f app.pid ]; then
    pid=$(cat app.pid)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        echo "Stopped Streamlit process (PID: $pid)"
        APP_STOPPED=true
    else
        echo "PID file exists but process is not running (PID: $pid)"
    fi
    rm -f app.pid
else
    echo "PID file not found"
fi

# Fallback: stop any remaining matching Streamlit app process
if pgrep -f "streamlit run app.py --server.port 8502" >/dev/null 2>&1; then
    pkill -f "streamlit run app.py --server.port 8502"
    echo "Stopped remaining Streamlit app process(es)"
    APP_STOPPED=true
fi

if [ "$APP_STOPPED" = false ]; then
    echo "Streamlit app was already stopped"
fi

# Stop local proxy service if present
if systemctl list-unit-files | grep -q "^google-scholar-proxy.service"; then
    if systemctl is-active --quiet google-scholar-proxy.service; then
        systemctl stop google-scholar-proxy.service
        echo "Stopped google-scholar-proxy.service"
    else
        echo "google-scholar-proxy.service is already stopped"
    fi
else
    echo "google-scholar-proxy.service not installed"
fi