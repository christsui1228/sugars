# ETL 定时任务配置指南

## 方案：APScheduler（Python 内置定时任务）

### 优点
- 纯 Python 实现，不污染 Dockerfile
- 代码集成，易于调试和监控
- 跨平台，本地和生产环境一致

### 缺点
- 容器重启期间会漏执行（可通过启动时补偿）

---

## 实施步骤

### 1. 安装依赖

```bash
pdm add apscheduler
```

### 2. 修改 `sugars/main.py`

在 lifespan 中启动定时任务：

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

from .routers import market
from .etl_service import fetch_and_store_data

# 创建调度器
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # [Startup] 启动时执行
    logger.info("🚀 Sugar Nexus API is starting up...")
    
    # 启动定时任务：每天凌晨 2:00 执行 ETL
    scheduler.add_job(
        lambda: asyncio.to_thread(fetch_and_store_data),
        CronTrigger(hour=2, minute=0),
        id="daily_etl",
        name="每日数据抓取",
        replace_existing=True
    )
    scheduler.start()
    logger.info("⏰ ETL 定时任务已启动 (每天 02:00)")
    
    yield
    
    # [Shutdown] 关闭时执行
    scheduler.shutdown()
    logger.info("👋 Sugar Nexus API is shutting down...")
```

### 3. 添加手动触发接口（可选）

在 `sugars/routers/market.py` 添加：

```python
from ..etl_service import fetch_and_store_data

@router.post("/etl/trigger", tags=["管理"])
def trigger_etl():
    """手动触发 ETL 任务"""
    result = fetch_and_store_data()
    return result
```

### 4. 修改 ETL 存储策略

编辑 `sugars/etl_service.py`，删除 30 天限制：

```python
# 删除或注释掉这一行（约第 145 行）
# .filter(pl.col("record_date") >= (date.today() - timedelta(days=30)))

# 改为：保留所有数据
df_final = (
    q_sugar.join(q_fx, on="record_date", how="left")
    .join(q_bdi, on="record_date", how="left")
    .sort("record_date")
    .with_columns([
        pl.col("usd_cny_rate").forward_fill(),
        pl.col("bdi_index").forward_fill(),
    ])
    # 可选：只保留最近 1 年数据
    # .filter(pl.col("record_date") >= (date.today() - timedelta(days=365)))
)
```

---

## 部署后验证

### 1. 查看日志确认定时任务启动

```bash
docker logs sugars-api | grep "ETL 定时任务"
```

### 2. 手动触发测试

```bash
curl -X POST https://sugar-api.thankscrw.top/api/market/etl/trigger
```

### 3. 查看下次执行时间

在 `main.py` 的 startup 中添加：

```python
next_run = scheduler.get_job("daily_etl").next_run_time
logger.info(f"📅 下次 ETL 执行时间: {next_run}")
```

---

## 时区配置

确保容器时区正确（中国时区）：

### 方法 1：Dockerfile 设置

```dockerfile
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
```

### 方法 2：docker-compose.yml

```yaml
services:
  api:
    environment:
      - TZ=Asia/Shanghai
```

---

## 监控和告警（可选）

### 添加执行日志

修改 `etl_service.py`：

```python
from loguru import logger

def fetch_and_store_data():
    logger.info(f"🚀 [ETL Start] {datetime.now()}")
    try:
        # ... 原有逻辑
        logger.info(f"🎉 ETL 完成! 新增: {count_new}, 更新: {count_update}")
        return {"status": "success", "new": count_new, "updated": count_update}
    except Exception as e:
        logger.error(f"❌ ETL 失败: {e}")
        # TODO: 发送告警通知（邮件/钉钉/Slack）
        raise
```

---

## 故障恢复

如果容器在 ETL 执行期间重启，数据会丢失当天更新。

### 解决方案：启动时检查并补偿

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Sugar Nexus API is starting up...")
    
    # 检查今天是否已执行 ETL
    with Session(engine) as session:
        today = date.today()
        latest = session.exec(
            select(MarketDaily).order_by(MarketDaily.record_date.desc()).limit(1)
        ).first()
        
        if not latest or latest.record_date < today:
            logger.warning("⚠️ 检测到数据未更新，立即执行 ETL...")
            await asyncio.to_thread(fetch_and_store_data)
    
    # 启动定时任务
    scheduler.add_job(...)
    scheduler.start()
    
    yield
    scheduler.shutdown()
```

---

## 回填历史数据

首次部署时，手动回填历史数据：

```bash
# 进入容器
docker exec -it sugars-api bash

# 运行 ETL（会自动获取 AkShare 提供的历史数据）
python -m sugars.etl_service
```

---

## 常见问题

### Q: 定时任务没有执行？
A: 检查容器时区和日志：`docker exec sugars-api date`

### Q: 如何修改执行时间？
A: 修改 `CronTrigger(hour=2, minute=0)` 参数后重启容器

### Q: 如何暂停定时任务？
A: `scheduler.pause_job("daily_etl")`

### Q: 数据库空间不够？
A: 添加数据清理策略，只保留最近 2 年数据
