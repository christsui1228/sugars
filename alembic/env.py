from logging.config import fileConfig
import asyncio

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 导入配置和模型
import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 导入配置
from {{ project_slug }}.core.config import settings

# 导入 SQLModel 和所有模型
from sqlmodel import SQLModel

# 导入所有模型以确保它们被注册到 metadata
from {{ project_slug }}.features.demo.models import DemoItem  # noqa: F401
# 在这里导入其他模型...
# from {{ project_slug }}.features.other.models import OtherModel  # noqa: F401

# Alembic Config 对象
config = context.config

# 从配置中设置数据库 URL
config.set_main_option("sqlalchemy.url", settings.database.async_url)

# 配置 Python 日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 使用 SQLModel 的 metadata
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """离线模式运行迁移
    
    在离线模式下，只需要 URL 而不需要 Engine。
    这样甚至不需要 DBAPI 可用。
    
    调用 context.execute() 会将 SQL 输出到脚本。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # 比较列类型变化
        render_as_batch=True,  # 支持 SQLite 等数据库
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """在给定连接上运行迁移"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # 比较列类型变化
        render_as_batch=True,  # 支持 SQLite 等数据库
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """使用异步引擎运行迁移"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """在线模式运行迁移（异步版本）"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
