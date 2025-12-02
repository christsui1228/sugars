"""市场数据路由 - 提供白糖市场数据查询接口"""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from ..core.database_sync import get_db
from ..models import MarketDaily, MarketDailyRead

router = APIRouter(prefix="/market", tags=["市场数据"])


@router.get("/daily", response_model=list[MarketDailyRead], summary="查询市场日数据")
def list_daily_data(
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    limit: int = Query(30, ge=1, le=365, description="返回记录数"),
    db: Session = Depends(get_db),
):
    """获取市场日数据列表，支持日期范围过滤"""
    query = select(MarketDaily).order_by(MarketDaily.record_date.desc())
    
    if start_date:
        query = query.where(MarketDaily.record_date >= start_date)
    if end_date:
        query = query.where(MarketDaily.record_date <= end_date)
    
    query = query.limit(limit)
    results = db.exec(query).all()
    return results


@router.get("/daily/{record_date}", response_model=MarketDailyRead, summary="查询指定日期数据")
def get_daily_data(
    record_date: date,
    db: Session = Depends(get_db),
):
    """获取指定日期的市场数据"""
    item = db.get(MarketDaily, record_date)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到日期 {record_date} 的数据"
        )
    return item


@router.get("/daily/latest", response_model=MarketDailyRead, summary="获取最新数据")
def get_latest_data(db: Session = Depends(get_db)):
    """获取最新的市场数据"""
    query = select(MarketDaily).order_by(MarketDaily.record_date.desc()).limit(1)
    result = db.exec(query).first()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无市场数据"
        )
    return result
