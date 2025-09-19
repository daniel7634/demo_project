#!/bin/bash
# Added execute permission

# Amazon 產品監控與優化工具 - Docker 啟動腳本

echo "🚀 Amazon 產品監控與優化工具 Docker 啟動腳本"
echo "================================================"

# 檢查 Docker 和 Docker Compose 是否安裝
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安裝，請先安裝 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安裝，請先安裝 Docker Compose"
    exit 1
fi


# 載入環境變量
echo "🔍 載入環境變量配置..."
export $(grep -v '^#' .env | xargs)

if [ -z "$APIFY_API_TOKEN" ] || [ "$APIFY_API_TOKEN" = "your_apify_token_here" ]; then
    echo "❌ 請在 .env 文件中設定 APIFY_API_TOKEN"
    exit 1
fi

if [ -z "$SUPABASE_URL" ] || [ "$SUPABASE_URL" = "https://your-project.supabase.co" ]; then
    echo "❌ 請在 .env 文件中設定 SUPABASE_URL"
    exit 1
fi

if [ -z "$SUPABASE_KEY" ] || [ "$SUPABASE_KEY" = "your_supabase_anon_key_here" ]; then
    echo "❌ 請在 .env 文件中設定 SUPABASE_KEY"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your_openai_api_key_here" ]; then
    echo "❌ 請在 .env 文件中設定 OPENAI_API_KEY"
    exit 1
fi

echo "✅ 環境變量配置檢查通過"

# 停止現有容器
echo "🛑 停止現有容器..."
docker-compose down

# 構建並啟動服務（使用 Docker Stack 方式）
echo "🔨 構建並啟動服務..."
export $(grep -v '^#' .env | xargs) && docker-compose up --build -d

# 等待服務啟動
echo "⏳ 等待服務啟動..."
sleep 10

# 檢查服務狀態
echo "🔍 檢查服務狀態..."
docker-compose ps

# 顯示服務訪問信息
echo ""
echo "🎉 服務啟動完成！"
echo "================================================"
echo "📊 服務訪問地址："
echo "   API 服務: http://localhost:8000"
echo "   API 文檔: http://localhost:8000/docs"
echo "   Flower 監控: http://localhost:5555"
echo "   Nginx 代理: http://localhost"
echo ""
echo "🔧 管理命令："
echo "   查看日誌: docker-compose logs -f"
echo "   停止服務: docker-compose down"
echo "   重啟服務: docker-compose restart"
echo "   查看狀態: docker-compose ps"
echo ""
echo "📝 測試 API："
echo "   curl http://localhost:8000/api/v1/health"
echo ""
echo "⏰ 定時任務："
echo "   Amazon 抓取: 每2分鐘執行一次"
echo "   報告清理: 每天凌晨2點執行"
echo "   健康監控: 每10分鐘執行一次"
echo "================================================"
