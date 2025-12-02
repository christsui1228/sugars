"""Demo CRUD（异步版本）"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .models import DemoItem
from .schemas import DemoItemCreate, DemoItemUpdate


async def get_items(db: AsyncSession) -> list[DemoItem]:
    result = await db.execute(select(DemoItem).order_by(DemoItem.id))
    return result.scalars().all()


async def get_item(db: AsyncSession, item_id: int) -> DemoItem | None:
    return await db.get(DemoItem, item_id)


async def create_item(db: AsyncSession, payload: DemoItemCreate) -> DemoItem:
    item = DemoItem.model_validate(payload, update={})
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_item(db: AsyncSession, item_id: int, payload: DemoItemCreate | DemoItemUpdate) -> DemoItem:
    item = await get_item(db, item_id)
    if item is None:
        raise ValueError("物品不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(item, k, v)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item_id: int) -> None:
    item = await get_item(db, item_id)
    if item is None:
        raise ValueError("物品不存在")
    await db.delete(item)
    await db.commit()
