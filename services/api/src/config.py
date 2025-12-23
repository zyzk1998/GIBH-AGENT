import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 基础路径
    UPLOAD_DIR: str = "/app/uploads"
    
    # 服务连接
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    VLLM_URL: str = os.getenv("VLLM_URL", "http://inference-engine:8000/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen3-vl")
    
    # Galaxy 配置 (可选)
    GALAXY_URL: str = os.getenv("GALAXY_URL", "http://192.168.8.111:8080")
    GALAXY_KEY: str = os.getenv("GALAXY_API_KEY", "your_key")

settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
