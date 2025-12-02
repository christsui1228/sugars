from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
import os
from loguru import logger
from enum import Enum

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

_ENV_FOR_FILE_PRIORITY = os.getenv("ENV", "development").lower()
_SPECIFIC_ENV_FILE_NAME = f".env.{_ENV_FOR_FILE_PRIORITY}"
SPECIFIC_ENV_FILE_PATH = ROOT_DIR / _SPECIFIC_ENV_FILE_NAME
DEFAULT_ENV_FILE_PATH = ROOT_DIR / ".env"


class Environment(str, Enum):
    """環境類型枚舉"""

    DEVELOPMENT = "development"
    PRODUCTION = "production"


class DatabaseConfig(BaseModel):
    """PostgreSQL 数据库配置"""

    user: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")
    host: str = Field(default="localhost", description="数据库主机地址")
    port: int = Field(default=5432, description="数据库端口")
    name: str = Field(..., description="数据库名称")
    echo_log: bool = Field(default=False, description="是否打印 SQL 日志")
    pool_size: int = Field(default=10, description="连接池大小")
    max_overflow: int = Field(default=20, description="连接池最大溢出")
    pool_recycle: int = Field(default=180, description="连接回收时间（秒）")

    @property
    def async_url(self) -> str:
        """异步数据库连接 URL (for SQLAlchemy async)"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_url(self) -> str:
        """同步数据库连接 URL (for Polars/ConnectorX)"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

        return f"{self.url}/collections/{self.collection}"
        return f"http://{self.host}:{self.port}"


class Settings(BaseSettings):
    env: Environment = Field(default=Environment.DEVELOPMENT, description="运行环境")
    debug: bool = Field(default=False, description="调试模式")
    database: DatabaseConfig

    model_config = SettingsConfigDict(
        env_file=(SPECIFIC_ENV_FILE_PATH, DEFAULT_ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # 允许额外字段，便于扩展
        env_nested_delimiter="__",  # 嵌套配置使用双下划线分隔
    )


@lru_cache
def get_settings() -> Settings:
    print("正在加载配置...")
    return Settings()


settings = get_settings()

if settings.env == Environment.DEVELOPMENT:
    logger.info(f"Running environment: {settings.env.value}")
    logger.info(f"Debug mode: {'Enabled' if settings.debug else 'Disabled'}")

    # 数据库信息（注意：包含敏感信息，仅开发环境打印）
    if settings.database:
        logger.info(f"Database async URL: {settings.database.async_url}")
        logger.info(f"Database sync URL: {settings.database.sync_url}")
