"""定时任务调度器配置"""

import asyncio
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlmodel import Session, select

from ..etl_service import fetch_and_store_data
from ..core.database_sync import engine
from ..models import MarketDaily

# 创建调度器实例
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


def check_and_run_etl():
    """检查并执行 ETL 任务（启动时补偿机制）"""
    try:
        with Session(engine) as session:
            today = date.today()
            latest = session.exec(
                select(MarketDaily)
                .order_by(MarketDaily.record_date.desc())
                .limit(1)
            ).first()

            if not latest or latest.record_date < today:
                logger.warning(f"⚠️ 数据未更新（最新: {latest.record_date if latest else 'None'}），立即执行 ETL...")
                fetch_and_store_data()
            else:
                logger.info(f"✅ 数据已是最新（{latest.record_date}），跳过启动 ETL")
    except Exception as e:
        logger.error(f"❌ 启动检查失败: {e}")


def start_scheduler():
    """启动定时任务调度器"""
    # 启动时检查并补偿
    check_and_run_etl()

    # 添加定时任务：每天凌晨 2:00 执行
    scheduler.add_job(
        fetch_and_store_data,
        CronTrigger(hour=2, minute=0),
        id="daily_etl",
        name="每日数据抓取",
        replace_existing=True,
    )

    scheduler.start()
    
    # 显示下次执行时间
    next_run = scheduler.get_job("daily_etl").next_run_time
    logger.info(f"⏰ ETL 定时任务已启动")
    logger.info(f"📅 执行时间: 每天 02:00 (Asia/Shanghai)")
    logger.info(f"🕐 下次执行: {next_run}")


def stop_scheduler():
    """停止定时任务调度器"""
    scheduler.shutdown()
    logger.info("⏹️ ETL 定时任务已停止")
