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

        # B. 汇率 (为了 MVP 稳定，获取最近历史数据)
        print("   -> 正在抓取美元/人民币汇率...")
        # 注意：这里我们取最近 60 天，确保能覆盖到白糖的交易日
        start_date_str = (date.today() - timedelta(days=60)).strftime("%Y%m%d")
        try:
            # 尝试获取中行历史数据
            df_fx_raw = ak.currency_boc_sina(
                symbol="美元",
                start_date=start_date_str,
                end_date=date.today().strftime("%Y%m%d"),
            )
        except Exception as e:
            # 降级策略：使用固定汇率
            print(f"      ⚠️ 汇率接口失败，使用固定汇率 7.0")
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
        # A. 清洗白糖
        q_sugar = (
            pl.from_pandas(df_sugar_raw)
            .with_columns(pl.col("date").cast(pl.Date))
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
        # 以白糖交易日为主表 (Left Join)
        df_final = (
            q_sugar.join(q_fx, on="record_date", how="left")
            .join(q_bdi, on="record_date", how="left")
            .sort("record_date")
            # 填充空值 (Forward Fill: 周末汇率/BDI 不更新，沿用周五的)
            .with_columns(
                [
                    pl.col("usd_cny_rate").forward_fill(),
                    pl.col("bdi_index").forward_fill(),
                ]
            )
            # 只取最近 365 天的数据入库
            .filter(pl.col("record_date") >= (date.today() - timedelta(days=365)))
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

    with Session(engine) as session:
        count_new = 0
        count_update = 0
        for row in records:
            # 检查当日数据是否存在 (Upsert 逻辑)
            existing = session.get(MarketDaily, row["record_date"])
            if existing:
                # 更新
                existing.sugar_close = row["sugar_close"]
                existing.sugar_open = row["sugar_open"]
                existing.usd_cny_rate = row["usd_cny_rate"]
                existing.bdi_index = row["bdi_index"]
                existing.import_cost_estimate = row["import_cost_estimate"]
                existing.updated_at = datetime.now()
                session.add(existing)
                count_update += 1
            else:
                # 插入
                session.add(MarketDaily(**row))
                count_new += 1
        session.commit()

    print(f"🎉 ETL 完成! 新增: {count_new}, 更新: {count_update}")
    return {"status": "success", "new": count_new, "updated": count_update}


if __name__ == "__main__":
    # 允许直接运行此脚本进行测试
    fetch_and_store_data()
