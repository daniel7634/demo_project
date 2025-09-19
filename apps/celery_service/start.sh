#!/bin/bash

# Celery 服務啟動腳本

echo "🚀 啟動 Celery 簡單服務"
echo "================================"

# 檢查是否在正確的目錄
if [ ! -f "worker.py" ]; then
    echo "❌ 請在 celery_service 目錄中運行此腳本"
    exit 1
fi

# 檢查 Python 環境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3"
    exit 1
fi

# 檢查 Redis 連接
echo "🔍 檢查 Redis 連接..."
if ! python3 -c "import redis; redis.Redis().ping()" 2>/dev/null; then
    echo "❌ 無法連接到 Redis"
    echo "💡 請先啟動 Redis 服務："
    echo "   docker run -d --name redis -p 6379:6379 redis:latest"
    echo "   或"
    echo "   redis-server"
    exit 1
fi

echo "✅ Redis 連接正常"

# 啟動 Worker
echo "🚀 啟動 Celery Worker..."
echo "按 Ctrl+C 停止服務"
echo "================================"

python3 worker.py
