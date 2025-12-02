"""瘦路由示例（同步）—— 仅协调层，不含业务实现"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database_sync import get_db

from ..features.demo.schemas import DemoItemCreate, DemoItemUpdate, DemoItemRead
from ..features.demo import crud_sync as crud
from ..features.demo.dependencies import require_permission

router = APIRouter(prefix="/demo-slim-sync", tags=["Demo 瘦路由（同步）"])


@router.get("/items", response_model=list[DemoItemRead], summary="查询物品列表")
def list_items(
    db: Session = Depends(get_db),
    _=Depends(require_permission("demo:read")),
):
    return crud.get_items(db)


@router.get("/items/{item_id}", response_model=DemoItemRead, summary="物品详情")
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("demo:read")),
):
    item = crud.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="物品不存在")
    return item


@router.post("/items", response_model=DemoItemRead, status_code=201, summary="创建物品")
def create_item(
    payload: DemoItemCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("demo:write")),
):
    return crud.create_item(db, payload)


@router.patch("/items/{item_id}", response_model=DemoItemRead, summary="更新物品")
def patch_item(
    item_id: int,
    payload: DemoItemUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("demo:write")),
):
    try:
        return crud.update_item(db, item_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/items/{item_id}", status_code=204, summary="删除物品")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("demo:write")),
):
    try:
        crud.delete_item(db, item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return None
