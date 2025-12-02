"""Demo 模型：示例用 SQLModel 数据表"""
from sqlmodel import SQLModel, Field

class DemoItem(SQLModel, table=True):
    """示例物品表"""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, description="名称")
    description: str | None = Field(default=None, description="描述")
