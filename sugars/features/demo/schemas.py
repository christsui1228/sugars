"""Demo schemas：请求 / 响应 Pydantic 模型"""
from sqlmodel import SQLModel, Field

class DemoItemBase(SQLModel):
    name: str = Field(max_length=100, description="名称")
    description: str | None = Field(default=None, description="描述")

class DemoItemCreate(DemoItemBase):
    pass

class DemoItemUpdate(SQLModel):
    name: str | None = Field(default=None)
    description: str | None = Field(default=None)

class DemoItemRead(DemoItemBase):
    id: int
