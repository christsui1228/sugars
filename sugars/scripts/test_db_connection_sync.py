#!/usr/bin/env python3
"""同步数据库连接测试脚本

测试同步数据库配置是否正确，连接是否成功。

使用方法：
    pdm run python scripts/test_db_sync.py
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

# 测试配置加载
print("\n" + "=" * 70)
print("🔧 步骤 1: 测试配置加载")
print("=" * 70)

try:
    from .core.config import settings

    print("✅ 配置模块导入成功")
    print(f"   环境: {settings.env.value}")
    print(f"   调试模式: {settings.debug}")
    print(f"   数据库主机: {settings.database.host}")
    print(f"   数据库端口: {settings.database.port}")
    print(f"   数据库名称: {settings.database.name}")
    print(f"   数据库用户: {settings.database.user}")
    print(f"   连接池大小: {settings.database.pool_size}")
    print(f"   最大溢出: {settings.database.max_overflow}")
    print(f"   连接回收: {settings.database.pool_recycle}秒")
except Exception as e:
    print(f"❌ 配置加载失败: {e}")
    sys.exit(1)

# 测试同步数据库连接
print("\n" + "=" * 70)
print("🔌 步骤 2: 测试同步数据库连接")
print("=" * 70)

try:
    from .core.database_sync import engine, SessionFactory

    print("✅ 同步数据库模块导入成功")
    print(f"   连接 URL: {settings.database.sync_url}")

    # 测试连接
    with SessionFactory() as session:
        result = session.exec(text("SELECT version()")).first()
        print(f"✅ 数据库连接成功")
        print(f"   PostgreSQL 版本: {result[0]}")

        # 测试当前数据库
        db_result = session.exec(text("SELECT current_database()")).first()
        print(f"   当前数据库: {db_result[0]}")

        # 测试当前用户
        user_result = session.exec(text("SELECT current_user")).first()
        print(f"   当前用户: {user_result[0]}")

except Exception as e:
    print(f"❌ 同步数据库连接失败: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# 测试数据库表
print("\n" + "=" * 70)
print("📊 步骤 3: 检查数据库表")
print("=" * 70)

try:
    with SessionFactory() as session:
        # 查询所有表
        query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        result = session.exec(query).all()

        if result:
            print(f"✅ 找到 {len(result)} 个表:")
            for row in result:
                print(f"   - {row[0]}")
        else:
            print("⚠️  数据库中没有表（可能需要运行 Alembic 迁移）")

except Exception as e:
    print(f"❌ 查询表失败: {e}")
    import traceback

    traceback.print_exc()

# 测试连接池
print("\n" + "=" * 70)
print("🏊 步骤 4: 测试连接池")
print("=" * 70)

try:
    pool = engine.pool
    print(f"✅ 连接池状态:")
    print(f"   连接池大小: {pool.size()}")
    print(f"   已签出连接: {pool.checkedout()}")
    print(f"   溢出连接: {pool.overflow()}")
    print(f"   总连接数: {pool.size() + pool.overflow()}")

except Exception as e:
    print(f"⚠️  无法获取连接池状态: {e}")

# 测试简单查询性能
print("\n" + "=" * 70)
print("⚡ 步骤 5: 测试查询性能")
print("=" * 70)

try:
    import time

    with SessionFactory() as session:
        # 测试 10 次简单查询
        start_time = time.time()
        for _ in range(10):
            session.exec(text("SELECT 1")).first()
        elapsed = time.time() - start_time

        print(f"✅ 10 次查询耗时: {elapsed:.3f} 秒")
        print(f"   平均每次: {elapsed / 10 * 1000:.2f} 毫秒")

except Exception as e:
    print(f"⚠️  性能测试失败: {e}")

# 总结
print("\n" + "=" * 70)
print("✅ 同步数据库测试通过！配置正确，连接正常。")
print("=" * 70 + "\n")
