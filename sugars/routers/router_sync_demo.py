"""FastAPI 路由同步示例（参考模板）

本文件演示一个遵循最佳实践的路由模块结构，涵盖：
1. 导入顺序与 APIRouter 配置
2. SQLModel 数据模型与 CRUD
3. 依赖注入（数据库会话、权限、配置）
4. 错误处理与私有工具函数
5. 文档与注释均为中文

开发者可据此模板快速搭建新的同步路由模块。
"""

# ==================== 标准库导入 ====================
from __future__ import annotations

from typing import List

# ==================== 第三方库导入 ====================
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy.exc import IntegrityError

# ==================== 本地模块导入 ====================
from ..core.config_new import settings
from ..core.database_sync import get_db

# ==================== 路由器实例 ====================
router = APIRouter(
    prefix="/demo-sync",
    tags=["示例（同步）"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "资源不存在"},
        status.HTTP_401_UNAUTHORIZED: {"description": "未认证"},
        status.HTTP_403_FORBIDDEN: {"description": "无权限"},
    },
)


# ==================== 权限与用户依赖 ====================
class DemoUser(BaseModel):
    """示例用户对象，实际项目可替换为真实用户模型"""

    username: str
    permissions: set[str]


def get_current_user() -> DemoUser:
    """示例当前用户依赖，默认拥有部分权限"""

    # 实际项目可从 JWT / Session 中解析用户信息
    return DemoUser(username="demo-user", permissions={"items:read", "items:write"})


def require_permission(permission: str):
    """通用权限检查依赖，演示如何在路由层校验权限"""

    def _checker(user: DemoUser = Depends(get_current_user)) -> DemoUser:
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"当前用户缺少权限: {permission}",
            )
        return user

    return _checker


# ==================== SQLModel 模型定义 ====================
class ItemBase(SQLModel):
    """公共字段，便于复用"""

    name: str = Field(max_length=100, description="物品名称")
    description: str | None = Field(default=None, description="物品描述")


class Item(ItemBase, table=True):
    """数据库表模型"""

    id: int | None = Field(default=None, primary_key=True)


class ItemCreate(ItemBase):
    """创建请求体"""

    pass


class ItemUpdate(SQLModel):
    """更新请求体，允许部分字段可选"""

    name: str | None = Field(default=None, description="物品名称")
    description: str | None = Field(default=None, description="物品描述")


class ItemRead(ItemBase):
    """响应模型"""

    id: int


# ==================== 私有工具函数 ====================
def _get_item_or_404(session: Session, item_id: int) -> Item:
    """封装常用查询逻辑，保持路由函数整洁"""

    item = session.get(Item, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID 为 {item_id} 的物品不存在",
        )
    return item


# ==================== 路由函数：CRUD ====================
@router.get(
    "/items",
    response_model=List[ItemRead],
    summary="获取物品列表",
)
def list_items(
    session: Session = Depends(get_db),
    _: DemoUser = Depends(require_permission("items:read")),
):
    """查询所有物品，并演示如何读取配置参数"""

    # 使用 settings 展示读取全局配置
    if settings.debug:
        # 在调试模式下可输出额外日志（这里使用 print，实际项目建议使用 logger）
        print("[DEBUG] 正在列出所有物品")

    results = session.exec(select(Item).order_by(Item.id)).all()
    return results


@router.get(
    "/items/{item_id}",
    response_model=ItemRead,
    summary="获取物品详情",
)
def get_item(
    item_id: int,
    session: Session = Depends(get_db),
    _: DemoUser = Depends(require_permission("items:read")),
):
    """根据 ID 获取单个物品"""

    item = _get_item_or_404(session, item_id)
    return item


@router.post(
    "/items",
    response_model=ItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建物品",
)
def create_item(
    payload: ItemCreate,
    session: Session = Depends(get_db),
    _: DemoUser = Depends(require_permission("items:write")),
):
    """创建新的物品，包含基本异常处理"""

    item = Item.model_validate(payload, update={})
    session.add(item)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建物品失败，数据库约束错误: {exc.args[0]}",
        )
    session.refresh(item)
    return item


@router.put(
    "/items/{item_id}",
    response_model=ItemRead,
    summary="替换更新物品",
)
def update_item(
    item_id: int,
    payload: ItemCreate,
    session: Session = Depends(get_db),
    _: DemoUser = Depends(require_permission("items:write")),
):
    """使用 PUT 进行完整字段替换"""

    item = _get_item_or_404(session, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.patch(
    "/items/{item_id}",
    response_model=ItemRead,
    summary="部分更新物品",
)
def patch_item(
    item_id: int,
    payload: ItemUpdate,
    session: Session = Depends(get_db),
    _: DemoUser = Depends(require_permission("items:write")),
):
    """演示 PATCH 局部更新"""

    item = _get_item_or_404(session, item_id)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除物品",
)
def delete_item(
    item_id: int,
    session: Session = Depends(get_db),
    _: DemoUser = Depends(require_permission("items:write")),
):
    """删除指定物品，返回空响应体"""

    item = _get_item_or_404(session, item_id)
    session.delete(item)
    session.commit()
    return None
