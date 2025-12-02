# 数据库连接测试修复说明

## 问题描述

运行 `pdm run scripts/test_db_connection_sync.py` 时出现错误：
```
❌ 配置加载失败: attempted relative import with no known parent package
```

## 根本原因

1. **缺少 `__init__.py` 文件**：`sugars/`, `sugars/core/`, `sugars/scripts/` 目录缺少 `__init__.py`，导致无法作为 Python 包导入
2. **使用了相对导入**：测试脚本使用了 `from .core.config import settings` 这样的相对导入，但脚本是直接运行的，不是作为包的一部分
3. **缺少导入**：`database_async.py` 中使用了 `async_sessionmaker` 但没有导入

## 修复内容

### 1. 创建 `__init__.py` 文件

- `sugars/__init__.py`
- `sugars/core/__init__.py`
- `sugars/scripts/__init__.py`

### 2. 修复导入语句

**test_db_connection_sync.py**:
```python
# 修改前
from .core.config import settings
from .core.database_sync import engine, SessionFactory

# 修改后
from sugars.core.config import settings
from sugars.core.database_sync import engine, SessionFactory
```

**test_db_connection_async.py**:
```python
# 修改前
from .core.config import settings
from .core.database_async import async_engine, AsyncSessionFactory

# 修改后
from sugars.core.config import settings
from sugars.core.database_async import async_engine, AsyncSessionFactory
```

### 3. 修复 database_async.py 导入

```python
# 修改前
from sqlalchemy.ext.asyncio import create_async_engine

# 修改后
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
```

### 4. 添加 PDM 快捷命令

在 `pyproject.toml` 中添加：
```toml
[tool.pdm.scripts]
test-db-sync = {cmd = "python sugars/scripts/test_db_connection_sync.py", env = {PYTHONPATH = "."}}
test-db-async = {cmd = "python sugars/scripts/test_db_connection_async.py", env = {PYTHONPATH = "."}}
```

## 使用方法

现在可以使用以下命令测试数据库连接：

```bash
# 测试同步数据库连接
pdm run test-db-sync

# 测试异步数据库连接
pdm run test-db-async
```

## 测试结果

两个测试脚本都成功运行，输出显示：
- ✅ 配置加载成功
- ✅ 数据库连接成功
- ✅ 连接池正常工作
- ✅ 查询性能正常

## 注意事项

- 确保 PostgreSQL 数据库正在运行
- 确保 `.env.development` 文件配置正确
- 如果数据库中没有表，需要运行 `pdm run db-init` 进行迁移
