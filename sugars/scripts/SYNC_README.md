# 数据库全量同步工具

通用的 PostgreSQL 数据库全量同步脚本，支持从本地 Docker 容器同步到 RDS。

## 特性

- ✅ **全库同步** - 自动同步所有表、索引、约束
- ✅ **配置文件驱动** - 支持多项目、多环境配置
- ✅ **安全备份** - 同步前可选备份 RDS 数据
- ✅ **错误处理** - 遇到错误自动停止并回滚
- ✅ **自动清理** - 临时文件自动删除

## 快速开始

### 1. 创建配置文件

```bash
cp scripts/sync_data_to_rds_config.env.example scripts/sync_data_to_rds_config.env
```

编辑 `sync_data_to_rds_config.env`，填入你的数据库配置：

```bash
LOCAL_CONTAINER="rag_service-postgres-1"
LOCAL_DB="rag_db"
LOCAL_USER="user"

RDS_HOST="your-rds-host.rds.aliyuncs.com"
RDS_USER="postgres"
RDS_DB="rag_db"
```

### 2. 执行同步

```bash
# 使用配置文件
./scripts/sync_data_to_rds.sh scripts/sync_data_to_rds_config.env

# 或使用默认配置（sync_data_to_rds_config.env）
./scripts/sync_data_to_rds.sh
```

### 3. 按提示操作

脚本会依次提示：
1. 输入 RDS 密码
2. 是否备份 RDS 数据（推荐）
3. 确认同步操作（输入 `yes`）

## 使用场景

### 场景 1: 本地测试数据同步到 RDS

```bash
# 1. 在本地 Docker 中准备好测试数据
docker-compose up -d

# 2. 执行同步
./scripts/sync_data_to_rds.sh

# 3. 在 RDS 上验证数据
```

### 场景 2: 多项目管理

为不同项目创建不同的配置文件：

```bash
# RAG 项目
./scripts/sync_data_to_rds.sh scripts/sync_data_to_rds_config_rag.env

# OneManage 项目
./scripts/sync_data_to_rds.sh scripts/sync_data_to_rds_config_onemanage.env
```

### 场景 3: 环境迁移

```bash
# 开发环境 -> 测试环境
./scripts/sync_data_to_rds.sh scripts/sync_data_to_rds_config_dev_to_test.env

# 测试环境 -> 生产环境（谨慎！）
./scripts/sync_data_to_rds.sh scripts/sync_data_to_rds_config_test_to_prod.env
```

## 配置说明

### 必填配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `LOCAL_CONTAINER` | 本地 PostgreSQL 容器名 | `rag_service-postgres-1` |
| `LOCAL_DB` | 本地数据库名 | `rag_db` |
| `LOCAL_USER` | 本地数据库用户 | `user` |
| `RDS_HOST` | RDS 主机地址 | `xxx.rds.aliyuncs.com` |
| `RDS_USER` | RDS 用户名 | `postgres` |
| `RDS_DB` | RDS 数据库名 | `rag_db` |

### 可选配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `RDS_PORT` | RDS 端口 | `5432` |
| `RDS_PASSWORD` | RDS 密码 | 留空则运行时输入 |

## 安全建议

### 密码管理

**不推荐**：在配置文件中明文存储密码
```bash
RDS_PASSWORD="your_password"  # ❌ 不安全
```

**推荐**：运行时输入密码
```bash
RDS_PASSWORD=""  # ✅ 脚本会提示输入
```

**推荐**：使用环境变量
```bash
export RDS_PASSWORD="your_password"
./scripts/sync_data_to_rds.sh
```

### .gitignore 配置

确保配置文件不被提交到 Git：

```gitignore
# 数据库同步配置
scripts/sync_data_to_rds_config.env
scripts/sync_data_to_rds_config_*.env
scripts/*_backup_*.sql
scripts/temp_*.sql
```

## 故障排查

### 问题 1: 容器未运行

```
Error: No such container: rag_service-postgres-1
```

**解决**：启动本地数据库容器
```bash
docker-compose up -d postgres
```

### 问题 2: 权限不足

```
ERROR: permission denied for database
```

**解决**：检查 RDS 用户权限，确保有 CREATE/DROP 权限

### 问题 3: 连接超时

```
could not connect to server
```

**解决**：
1. 检查 RDS 白名单是否包含你的 IP
2. 检查 RDS 安全组配置
3. 确认 RDS 主机地址和端口正确

### 问题 4: 数据冲突

```
ERROR: duplicate key value violates unique constraint
```

**解决**：脚本使用 `--clean --if-exists` 参数，会自动清理旧数据。如果仍有问题，手动清空 RDS：

```bash
# 连接到 RDS
psql -h your-rds-host -U postgres -d rag_db

# 删除所有表
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

## 高级用法

### 仅导出数据（不含结构）

修改脚本中的 `pg_dump` 参数：

```bash
docker exec $LOCAL_CONTAINER pg_dump \
    -U $LOCAL_USER \
    -d $LOCAL_DB \
    --data-only \
    > $TEMP_DUMP
```

### 排除特定表

```bash
docker exec $LOCAL_CONTAINER pg_dump \
    -U $LOCAL_USER \
    -d $LOCAL_DB \
    --exclude-table=alembic_version \
    --exclude-table=temp_* \
    > $TEMP_DUMP
```

### 压缩导出文件

```bash
docker exec $LOCAL_CONTAINER pg_dump \
    -U $LOCAL_USER \
    -d $LOCAL_DB \
    -Fc \
    > $TEMP_DUMP.dump

# 导入时使用 pg_restore
pg_restore -h $RDS_HOST -U $RDS_USER -d $RDS_DB $TEMP_DUMP.dump
```

## 性能优化

### 大数据库同步

对于大型数据库（>1GB），建议：

1. **使用压缩格式**
```bash
pg_dump -Fc  # 自定义格式，支持压缩和并行
```

2. **并行导入**
```bash
pg_restore -j 4  # 使用 4 个并行任务
```

3. **分批同步**
```bash
# 先同步结构
pg_dump --schema-only

# 再分表同步数据
pg_dump --data-only -t table1
pg_dump --data-only -t table2
```

## 相关命令

### 查看本地数据库大小

```bash
docker exec rag_service-postgres-1 psql -U user -d rag_db -c "
SELECT 
    pg_size_pretty(pg_database_size('rag_db')) as db_size;
"
```

### 查看 RDS 数据库大小

```bash
docker run --rm -e PGPASSWORD="$RDS_PASSWORD" postgres:18 psql \
    -h your-rds-host -U postgres -d rag_db -c "
SELECT 
    pg_size_pretty(pg_database_size('rag_db')) as db_size;
"
```

### 对比本地和 RDS 数据

```bash
# 本地表数量
docker exec rag_service-postgres-1 psql -U user -d rag_db -c "
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
"

# RDS 表数量
docker run --rm -e PGPASSWORD="$RDS_PASSWORD" postgres:18 psql \
    -h your-rds-host -U postgres -d rag_db -c "
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
"
```
