# 文件路径: ~/coding/sugars/sugars/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# 导入路由模块
from .routers import market


# --- 1. 定义 Lifespan (生命周期) ---
# yield 之前是启动逻辑 (Startup)
# yield 之后是关闭逻辑 (Shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # [Startup] 启动时执行
    logger.info("🚀 Sugar Nexus API is starting up...")
    logger.info("✅ Database schema is managed by Alembic.")

    yield  # 应用程序在此处运行

    # [Shutdown] 关闭时执行
    logger.info("👋 Sugar Nexus API is shutting down...")


# --- 2. 实例化 App (注入 lifespan) ---
app = FastAPI(
    title="Sugar Nexus API",
    description="糖业分析数据中台 MVP (Powered by AkShare & Polars)",
    version="1.0.0",
    lifespan=lifespan,  # ✅ 这里挂载 lifespan
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


# --- 5. 健康检查 ---
@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "project": "Sugar Nexus",
        "version": "1.0.0",
        "docs_url": "/docs",
    }
