# ETL 定时任务实施方案

## 架构设计

### 目录结构

```
sugars/
├── main.py                    # 保持简洁，只负责启动/停止
├── etl_service.py             # ETL 业务逻辑（数据抓取和存储）
├── events/                    # 事件驱动模块（新增）
│   ├── __init__.py           # 导出接口
│   ├── scheduler.py          # 调度器配置和启动逻辑
│   └── routes.py             # ETL 管理接口（手动触发、状态查询）
├── routers/
│   └── market.py             # 市场数据查询接口
└── core/
    ├── config.py
    └── database_sync.py
```

### 设计原则

1. **关注点分离**
   - `main.py`: 只负责应用启动和生命周期管理
   - `events/scheduler.py`: 定时任务的配置和调度逻辑
   - `etl_service.py`: ETL 业务逻辑
   - `events/routes.py`: ETL 管理接口

2. **无消息队列依赖**
   - 使用 APScheduler 内置调度
   - 适合单实例部署
   - 启动时自动补偿机制

3. **易于测试和维护**
   - 每个模块职责单一
   - 可独立测试 ETL 逻辑
   - 支持手动触发

---

## 核心功能

### 1. 自动定时执行

**时间：** 每天凌晨 2:00（Asia/Shanghai 时区）

**逻辑：**
```python
# events/scheduler.py
scheduler.add_job(
    fetch_and_store_data,
    CronTrigger(hour=2, minute=0),
    id="daily_etl",
    name="每日数据抓取"
)
```

### 2. 启动时补偿机制

**场景：** 容器在 ETL 执行期间重启，导致当天数据缺失

**解决：** 启动时检查最新数据日期，如果不是今天则立即执行

```python
def check_and_run_etl():
    latest = session.exec(
        select(MarketDaily)
        .order_by(MarketDaily.record_date.desc())
        .limit(1)
    ).first()
    
    if not latest or latest.record_date < date.today():
        logger.warning("⚠️ 数据未更新，立即执行 ETL...")
        fetch_and_store_data()
```

### 3. 手动触发接口

**接口：** `POST /api/etl/trigger`

**用途：**
- 首次部署后回填历史数据
- 数据异常时手动重新抓取
- 测试 ETL 流程

**示例：**
```bash
curl -X POST http://localhost:8001/api/etl/trigger
```

### 4. 状态查询接口

**接口：** `GET /api/etl/status`

**返回：**
```json
{
  "status": "running",
  "job_id": "daily_etl",
  "job_name": "每日数据抓取",
  "next_run_time": "2025-12-05T02:00:00+08:00",
  "trigger": "cron[hour='2', minute='0']"
}
```

---

## 使用指南

### 本地开发

```bash
# 启动后端（会自动启动定时任务）
pdm run uvicorn sugars.main:app --reload --port 8001

# 查看日志
# ⏰ ETL 定时任务已启动
# 📅 执行时间: 每天 02:00 (Asia/Shanghai)
# 🕐 下次执行: 2025-12-05 02:00:00+08:00
```

### 手动触发 ETL

```bash
# 方式 1：通过 API
curl -X POST http://localhost:8001/api/etl/trigger

# 方式 2：直接运行脚本
cd /home/chris/coding/sugars
pdm run python -m sugars.etl_service
```

### 查看任务状态

```bash
curl http://localhost:8001/api/etl/status
```

### 生产部署

```bash
# 1. 构建镜像
docker build -t sugars-api .

# 2. 启动容器（确保时区正确）
docker run -d \
  --name sugars-api \
  -p 8001:8001 \
  -e TZ=Asia/Shanghai \
  sugars-api

# 3. 查看日志确认定时任务启动
docker logs sugars-api | grep "ETL"

# 4. 首次部署后手动触发回填历史数据
curl -X POST https://sugar-api.thankscrw.top/api/etl/trigger
```

---

## 监控和告警

### 日志监控

ETL 执行时会输出详细日志：

```
2025-12-04 02:00:00 | INFO | 🚀 [ETL Start] 开始抓取数据...
2025-12-04 02:00:15 | INFO | ✅ 数据抓取完成: 新增 1 条, 更新 0 条
2025-12-04 02:00:15 | INFO | 🎉 ETL 完成!
```

### 失败告警（可选扩展）

在 `etl_service.py` 中添加：

```python
def fetch_and_store_data():
    try:
        # ... ETL 逻辑
        logger.info("🎉 ETL 完成!")
    except Exception as e:
        logger.error(f"❌ ETL 失败: {e}")
        # TODO: 发送告警
        # send_alert_to_dingtalk(f"ETL 失败: {e}")
        raise
```

---

## 常见问题

### Q1: 如何修改执行时间？

修改 `events/scheduler.py`:

```python
# 改为每天 3:30 执行
CronTrigger(hour=3, minute=30)

# 改为每 6 小时执行一次
CronTrigger(hour='*/6')
```

### Q2: 如何暂停定时任务？

```python
from sugars.events import scheduler

# 暂停
scheduler.pause_job("daily_etl")

# 恢复
scheduler.resume_job("daily_etl")
```

### Q3: 容器重启会丢失数据吗？

不会。启动时会自动检查并补偿：
- 如果最新数据不是今天 → 立即执行 ETL
- 如果已是最新 → 跳过，等待下次定时执行

### Q4: 如何清理历史数据？

修改 `etl_service.py`，添加数据保留策略：

```python
# 只保留最近 2 年数据
df_final = df_final.filter(
    pl.col("record_date") >= (date.today() - timedelta(days=730))
)
```

### Q5: 支持多实例部署吗？

当前方案适合单实例。如需多实例，建议：
- 使用外部调度器（如 Celery + Redis）
- 或使用分布式锁（如 Redis SETNX）

---

## 测试清单

- [ ] 启动后查看日志，确认定时任务已启动
- [ ] 调用 `/api/etl/status` 查看下次执行时间
- [ ] 调用 `/api/etl/trigger` 手动触发，确认数据入库
- [ ] 查询 `/api/market/daily/latest` 确认数据正确
- [ ] 重启容器，确认启动时补偿机制生效
- [ ] 等待定时任务自动执行（或修改时间测试）

---

## 后续优化方向

1. **数据质量监控**
   - 检查数据完整性（是否有缺失字段）
   - 检查数据合理性（价格是否异常）

2. **性能优化**
   - 增量更新（只更新最近 N 天）
   - 批量插入优化

3. **告警通知**
   - 集成钉钉/企业微信/邮件
   - ETL 失败自动通知

4. **数据备份**
   - 定期导出数据到 S3/OSS
   - 数据库定期备份

---

**创建时间：** 2025-12-04  
**维护者：** christsui1228
