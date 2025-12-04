"""ETL 管理接口"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from ..etl_service import fetch_and_store_data
from .scheduler import scheduler

router = APIRouter(prefix="/etl", tags=["ETL 管理"])


@router.post("/trigger", summary="手动触发 ETL 任务")
def trigger_etl():
    """立即执行一次 ETL 数据抓取"""
    try:
        logger.info("🔧 手动触发 ETL 任务...")
        result = fetch_and_store_data()
        return {
            "status": "success",
            "message": "ETL 执行完成",
            "result": result,
        }
    except Exception as e:
        logger.error(f"❌ ETL 执行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", summary="查看定时任务状态")
def get_etl_status():
    """获取 ETL 定时任务的状态信息"""
    job = scheduler.get_job("daily_etl")
    if not job:
        return {"status": "not_configured"}

    return {
        "status": "running" if scheduler.running else "stopped",
        "job_id": job.id,
        "job_name": job.name,
        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        "trigger": str(job.trigger),
    }
