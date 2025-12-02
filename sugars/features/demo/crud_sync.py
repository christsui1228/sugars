"""Demo CRUD（同步版本）"""
from sqlalchemy.orm import Session
from sqlmodel import select

from .models import DemoItem
from .schemas import DemoItemCreate, DemoItemUpdate


def get_items(db: Session) -> list[DemoItem]:
    return db.exec(select(DemoItem).order_by(DemoItem.id)).all()


def get_item(db: Session, item_id: int) -> DemoItem | None:
    return db.get(DemoItem, item_id)


def create_item(db: Session, payload: DemoItemCreate) -> DemoItem:
    item = DemoItem.model_validate(payload, update={})
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item_id: int, payload: DemoItemCreate | DemoItemUpdate) -> DemoItem:
    item = get_item(db, item_id)
    if item is None:
        raise ValueError("物品不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(item, k, v)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item_id: int) -> None:
    item = get_item(db, item_id)
    if item is None:
        raise ValueError("物品不存在")
    db.delete(item)
    db.commit()
