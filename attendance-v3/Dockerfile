# MonkeyCode 考勤管理系统 V3.2 - Docker 镜像
# 多阶段构建：Stage 1 用 Node 构建 Vite 前端，Stage 2 用 Python 运行后端并托管前端产物
# 镜像端口：8001（与 server.py PORT 一致），数据目录 /app/server/data（建议挂载 volume）

# ---------- Stage 1: build frontend ----------
FROM node:20-alpine AS frontend

WORKDIR /build

COPY client/package.json client/package-lock.json ./

# 国内网络可将构建时 registry 切换为 npmmirror：
#   docker build --build-arg NPM_REGISTRY=https://registry.npmmirror.com .
ARG NPM_REGISTRY=https://registry.npmjs.org
RUN npm config set registry ${NPM_REGISTRY} && npm ci

COPY client/ .
RUN npm run build

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} -r requirements.txt

COPY server/ server/
COPY --from=frontend /build/dist client/dist

RUN mkdir -p /app/server/data

EXPOSE 8001

VOLUME /app/server/data

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/', timeout=3)"

CMD ["python3", "server/server.py"]
