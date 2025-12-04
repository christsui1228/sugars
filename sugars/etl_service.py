import akshare as ak
import polars as pl
from datetime import date, timedelta, datetime
from sqlmodel import Session, select
from .core.database_sync import engine
from .models import MarketDaily


def fetch_and_store_data():
    """
    核心 ETL 函数：抓取 -> 清洗 -> 入库
    """
    print(f"🚀 [ETL Start] 开始执行数据抓取任务 - {datetime.now()}")

    # --- 1. 获取数据源 (Extract) ---
    try:
        # A. 白糖期货 (郑商所 SR0)
        print("   -> 正在抓取白糖期货 (SR0)...")
        df_sugar_raw = ak.futures_zh_daily_sina(symbol="SR0")

        # B. 汇率 (使用中国银行安全接口)
        print("   -> 正在抓取美元/人民币汇率...")
        try:
            df_fx_raw = ak.currency_boc_safe()
            # 只保留日期和美元列，重命名为标准格式
            df_fx_raw = df_fx_raw[["日期", "美元"]].copy()
            df_fx_raw.columns = ["日期", "中行汇买价"]
            # 汇率需要除以 100（707.89 -> 7.0789）
            df_fx_raw["中行汇买价"] = df_fx_raw["中行汇买价"] / 100
        except Exception as e:
            # 降级策略：使用固定汇率
            print(f"      ⚠️ 汇率接口失败 ({e})，使用固定汇率 7.0")
            current_rate = 7.0
            dates = [date.today() - timedelta(days=i) for i in range(60)]
            df_fx_raw = pl.DataFrame(
                {"日期": dates, "中行汇买价": [current_rate] * 60}
            ).to_pandas()

        # C. 航运指数 (BDI)
        print("   -> 正在抓取波罗的海干散货指数 (BDI)...")
        df_bdi_raw = ak.spot_goods(symbol="波罗的海干散货指数")

    except Exception as e:
        error_msg = f"❌ 数据源抓取失败: {e}"
        print(error_msg)
        return {"status": "error", "detail": str(e)}

    # --- 2. 数据清洗 (Transform with Polars) ---
    print("   -> 正在使用 Polars 清洗数据...")
    try:
        # A. 清洗白糖（只保留最近2年数据）
        q_sugar = (
            pl.from_pandas(df_sugar_raw)
            .with_columns(pl.col("date").cast(pl.Date))
            .filter(pl.col("date") >= (date.today() - timedelta(days=730)))
            .select(
                [
                    pl.col("date").alias("record_date"),
                    pl.col("close").cast(pl.Float64).alias("sugar_close"),
                    pl.col("open").cast(pl.Float64).alias("sugar_open"),
                ]
            )
        )

        # B. 清洗汇率 (处理列名变动风险)
        # 自动识别列名，防止 'date' 或 '日期' 混淆
        fx_cols = df_fx_raw.columns.tolist()
        rate_col = "中行汇买价" if "中行汇买价" in fx_cols else fx_cols[1]
        date_col = "日期" if "日期" in fx_cols else "date"

        q_fx = (
            pl.from_pandas(df_fx_raw)
            .with_columns(pl.col(date_col).cast(pl.Date).alias("record_date"))
            .select(
                [
                    pl.col("record_date"),
                    pl.col(rate_col).cast(pl.Float64).alias("usd_cny_rate"),
                ]
            )
            # 中行数据通常是 725.5 (每百美元)，需要除以 100 变成 7.255
            .with_columns(
                pl.when(pl.col("usd_cny_rate") > 50)
                .then(pl.col("usd_cny_rate") / 100)
                .otherwise(pl.col("usd_cny_rate"))
                .round(4)
                .alias("usd_cny_rate")
            )
        )

        # C. 清洗 BDI
        q_bdi = (
            pl.from_pandas(df_bdi_raw)
            .with_columns(pl.col("日期").cast(pl.Date).alias("record_date"))
            .select(
                [
                    pl.col("record_date"),
                    pl.col("指数").cast(pl.Float64).alias("bdi_index"),
                ]
            )
        )

        # D. 核心合并 (Join) & 计算
        # 以白糖交易日为主表 (Left Join) - 只保留白糖有数据的日期
        df_final = (
            q_sugar.join(q_fx, on="record_date", how="left")
            .join(q_bdi, on="record_date", how="left")
            .sort("record_date")
            # 填充空值 (Forward Fill: 周末汇率/BDI 不更新，沿用最近的交易日数据)
            .with_columns(
                [
                    pl.col("usd_cny_rate").forward_fill(),
                    pl.col("bdi_index").forward_fill(),
                ]
            )
            # 不再过滤日期范围，保留所有白糖有数据的交易日
        )

        # E. 计算估算进口成本
        # 公式假设：(ICE原糖22美分 * 汇率 * 22.0462 * 1.5关税) + 运费估算
        # 注意：这里 BDI/10 + 200 只是一个非常粗略的运费拟合，仅供演示
        df_final = df_final.with_columns(
            (
                pl.lit(22) * pl.col("usd_cny_rate") * pl.lit(22.0462) * pl.lit(1.5)
                + (pl.col("bdi_index") / 10 + 200)
            )
            .round(2)
            .alias("import_cost_estimate")
        ).drop_nulls()  # 丢弃还补不全数据的行

    except Exception as e:
        print(f"❌ Polars 处理失败: {e}")
        return {"status": "error", "detail": str(e)}

    # --- 3. 入库 (Load to Postgres) ---
    records = df_final.to_dicts()
    print(f"   -> 准备写入 {len(records)} 条记录到数据库...")

    from sqlalchemy.dialects.postgresql import insert
    
    with Session(engine) as session:
        # 批量 UPSERT（PostgreSQL ON CONFLICT）
        stmt = insert(MarketDaily.__table__).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['record_date'],
            set_={
                'sugar_close': stmt.excluded.sugar_close,
                'sugar_open': stmt.excluded.sugar_open,
                'usd_cny_rate': stmt.excluded.usd_cny_rate,
                'bdi_index': stmt.excluded.bdi_index,
                'import_cost_estimate': stmt.excluded.import_cost_estimate,
                'updated_at': datetime.now()
            }
        )
        result = session.execute(stmt)
        session.commit()

    print(f"🎉 ETL 完成! 处理 {len(records)} 条记录")
    return {"status": "success", "records": len(records)}


if __name__ == "__main__":
    # 允许直接运行此脚本进行测试
    fetch_and_store_data()
