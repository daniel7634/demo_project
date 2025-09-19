# 使用 Python 3.12 官方映像
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Poetry
RUN pip install poetry

# 複製專案文件
COPY pyproject.toml poetry.lock ./
COPY shared/ /app/shared/
COPY apps/celery_service/ /app/apps/celery_service/

# 配置 Poetry
RUN poetry config virtualenvs.create false

# 安裝專案依賴
RUN poetry install --only=main

# 設定工作目錄到 Celery 服務
WORKDIR /app/apps/celery_service

# 設定環境變量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露 Flower 監控端口
EXPOSE 5555

# 啟動命令
CMD ["python", "worker.py"]
