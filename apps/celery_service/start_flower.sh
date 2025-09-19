#!/bin/bash

# Flower 監控啟動腳本

echo "🌸 啟動 Flower 監控"
echo "================================"

# 檢查是否在正確的目錄
if [ ! -f "celery_app.py" ]; then
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

# 啟動 Flower
echo "🚀 啟動 Flower 監控..."
echo "🌐 Web UI: http://localhost:5555"
echo "按 Ctrl+C 停止監控"
echo "================================"

python3 -m flower --app=celery_app --port=5555 --address=0.0.0.0 --auto_refresh=True --refresh_interval=2000 --max_tasks=1000 --db=flower.db --persistent=True --enable_events=True --format_task=True --natural_time=True --timezone=UTC
