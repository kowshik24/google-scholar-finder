#!/bin/bash
if [ -f app.pid ]; then
    pid=$(cat app.pid)
    kill $pid
    rm app.pid
    echo "Streamlit app stopped"
else
    echo "PID file not found"
fi