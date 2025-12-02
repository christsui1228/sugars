#!/usr/bin/env python3
"""异步数据库连接测试脚本

测试异步数据库配置是否正确，连接是否成功。

使用方法：
    pdm run python scripts/test_db_async.py
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from sqlalchemy import text

# 测试配置加载
print("\n" + "=" * 70)
print("🔧 步骤 1: 测试配置加载")
print("=" * 70)

try:
    from sugars.core.config import settings

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


async def test_async_database():
    """异步数据库测试主函数"""

    # 测试异步数据库连接
    print("\n" + "=" * 70)
    print("🔌 步骤 2: 测试异步数据库连接")
    print("=" * 70)

    try:
        from sugars.core.database_async import async_engine, AsyncSessionFactory

        print("✅ 异步数据库模块导入成功")
        print(f"   连接 URL: {settings.database.async_url}")

        # 测试连接
        async with AsyncSessionFactory() as session:
            result = await session.exec(text("SELECT version()"))
            version = result.first()
            print(f"✅ 异步数据库连接成功")
            print(f"   PostgreSQL 版本: {version[0]}")

            # 测试当前数据库
            db_result = await session.exec(text("SELECT current_database()"))
            db_name = db_result.first()
            print(f"   当前数据库: {db_name[0]}")

            # 测试当前用户
            user_result = await session.exec(text("SELECT current_user"))
            user_name = user_result.first()
            print(f"   当前用户: {user_name[0]}")

    except Exception as e:
        print(f"❌ 异步数据库连接失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # 测试数据库表
    print("\n" + "=" * 70)
    print("📊 步骤 3: 检查数据库表")
    print("=" * 70)

    try:
        async with AsyncSessionFactory() as session:
            # 查询所有表
            query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            result = await session.exec(query)
            tables = result.all()

            if tables:
                print(f"✅ 找到 {len(tables)} 个表:")
                for row in tables:
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
        pool = async_engine.pool
        print(f"✅ 连接池状态:")
        print(f"   连接池大小: {pool.size()}")
        print(f"   已签出连接: {pool.checkedout()}")
        print(f"   溢出连接: {pool.overflow()}")
        print(f"   总连接数: {pool.size() + pool.overflow()}")

    except Exception as e:
        print(f"⚠️  无法获取连接池状态: {e}")

    # 测试并发查询性能
    print("\n" + "=" * 70)
    print("⚡ 步骤 5: 测试并发查询性能")
    print("=" * 70)

    try:
        import time

        async def single_query():
            """单次查询"""
            async with AsyncSessionFactory() as session:
                result = await session.exec(text("SELECT 1"))
                return result.first()

        # 测试 10 次并发查询
        start_time = time.time()
        tasks = [single_query() for _ in range(10)]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        print(f"✅ 10 次并发查询耗时: {elapsed:.3f} 秒")
        print(f"   平均每次: {elapsed / 10 * 1000:.2f} 毫秒")

    except Exception as e:
        print(f"⚠️  性能测试失败: {e}")
        import traceback

        traceback.print_exc()

    # 测试事务
    print("\n" + "=" * 70)
    print("🔄 步骤 6: 测试事务支持")
    print("=" * 70)

    try:
        async with AsyncSessionFactory() as session:
            # 开始事务
            async with session.begin():
                result = await session.exec(text("SELECT 1"))
                result.first()
            print("✅ 事务测试通过")

    except Exception as e:
        print(f"⚠️  事务测试失败: {e}")

    # 关闭引擎
    print("\n" + "=" * 70)
    print("🔚 步骤 7: 清理资源")
    print("=" * 70)

    try:
        await async_engine.dispose()
        print("✅ 异步引擎已关闭")
    except Exception as e:
        print(f"⚠️  关闭引擎失败: {e}")


# 运行异步测试
if __name__ == "__main__":
    try:
        asyncio.run(test_async_database())

        # 总结
        print("\n" + "=" * 70)
        print("✅ 异步数据库测试通过！配置正确，连接正常。")
        print("=" * 70 + "\n")

    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
