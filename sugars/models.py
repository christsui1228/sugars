# backend/models.py
from sqlmodel import SQLModel, Field
from datetime import date, datetime


# --- 1. 基础模型 (Base Schema) ---
# 定义数据结构和字段属性
class MarketDailyBase(SQLModel):
    # 核心数据点
    sugar_close: float = Field(description="郑糖收盘价")
    sugar_open: float | None = Field(default=None, description="郑糖开盘价")

    usd_cny_rate: float = Field(description="美元兑人民币汇率")
    bdi_index: float | None = Field(default=None, description="波罗的海干散货指数")

    # 衍生计算字段
    import_cost_estimate: float | None = Field(
        default=None, description="估算进口成本 (人民币/吨)"
    )

    # 元数据
    updated_at: datetime = Field(
        default_factory=datetime.now, description="最后更新时间"
    )


# --- 2. 数据库表模型 (Table Model) ---
# 继承 Base，并添加 table=True 和主键
class MarketDaily(MarketDailyBase, table=True):
    __tablename__ = "market_daily"

    # 将 record_date 定义为唯一主键
    record_date: date = Field(primary_key=True, index=True, description="交易日期")


# --- 3. API 响应模型 (Read Schema) ---
# 用于 GET 请求的响应，确保数据输出格式正确
class MarketDailyRead(MarketDailyBase):
    record_date: date
    # 在 Read 模型中可以添加 API 特有字段或排除敏感字段，这里我们直接继承并使用
    pass
