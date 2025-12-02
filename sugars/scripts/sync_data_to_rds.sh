#!/bin/bash
# 通用数据库全量同步脚本
# 使用方法: ./scripts/sync_data_to_rds.sh [config_file]
# 示例: ./scripts/sync_data_to_rds.sh sync_data_to_rds_config.env

set -e  # 遇到错误立即退出

# ============================================
# 配置加载
# ============================================

# 默认配置文件
CONFIG_FILE="${1:-sync_data_to_rds_config.env}"

# 如果配置文件存在，则加载
if [ -f "$CONFIG_FILE" ]; then
    echo "📄 加载配置文件: $CONFIG_FILE"
    source "$CONFIG_FILE"
else
    echo "⚠️  未找到配置文件 $CONFIG_FILE，使用默认配置"
    
    # 默认配置（可根据项目修改）
    LOCAL_CONTAINER="${LOCAL_CONTAINER:-rag_service-postgres-1}"
    LOCAL_DB="${LOCAL_DB:-rag_db}"
    LOCAL_USER="${LOCAL_USER:-user}"
    LOCAL_PASSWORD="${LOCAL_PASSWORD:-password}"
    
    RDS_HOST="${RDS_HOST:-pgm-bp1tda565ghz358qho.pg.rds.aliyuncs.com}"
    RDS_USER="${RDS_USER:-postgres}"
    RDS_DB="${RDS_DB:-rag_db}"
    RDS_PORT="${RDS_PORT:-5432}"
fi

# ============================================
# 显示配置信息
# ============================================

echo "======================================"
echo "📦 PostgreSQL 全库同步工具"
echo "======================================"
echo ""
echo "源数据库:"
echo "  容器: $LOCAL_CONTAINER"
echo "  数据库: $LOCAL_DB"
echo "  用户: $LOCAL_USER"
echo ""
echo "目标数据库:"
echo "  主机: $RDS_HOST"
echo "  数据库: $RDS_DB"
echo "  用户: $RDS_USER"
echo ""

# ============================================
# 密码输入
# ============================================

if [ -z "$RDS_PASSWORD" ]; then
    read -sp "请输入 RDS 密码: " RDS_PASSWORD
    echo ""
fi

# ============================================
# 临时文件
# ============================================

TEMP_DUMP="./temp_full_dump_$(date +%Y%m%d_%H%M%S).sql"
trap "rm -f $TEMP_DUMP" EXIT  # 脚本退出时自动清理

# ============================================
# 步骤 1: 导出完整数据库
# ============================================

echo ""
echo "🔍 步骤 1/4: 从本地容器导出完整数据库..."
echo "   导出文件: $TEMP_DUMP"

# 使用 pg_dump 导出完整数据库（包含结构和数据）
docker exec $LOCAL_CONTAINER pg_dump \
    -U $LOCAL_USER \
    -d $LOCAL_DB \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    > $TEMP_DUMP

# 检查导出是否成功
if [ ! -s $TEMP_DUMP ]; then
    echo "❌ 导出失败或数据为空"
    exit 1
fi

FILE_SIZE=$(du -h $TEMP_DUMP | cut -f1)
LINE_COUNT=$(wc -l < $TEMP_DUMP)
echo "✅ 导出成功"
echo "   文件大小: $FILE_SIZE"
echo "   SQL 行数: $LINE_COUNT"

# ============================================
# 步骤 2: 备份 RDS 数据（可选）
# ============================================

echo ""
echo "💾 步骤 2/4: 备份 RDS 数据（可选）..."
read -p "是否备份 RDS 当前数据？(y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    BACKUP_FILE="./rds_backup_$(date +%Y%m%d_%H%M%S).sql"
    echo "   备份到: $BACKUP_FILE"
    
    docker run --rm \
        -e PGPASSWORD="$RDS_PASSWORD" \
        postgres:18 pg_dump \
        -h $RDS_HOST \
        -p $RDS_PORT \
        -U $RDS_USER \
        -d $RDS_DB \
        --clean \
        --if-exists \
        > $BACKUP_FILE
    
    echo "✅ RDS 数据已备份到 $BACKUP_FILE"
else
    echo "⏭️  跳过备份"
fi

# ============================================
# 步骤 3: 确认同步操作
# ============================================

echo ""
echo "⚠️  步骤 3/4: 确认同步操作"
echo "   这将完全覆盖 RDS 数据库: $RDS_DB"
echo "   源: $LOCAL_CONTAINER/$LOCAL_DB"
echo "   目标: $RDS_HOST/$RDS_DB"
echo ""
read -p "确认执行全库同步？(yes/N): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ 操作已取消"
    exit 0
fi

# ============================================
# 步骤 4: 导入到 RDS
# ============================================

echo ""
echo "📤 步骤 4/4: 导入数据到 RDS..."
echo "   这可能需要几分钟，请耐心等待..."

docker run -i --rm \
    -e PGPASSWORD="$RDS_PASSWORD" \
    postgres:18 psql \
    -h $RDS_HOST \
    -p $RDS_PORT \
    -U $RDS_USER \
    -d $RDS_DB \
    -v ON_ERROR_STOP=1 \
    < $TEMP_DUMP

echo "✅ 数据导入成功"

# ============================================
# 验证同步结果
# ============================================

echo ""
echo "======================================"
echo "✅ 同步完成！"
echo "======================================"
echo ""
echo "📊 验证数据..."

docker run --rm \
    -e PGPASSWORD="$RDS_PASSWORD" \
    postgres:18 psql \
    -h $RDS_HOST \
    -p $RDS_PORT \
    -U $RDS_USER \
    -d $RDS_DB \
    -c "
    SELECT 
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
    FROM pg_tables 
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
    "

echo ""
echo "🎉 全库同步完成！"
