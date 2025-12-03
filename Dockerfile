# 1. Base Image
FROM crpi-s1v7k92yzt12ry6y.cn-hangzhou.personal.cr.aliyuncs.com/christsui1228/python:3.12.11-slim-bookworm as base

# 2. Env Vars
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# 阿里云镜像源配置
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_DEFAULT_TIMEOUT=100
# ⚠️ 关键：确保 Python 能找到 /app 下的 sugars 包
ENV PYTHONPATH=/app

WORKDIR /app

# 3. Install PDM
# hadolint ignore=DL3013
RUN pip install --no-cache-dir pdm

# 4. 依赖缓存层 (先只复制依赖定义)
COPY pyproject.toml pdm.lock ./

# 配置 PDM 使用阿里云源
RUN pdm config pypi.url https://mirrors.aliyun.com/pypi/simple/

# 5. 安装依赖
# ⚠️ 修正：去掉了 --no-lock，确保使用 lock 文件，保证环境一致性
RUN pdm install --prod --no-editable

# 6. 复制剩余代码
# ⚠️ 建议：改回 COPY . .，因为 .dockerignore 已经过滤了垃圾
# 这样你在这个目录下的 scripts 或其他配置文件也能被拷进去
COPY . .

# 7. Metadata
EXPOSE 8000

# 8. Start Command (已确认修正)
CMD ["pdm", "run", "uvicorn", "sugars.main:app", "--host", "0.0.0.0", "--port", "8000"]
