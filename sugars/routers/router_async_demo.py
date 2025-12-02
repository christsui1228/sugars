"""FastAPI 路由异步示例（参考模板）

本文件演示一个符合最佳实践的异步路由模块结构，涵盖：
1. 异步 APIRouter 配置与依赖注入
2. SQLModel + AsyncSession CRUD 模板
3. 权限校验、异常处理、日志记录
4. 中英文不混用，注释全部中文

开发者可据此模板快速搭建新的异步路由模块。
"""

from __future__ import annotations

# ==================== 标准库导入 ====================
from typing import List

# ==================== 第三方库导入 ====================
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, Field, select

# ==================== 本地模块导入 ====================
from ..core.database_async import get_db
from ..core.config_new import settings

# ==================== 路由器实例 ====================
router = APIRouter(
    prefix="/demo-async",
    tags=["示例（异步）"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "资源不存在"},
        status.HTTP_401_UNAUTHORIZED: {"description": "未认证"},
        status.HTTP_403_FORBIDDEN: {"description": "无权限"},
    },
)


# ==================== 权限相关依赖 ====================
class AsyncDemoUser(SQLModel):
    """示例用户模型，实际项目可替换为真实用户结构"""

    username: str
    permissions: list[str]


def get_current_user_async() -> AsyncDemoUser:
    """示例当前用户依赖，返回拥有基础权限的用户"""

    # 此处直接返回静态用户，实际场景应解析 JWT 或调用用户服务
    return AsyncDemoUser(username="async-demo", permissions=["tasks:read", "tasks:write"])


def require_permission_async(permission: str):
    """异步权限检查依赖，可扩展为调用权限服务或数据库"""

    async def _checker(user: AsyncDemoUser = Depends(get_current_user_async)) -> AsyncDemoUser:
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"当前用户缺少权限: {permission}",
            )
        return user

    return _checker


# ==================== SQLModel 模型定义 ====================
class TaskBase(SQLModel):
    """异步任务的公共字段"""

    title: str = Field(max_length=120, description="任务标题")
    is_completed: bool = Field(default=False, description="任务完成状态")


class Task(TaskBase, table=True):
    """数据库表模型"""

    id: int | None = Field(default=None, primary_key=True)


class TaskCreate(TaskBase):
    """创建请求体"""

    pass


class TaskUpdate(SQLModel):
    """更新请求体"""

    title: str | None = Field(default=None, description="任务标题")
    is_completed: bool | None = Field(default=None, description="任务完成状态")


class TaskRead(TaskBase):
    """响应模型"""

    id: int


# ==================== 工具函数 ====================
async def _get_task_or_404(session: AsyncSession, task_id: int) -> Task:
    """复用查询逻辑，保持路由函数简洁"""

    result = await session.get(Task, task_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID 为 {task_id} 的任务不存在",
        )
    return result


# ==================== 路由函数：CRUD ====================
@router.get(
    "/tasks",
    response_model=List[TaskRead],
    summary="获取任务列表",
)
async def list_tasks(
    session: AsyncSession = Depends(get_db),
    _: AsyncDemoUser = Depends(require_permission_async("tasks:read")),
):
    """异步查询任务列表，演示 select + async session 用法"""

    query = select(Task).order_by(Task.id)
    result = await session.execute(query)
    tasks = result.scalars().all()

    if settings.debug:
        logger.debug("[DEBUG] 读取任务数量: %s", len(tasks))

    return tasks


@router.get(
    "/tasks/{task_id}",
    response_model=TaskRead,
    summary="获取任务详情",
)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
    _: AsyncDemoUser = Depends(require_permission_async("tasks:read")),
):
    """根据 ID 获取单个任务"""

    task = await _get_task_or_404(session, task_id)
    return task


@router.post(
    "/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建任务",
)
async def create_task(
    payload: TaskCreate,
    session: AsyncSession = Depends(get_db),
    _: AsyncDemoUser = Depends(require_permission_async("tasks:write")),
):
    """创建新任务，包含 IntegrityError 处理"""

    new_task = Task.model_validate(payload, update={})
    session.add(new_task)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        logger.error("创建任务失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="创建任务失败，数据库约束错误",
        )
    await session.refresh(new_task)
    return new_task


@router.put(
    "/tasks/{task_id}",
    response_model=TaskRead,
    summary="替换更新任务",
)
async def update_task(
    task_id: int,
    payload: TaskCreate,
    session: AsyncSession = Depends(get_db),
    _: AsyncDemoUser = Depends(require_permission_async("tasks:write")),
):
    """使用 PUT 进行全量替换更新"""

    task = await _get_task_or_404(session, task_id)
    for key, value in payload.model_dump().items():
        setattr(task, key, value)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.patch(
    "/tasks/{task_id}",
    response_model=TaskRead,
    summary="部分更新任务",
)
async def patch_task(
    task_id: int,
    payload: TaskUpdate,
    session: AsyncSession = Depends(get_db),
    _: AsyncDemoUser = Depends(require_permission_async("tasks:write")),
):
    """示例 PATCH 部分更新"""

    task = await _get_task_or_404(session, task_id)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除任务",
)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
    _: AsyncDemoUser = Depends(require_permission_async("tasks:write")),
):
    """删除指定任务并返回空响应"""

    task = await _get_task_or_404(session, task_id)
    await session.delete(task)
    await session.commit()
    return None
