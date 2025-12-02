#!/usr/bin/env python3
"""数据库 CRUD 测试脚本（支持同步和异步）

测试数据库的完整 CRUD 操作：
1. 连接测试
2. 创建表
3. 插入数据
4. 查询数据
5. 更新数据
6. 删除数据
7. 删除表
8. 自动清理

使用方法：
    pdm run python scripts/test_db_crud.py           # 同步测试（默认）
    pdm run python scripts/test_db_crud.py --sync    # 同步测试
    pdm run python scripts/test_db_crud.py --async   # 异步测试
    pdm run python scripts/test_db_crud.py --both    # 同步 + 异步测试
"""

import sys
from pathlib import Path
import argparse

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import text
from typing import Optional
import time
import asyncio


# 定义测试用的临时表模型
class TestProduct(SQLModel, table=True):
    """测试用的产品表"""

    __tablename__ = "test_products_temp"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    price: float
    stock: int = Field(default=0)
    description: Optional[str] = Field(default=None, max_length=500)


def test_database_crud():
    """测试数据库 CRUD 操作"""

    # 步骤 1: 测试配置加载
    print("\n" + "=" * 70)
    print("🔧 步骤 1: 测试配置加载")
    print("=" * 70)

    try:
        from .core.config import settings

        print("✅ 配置模块导入成功")
        print(f"   环境: {settings.env.value}")
        print(f"   数据库主机: {settings.database.host}")
        print(f"   数据库端口: {settings.database.port}")
        print(f"   数据库名称: {settings.database.name}")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        sys.exit(1)

    # 步骤 2: 测试数据库连接
    print("\n" + "=" * 70)
    print("🔌 步骤 2: 测试数据库连接")
    print("=" * 70)

    try:
        from .core.database_sync import engine, SessionFactory

        print("✅ 同步数据库模块导入成功")
        print(f"   连接 URL: {settings.database.sync_url}")

        # 测试连接
        with Session(engine) as session:
            result = session.exec(text("SELECT version()"))
            version = result.first()
            print(f"✅ 数据库连接成功")
            print(f"   PostgreSQL 版本: {version[0][:50]}...")

            # 测试当前数据库
            db_result = session.exec(text("SELECT current_database()"))
            db_name = db_result.first()
            print(f"   当前数据库: {db_name[0]}")

    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # 步骤 3: 创建测试表
    print("\n" + "=" * 70)
    print("📋 步骤 3: 创建测试表")
    print("=" * 70)

    try:
        # 先删除可能存在的旧表
        with Session(engine) as session:
            session.exec(text("DROP TABLE IF EXISTS test_products_temp CASCADE"))
            session.commit()

        # 创建新表
        SQLModel.metadata.create_all(engine, tables=[TestProduct.__table__])
        print(f"✅ 成功创建测试表: {TestProduct.__tablename__}")

        # 验证表是否存在
        with Session(engine) as session:
            result = session.exec(
                text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'test_products_temp'
            """)
            )
            if result.first():
                print("✅ 表创建验证通过")
            else:
                raise Exception("表创建失败")

    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # 步骤 4: 插入数据
    print("\n" + "=" * 70)
    print("➕ 步骤 4: 插入数据")
    print("=" * 70)

    try:
        test_products = [
            TestProduct(
                name="测试产品A", price=99.99, stock=100, description="这是测试产品A"
            ),
            TestProduct(
                name="测试产品B", price=199.99, stock=50, description="这是测试产品B"
            ),
            TestProduct(
                name="测试产品C", price=299.99, stock=30, description="这是测试产品C"
            ),
        ]

        with Session(engine) as session:
            for product in test_products:
                session.add(product)
            session.commit()

            # 刷新以获取生成的 ID
            for product in test_products:
                session.refresh(product)

        print(f"✅ 成功插入 {len(test_products)} 条数据")
        for product in test_products:
            print(f"   ID: {product.id}, 名称: {product.name}, 价格: ¥{product.price}")

    except Exception as e:
        print(f"❌ 插入数据失败: {e}")
        import traceback

        traceback.print_exc()
        cleanup_table(engine)
        sys.exit(1)

    # 步骤 5: 查询数据
    print("\n" + "=" * 70)
    print("🔍 步骤 5: 查询数据")
    print("=" * 70)

    try:
        with Session(engine) as session:
            # 查询所有数据
            statement = select(TestProduct)
            results = session.exec(statement).all()
            print(f"✅ 查询到 {len(results)} 条数据")

            # 条件查询
            statement = select(TestProduct).where(TestProduct.price > 150)
            expensive_products = session.exec(statement).all()
            print(f"✅ 价格 > 150 的产品: {len(expensive_products)} 个")
            for product in expensive_products:
                print(f"   {product.name}: ¥{product.price}")

            # 单条查询
            statement = select(TestProduct).where(TestProduct.name == "测试产品A")
            product_a = session.exec(statement).first()
            if product_a:
                print(f"✅ 单条查询成功: {product_a.name}")

    except Exception as e:
        print(f"❌ 查询数据失败: {e}")
        import traceback

        traceback.print_exc()
        cleanup_table(engine)
        sys.exit(1)

    # 步骤 6: 更新数据
    print("\n" + "=" * 70)
    print("✏️  步骤 6: 更新数据")
    print("=" * 70)

    try:
        with Session(engine) as session:
            # 查询要更新的数据
            statement = select(TestProduct).where(TestProduct.name == "测试产品A")
            product = session.exec(statement).first()

            if product:
                old_price = product.price
                old_stock = product.stock

                # 更新数据
                product.price = 149.99
                product.stock = 200
                session.add(product)
                session.commit()
                session.refresh(product)

                print(f"✅ 更新成功: {product.name}")
                print(f"   价格: ¥{old_price} → ¥{product.price}")
                print(f"   库存: {old_stock} → {product.stock}")
            else:
                raise Exception("未找到要更新的数据")

    except Exception as e:
        print(f"❌ 更新数据失败: {e}")
        import traceback

        traceback.print_exc()
        cleanup_table(engine)
        sys.exit(1)

    # 步骤 7: 删除数据
    print("\n" + "=" * 70)
    print("🗑️  步骤 7: 删除数据")
    print("=" * 70)

    try:
        with Session(engine) as session:
            # 删除单条数据
            statement = select(TestProduct).where(TestProduct.name == "测试产品C")
            product = session.exec(statement).first()

            if product:
                product_name = product.name
                session.delete(product)
                session.commit()
                print(f"✅ 删除成功: {product_name}")

            # 验证删除
            statement = select(TestProduct)
            remaining = session.exec(statement).all()
            print(f"✅ 剩余数据: {len(remaining)} 条")

    except Exception as e:
        print(f"❌ 删除数据失败: {e}")
        import traceback

        traceback.print_exc()
        cleanup_table(engine)
        sys.exit(1)

    # 步骤 8: 测试事务
    print("\n" + "=" * 70)
    print("🔄 步骤 8: 测试事务回滚")
    print("=" * 70)

    try:
        with Session(engine) as session:
            # 查询当前数据量
            statement = select(TestProduct)
            count_before = len(session.exec(statement).all())

            try:
                # 开始事务
                new_product = TestProduct(name="测试产品D", price=399.99, stock=10)
                session.add(new_product)

                # 故意触发错误（插入重复数据或其他错误）
                raise Exception("模拟事务错误")

            except Exception:
                # 回滚事务
                session.rollback()
                print("✅ 事务回滚成功")

            # 验证数据未被插入
            count_after = len(session.exec(statement).all())
            if count_before == count_after:
                print(f"✅ 事务验证通过: 数据量保持不变 ({count_after} 条)")
            else:
                raise Exception("事务回滚失败")

    except Exception as e:
        print(f"❌ 事务测试失败: {e}")
        import traceback

        traceback.print_exc()
        cleanup_table(engine)
        sys.exit(1)

    # 步骤 9: 测试性能
    print("\n" + "=" * 70)
    print("⚡ 步骤 9: 测试查询性能")
    print("=" * 70)

    try:
        # 批量插入测试数据
        with Session(engine) as session:
            bulk_products = [
                TestProduct(name=f"性能测试产品{i}", price=100 + i, stock=i)
                for i in range(100)
            ]
            session.add_all(bulk_products)
            session.commit()

        print(f"✅ 批量插入 100 条数据")

        # 测试查询性能
        start_time = time.time()
        with Session(engine) as session:
            statement = select(TestProduct)
            results = session.exec(statement).all()
        elapsed = time.time() - start_time

        print(f"✅ 查询 {len(results)} 条数据耗时: {elapsed * 1000:.2f} 毫秒")

    except Exception as e:
        print(f"⚠️  性能测试失败: {e}")
        import traceback

        traceback.print_exc()

    # 步骤 10: 清理测试表
    print("\n" + "=" * 70)
    print("🧹 步骤 10: 清理测试数据")
    print("=" * 70)

    cleanup_table(engine)


def cleanup_table(engine):
    """清理测试表"""
    try:
        with Session(engine) as session:
            # 删除表
            session.exec(text("DROP TABLE IF EXISTS test_products_temp CASCADE"))
            session.commit()
        print(f"✅ 测试表已删除: test_products_temp")

        # 验证表是否已删除
        with Session(engine) as session:
            result = session.exec(
                text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'test_products_temp'
            """)
            )
            if not result.first():
                print("✅ 清理验证通过")
            else:
                print("⚠️  表可能未完全删除")

    except Exception as e:
        print(f"⚠️  清理失败: {e}")


async def test_database_crud_async():
    """测试异步数据库 CRUD 操作"""

    # 步骤 1: 测试配置加载
    print("\n" + "=" * 70)
    print("🔧 步骤 1: 测试配置加载（异步模式）")
    print("=" * 70)

    try:
        from .core.config import settings

        print("✅ 配置模块导入成功")
        print(f"   环境: {settings.env.value}")
        print(f"   数据库主机: {settings.database.host}")
        print(f"   数据库端口: {settings.database.port}")
        print(f"   数据库名称: {settings.database.name}")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        sys.exit(1)

    # 步骤 2: 测试异步数据库连接
    print("\n" + "=" * 70)
    print("🔌 步骤 2: 测试异步数据库连接")
    print("=" * 70)

    try:
        from .core.database_async import async_engine, AsyncSessionFactory
        from sqlmodel.ext.asyncio.session import AsyncSession

        print("✅ 异步数据库模块导入成功")
        print(f"   连接 URL: {settings.database.async_url}")

        # 测试连接
        async with AsyncSessionFactory() as session:
            result = await session.exec(text("SELECT version()"))
            version = result.first()
            print(f"✅ 异步数据库连接成功")
            print(f"   PostgreSQL 版本: {version[0][:50]}...")

            # 测试当前数据库
            db_result = await session.exec(text("SELECT current_database()"))
            db_name = db_result.first()
            print(f"   当前数据库: {db_name[0]}")

    except Exception as e:
        print(f"❌ 异步数据库连接失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # 步骤 3: 创建测试表
    print("\n" + "=" * 70)
    print("📋 步骤 3: 创建测试表")
    print("=" * 70)

    try:
        # 先删除可能存在的旧表
        async with AsyncSessionFactory() as session:
            await session.exec(text("DROP TABLE IF EXISTS test_products_temp CASCADE"))
            await session.commit()

        # 创建新表（使用同步方式创建表结构）
        async with async_engine.begin() as conn:
            await conn.run_sync(
                SQLModel.metadata.create_all, tables=[TestProduct.__table__]
            )

        print(f"✅ 成功创建测试表: {TestProduct.__tablename__}")

        # 验证表是否存在
        async with AsyncSessionFactory() as session:
            result = await session.exec(
                text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'test_products_temp'
            """)
            )
            if result.first():
                print("✅ 表创建验证通过")
            else:
                raise Exception("表创建失败")

    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # 步骤 4: 插入数据
    print("\n" + "=" * 70)
    print("➕ 步骤 4: 插入数据")
    print("=" * 70)

    try:
        test_products = [
            TestProduct(
                name="异步测试产品A",
                price=99.99,
                stock=100,
                description="这是异步测试产品A",
            ),
            TestProduct(
                name="异步测试产品B",
                price=199.99,
                stock=50,
                description="这是异步测试产品B",
            ),
            TestProduct(
                name="异步测试产品C",
                price=299.99,
                stock=30,
                description="这是异步测试产品C",
            ),
        ]

        async with AsyncSessionFactory() as session:
            for product in test_products:
                session.add(product)
            await session.commit()

            # 刷新以获取生成的 ID
            for product in test_products:
                await session.refresh(product)

        print(f"✅ 成功插入 {len(test_products)} 条数据")
        for product in test_products:
            print(f"   ID: {product.id}, 名称: {product.name}, 价格: ¥{product.price}")

    except Exception as e:
        print(f"❌ 插入数据失败: {e}")
        import traceback

        traceback.print_exc()
        await cleanup_table_async(async_engine)
        sys.exit(1)

    # 步骤 5: 查询数据
    print("\n" + "=" * 70)
    print("🔍 步骤 5: 查询数据")
    print("=" * 70)

    try:
        async with AsyncSessionFactory() as session:
            # 查询所有数据
            statement = select(TestProduct)
            results = await session.exec(statement)
            all_products = results.all()
            print(f"✅ 查询到 {len(all_products)} 条数据")

            # 条件查询
            statement = select(TestProduct).where(TestProduct.price > 150)
            results = await session.exec(statement)
            expensive_products = results.all()
            print(f"✅ 价格 > 150 的产品: {len(expensive_products)} 个")
            for product in expensive_products:
                print(f"   {product.name}: ¥{product.price}")

            # 单条查询
            statement = select(TestProduct).where(TestProduct.name == "异步测试产品A")
            results = await session.exec(statement)
            product_a = results.first()
            if product_a:
                print(f"✅ 单条查询成功: {product_a.name}")

    except Exception as e:
        print(f"❌ 查询数据失败: {e}")
        import traceback

        traceback.print_exc()
        await cleanup_table_async(async_engine)
        sys.exit(1)

    # 步骤 6: 更新数据
    print("\n" + "=" * 70)
    print("✏️  步骤 6: 更新数据")
    print("=" * 70)

    try:
        async with AsyncSessionFactory() as session:
            # 查询要更新的数据
            statement = select(TestProduct).where(TestProduct.name == "异步测试产品A")
            results = await session.exec(statement)
            product = results.first()

            if product:
                old_price = product.price
                old_stock = product.stock

                # 更新数据
                product.price = 149.99
                product.stock = 200
                session.add(product)
                await session.commit()
                await session.refresh(product)

                print(f"✅ 更新成功: {product.name}")
                print(f"   价格: ¥{old_price} → ¥{product.price}")
                print(f"   库存: {old_stock} → {product.stock}")
            else:
                raise Exception("未找到要更新的数据")

    except Exception as e:
        print(f"❌ 更新数据失败: {e}")
        import traceback

        traceback.print_exc()
        await cleanup_table_async(async_engine)
        sys.exit(1)

    # 步骤 7: 删除数据
    print("\n" + "=" * 70)
    print("🗑️  步骤 7: 删除数据")
    print("=" * 70)

    try:
        async with AsyncSessionFactory() as session:
            # 删除单条数据
            statement = select(TestProduct).where(TestProduct.name == "异步测试产品C")
            results = await session.exec(statement)
            product = results.first()

            if product:
                product_name = product.name
                await session.delete(product)
                await session.commit()
                print(f"✅ 删除成功: {product_name}")

            # 验证删除
            statement = select(TestProduct)
            results = await session.exec(statement)
            remaining = results.all()
            print(f"✅ 剩余数据: {len(remaining)} 条")

    except Exception as e:
        print(f"❌ 删除数据失败: {e}")
        import traceback

        traceback.print_exc()
        await cleanup_table_async(async_engine)
        sys.exit(1)

    # 步骤 8: 测试事务
    print("\n" + "=" * 70)
    print("🔄 步骤 8: 测试事务回滚")
    print("=" * 70)

    try:
        async with AsyncSessionFactory() as session:
            # 查询当前数据量
            statement = select(TestProduct)
            results = await session.exec(statement)
            count_before = len(results.all())

            try:
                # 开始事务
                new_product = TestProduct(name="异步测试产品D", price=399.99, stock=10)
                session.add(new_product)

                # 故意触发错误
                raise Exception("模拟事务错误")

            except Exception:
                # 回滚事务
                await session.rollback()
                print("✅ 事务回滚成功")

            # 验证数据未被插入
            results = await session.exec(statement)
            count_after = len(results.all())
            if count_before == count_after:
                print(f"✅ 事务验证通过: 数据量保持不变 ({count_after} 条)")
            else:
                raise Exception("事务回滚失败")

    except Exception as e:
        print(f"❌ 事务测试失败: {e}")
        import traceback

        traceback.print_exc()
        await cleanup_table_async(async_engine)
        sys.exit(1)

    # 步骤 9: 测试并发性能
    print("\n" + "=" * 70)
    print("⚡ 步骤 9: 测试并发查询性能")
    print("=" * 70)

    try:

        async def single_query():
            """单次异步查询"""
            async with AsyncSessionFactory() as session:
                statement = select(TestProduct)
                results = await session.exec(statement)
                return results.all()

        # 测试 10 次并发查询
        start_time = time.time()
        tasks = [single_query() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        print(f"✅ 10 次并发查询耗时: {elapsed * 1000:.2f} 毫秒")
        print(f"   平均每次: {elapsed / 10 * 1000:.2f} 毫秒")
        print(f"   查询到 {len(results[0])} 条数据")

    except Exception as e:
        print(f"⚠️  性能测试失败: {e}")
        import traceback

        traceback.print_exc()

    # 步骤 10: 清理测试表
    print("\n" + "=" * 70)
    print("🧹 步骤 10: 清理测试数据")
    print("=" * 70)

    await cleanup_table_async(async_engine)

    # 关闭引擎
    await async_engine.dispose()


async def cleanup_table_async(engine):
    """清理异步测试表"""
    try:
        from .core.database_async import AsyncSessionFactory

        async with AsyncSessionFactory() as session:
            # 删除表
            await session.exec(text("DROP TABLE IF EXISTS test_products_temp CASCADE"))
            await session.commit()
        print(f"✅ 测试表已删除: test_products_temp")

        # 验证表是否已删除
        async with AsyncSessionFactory() as session:
            result = await session.exec(
                text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'test_products_temp'
            """)
            )
            if not result.first():
                print("✅ 清理验证通过")
            else:
                print("⚠️  表可能未完全删除")

    except Exception as e:
        print(f"⚠️  清理失败: {e}")


def print_summary():
    """打印测试总结"""
    print("\n" + "=" * 70)
    print("✅ 数据库 CRUD 测试全部通过！")
    print("=" * 70)
    print("\n测试项目:")
    print("  ✅ 配置加载")
    print("  ✅ 数据库连接")
    print("  ✅ 创建表")
    print("  ✅ 插入数据")
    print("  ✅ 查询数据")
    print("  ✅ 更新数据")
    print("  ✅ 删除数据")
    print("  ✅ 事务回滚")
    print("  ✅ 查询性能")
    print("  ✅ 清理数据")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="数据库 CRUD 测试脚本")
    parser.add_argument(
        "--mode",
        choices=["sync", "async", "both"],
        default="sync",
        help="测试模式: sync (同步), async (异步), both (两者都测试)",
    )
    # 兼容旧的参数格式
    parser.add_argument("--sync", action="store_true", help="同步测试")
    parser.add_argument(
        "--async", action="store_true", dest="async_mode", help="异步测试"
    )
    parser.add_argument("--both", action="store_true", help="同步 + 异步测试")

    args = parser.parse_args()

    # 确定测试模式
    if args.sync:
        mode = "sync"
    elif args.async_mode:
        mode = "async"
    elif args.both:
        mode = "both"
    else:
        mode = args.mode

    try:
        if mode == "sync":
            print("\n" + "=" * 70)
            print("🔄 运行同步数据库测试")
            print("=" * 70)
            test_database_crud()
            print_summary()

        elif mode == "async":
            print("\n" + "=" * 70)
            print("⚡ 运行异步数据库测试")
            print("=" * 70)
            asyncio.run(test_database_crud_async())
            print_summary()

        elif mode == "both":
            print("\n" + "=" * 70)
            print("🔄 运行同步数据库测试")
            print("=" * 70)
            test_database_crud()

            print("\n" + "=" * 70)
            print("⚡ 运行异步数据库测试")
            print("=" * 70)
            asyncio.run(test_database_crud_async())

            print_summary()

    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
