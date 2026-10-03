#!/bin/bash
set -e

# 选择要启动的进程
if [ "$PROCESS_TYPE" = "translator" ]; then
    exec python /app/src/translator.py
elif [ "$PROCESS_TYPE" = "downloader" ]; then
    exec python /app/src/downloader.py
elif [ "$PROCESS_TYPE" = "uploader" ]; then
    exec python /app/src/uploader.py
else
    echo "Unknown process type: $PROCESS_TYPE"
    exit 1
fi