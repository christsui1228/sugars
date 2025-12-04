# 文件路径: ~/coding/sugars/sugars/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# 导入路由模块
from .routers import market
from .events import start_scheduler, stop_scheduler
from .events.routers import router as etl_router


# --- 1. 定义 Lifespan (生命周期) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # [Startup] 启动时执行
    logger.info("🚀 Sugar Nexus API is starting up...")
    logger.info("✅ Database schema is managed by Alembic.")

    # 启动定时任务
    start_scheduler()

    yield  # 应用程序在此处运行

    # [Shutdown] 关闭时执行
    stop_scheduler()
    logger.info("👋 Sugar Nexus API is shutting down...")


# --- 2. 实例化 App (注入 lifespan) ---
app = FastAPI(
    title="Sugar Nexus API",
    description="糖业分析数据中台 MVP (Powered by AkShare & Polars)",
    version="1.0.0",
    lifespan=lifespan,
)

# --- 3. 核心配置：CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4. 注册路由 ---
app.include_router(market.router, prefix="/api")
app.include_router(etl_router, prefix="/api")


# --- 5. 健康检查 ---
@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "project": "Sugar Nexus",
        "version": "1.0.0",
        "docs_url": "/docs",
    }
