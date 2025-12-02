"""异步数据库模块（生产级模板 - FastAPI 专用）

- 使用 SQLModel + create_async_engine
- 参数可从 `settings.database` 读取，字段同同步版本
- 提供：
    async_engine          —— 全局异步引擎
    AsyncSessionFactory   —— `sessionmaker` for AsyncSession
    get_db                —— FastAPI Depends (async)

注意：
- 数据库表结构管理请使用 Alembic 迁移工具
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable

from loguru import logger
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from .config import settings


# ---------------------------------------------------------------------------
# 配置读取（带默认值）
# ---------------------------------------------------------------------------
_db_conf = settings.database


POOL_SIZE: int = getattr(_db_conf, "pool_size", 10)
MAX_OVERFLOW: int = getattr(_db_conf, "max_overflow", 20)
POOL_RECYCLE: int = getattr(_db_conf, "pool_recycle", 180)
ECHO_LOG: bool = getattr(_db_conf, "echo_log", getattr(settings, "debug", False))

logger.info(
    "[DB] Init async engine pool_size=%s max_overflow=%s recycle=%ss",
    POOL_SIZE,
    MAX_OVERFLOW,
    POOL_RECYCLE,
)


# ---------------------------------------------------------------------------
# 创建连接池（engine)
# ---------------------------------------------------------------------------

async_engine = create_async_engine(
    _db_conf.async_url,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
    echo=ECHO_LOG,
    connect_args={"timeout": 15},
)


# ---------------------------------------------------------------------------
# 创建会话工厂
# ---------------------------------------------------------------------------

AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ---------------------------------------------------------------------------
#                           定义数据库会话依赖注入
# ---------------------------------------------------------------------------


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session


# ---------------------------------------------------------------------------
# 定义模块的"公开API"
# ---------------------------------------------------------------------------

__all__: Iterable[str] = (
    "async_engine",  # 对应engine模块的参数
    "AsyncSessionFactory",  # 对应session工厂的参数
    "get_db",  # 定义数据库会话的依赖注入
)


# ----------------------------------------------------------------------------
# 拓展
# 关于 Iterable 的作用：这个是类型注解，定义了_all_模块括号里的数据类型
# 如果对不上，那么就会提示错误，非必须，但是建议加上的东西。
# __all__的作用就是高速使用者，智能使用括号里的3个东西
