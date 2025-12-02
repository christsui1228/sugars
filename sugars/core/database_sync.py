"""同步数据库模块（生产级模板 - FastAPI 专用）

- 使用 SQLModel + SQLAlchemy QueuePool
- 连接池参数、日志等可从 `settings.database` 读取
- 提供：
    engine               —— 全局同步引擎
    SessionFactory       —— `sessionmaker` 工厂
    get_db               —— FastAPI `Depends`（同步）

- 数据库表结构管理请使用 Alembic 迁移工具
"""

from __future__ import annotations

from typing import Iterator, Iterable

from loguru import logger
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine

from .config import settings  # 调整为实际配置模块名

# ---------------------------------------------------------------------------
# 配置读取（带默认值）
# ---------------------------------------------------------------------------
_db_conf = settings.database

POOL_SIZE: int = getattr(_db_conf, "pool_size", 10)
MAX_OVERFLOW: int = getattr(_db_conf, "max_overflow", 20)
POOL_RECYCLE: int = getattr(_db_conf, "pool_recycle", 180)  # 秒
ECHO_LOG: bool = getattr(_db_conf, "echo_log", getattr(settings, "debug", False))

logger.info(
    "[DB] Init sync engine pool_size=%s max_overflow=%s recycle=%ss",
    POOL_SIZE,
    MAX_OVERFLOW,
    POOL_RECYCLE,
)

engine = create_engine(
    _db_conf.sync_url,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
    echo=ECHO_LOG,
)

SessionFactory: sessionmaker[Session] = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)  # 同步版本不把autocommit=False写出来

# ----------------------------------------------------------------------------
#                              定义数据库会话依赖注入
# ----------------------------------------------------------------------------


def get_db() -> Iterator[Session]:
    """同步 Session 依赖，用于 `Depends(get_db)`"""
    with SessionFactory() as session:
        yield session


# ----------------------------------------------------------------------------
#                             定义模块的“公开API”
# ----------------------------------------------------------------------------

__all__: Iterable[str] = (
    "engine",  # 对应engine模块的参数
    "SessionFactory",  # 对应session工厂的参数
    "get_db",  # 定义数据库会话依赖注入
)

# ----------------------------------------------------------------------------
# 拓展
# 关于 Iterable 的作用：这个是类型注解，定义了_all_模块括号里的数据类型
# 如果对不上，那么就会提示错误，非必须，但是建议加上的东西。
# __all__的作用就是高速使用者，智能使用括号里的3个东西
