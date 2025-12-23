FROM python:3.12-slim

WORKDIR /app

# 安装系统级依赖 (编译生信库需要)
RUN apt-get update && apt-get install -y \
    build-essential gcc libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 默认启动命令 (会被 docker-compose 覆盖)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
