# V3.2 部署指南

本指南覆盖 V3.2（`attendance-v3/`，Vite + Vue 3 SPA + SQLite 后端）的完整部署流程，包括 Docker 镜像部署（推荐）与源码部署两种方式。

## 部署方式总览

| 方式 | 适用场景 | 难度 |
|------|----------|------|
| Docker 镜像 | 服务器/本地一键部署，环境隔离，升级方便 | 低 |
| 源码部署 | 二次开发、无 Docker 环境 | 中 |

Docker 容器只暴露 **8001**（API + `client/dist` 静态托管）。8002 仅本地 Vite 热更新，不进入镜像。

## 一、Docker 部署

### 1. 获取镜像

镜像由 GitHub Actions 自动构建并发布到 **GitHub Container Registry (GHCR)**。镜像地址（`<owner>` 为 `hjj1088`）：

```
ghcr.io/hjj1088/monkeycode-attendance_management-v3:latest
```

> Gitee 不提供容器镜像仓库服务，因此 Gitee 用户有两种选择：
> 1. 从 Gitee 仓库下载源码后在本地自行构建镜像（见下文"源码构建镜像"）；
> 2. 将镜像转发/推送至 Docker Hub、阿里云 ACR 等任意 Docker Registry 后拉取（见下文"镜像分发"）。

拉取镜像（国内网络访问 GHCR 较慢时，可先配置镜像加速器或使用 GHCR 代理，见"常见问题"）：

```bash
docker pull ghcr.io/hjj1088/monkeycode-attendance_management-v3:latest
```

镜像 tag 说明：

| Tag | 内容 |
|-----|------|
| `latest` | 最新稳定版（默认分支构建） |
| `v3.2.0` 等 | 与 git tag 对应的版本 |
| `main` | 默认分支最新提交 |
| `<sha>` | 具体提交构建 |

### 2. 使用 docker run 启动

```bash
docker run -d \
  --name attendance-v3 \
  -p 8001:8001 \
  -e PYTHONUNBUFFERED=1 \
  -e JWT_SECRET=<CHANGE_ME> \
  -v ./attendance-data:/app/server/data \
  --restart unless-stopped \
  ghcr.io/hjj1088/monkeycode-attendance_management-v3:latest
```

- `-p 8001:8001`：暴露 Web 端口（宿主端口可改，如 `-p 8080:8001`）
- `-e JWT_SECRET=<CHANGE_ME>`：生产环境必须设置；未设置时后端使用内置默认值
- `-v ./attendance-data:/app/server/data`：将 SQLite 数据文件持久化到宿主机目录（**必须挂载**，否则容器删除后数据丢失）
- `--restart unless-stopped`：宕机/重启后自动拉起

启动后访问 `http://localhost:8001`，初始账号 `admin` / `admin123`（角色 superadmin，首次登录强制改密）。

### 3. 使用 docker compose 启动（推荐）

`attendance-v3/` 目录已提供 `docker-compose.yml`：

```bash
cd attendance-v3
docker compose up -d --build
docker compose logs -f
docker compose down
```

- 首次或源码有改动：`docker compose up -d --build`（本地重建前端 dist + 后端镜像）
- 已有镜像、仅重启：`docker compose up -d`
- 从 GHCR 拉最新：`docker compose pull && docker compose up -d`

数据保存在 `attendance-v3/data/`（映射容器内 `/app/server/data`）。

可选环境变量（写在 `attendance-v3/.env` 或命令前缀）：

| 变量 | 默认 | 说明 |
|------|------|------|
| `HOST_PORT` | `8001` | 宿主端口 |
| `NPM_REGISTRY` | `https://registry.npmjs.org` | 构建前端时的 npm 源 |
| `PIP_INDEX_URL` | `https://pypi.org/simple` | 构建后端时的 PyPI 源 |

国内构建示例：

```bash
NPM_REGISTRY=https://registry.npmmirror.com \
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
docker compose up -d --build
```

生产环境在 `docker-compose.yml` 的 `environment` 增加 `JWT_SECRET: ${JWT_SECRET}`，并在同目录 `.env` 写入 `JWT_SECRET=<CHANGE_ME>`。未注入时容器沿用 `middleware.py` 的 `os.environ.get` 回退值。

### 4. 源码构建镜像

```bash
cd attendance-v3
docker build -t attendance-v3:latest .

# 国内网络构建时切换 npm / pip 源
docker build -t attendance-v3:latest \
  --build-arg NPM_REGISTRY=https://registry.npmmirror.com \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple .
```

镜像内已包含 Vite 生产产物（`client/dist`）。容器启动后只跑 `python3 server/server.py`，监听 `0.0.0.0:8001`。

### 5. 镜像分发（可选）

GHCR 在国内访问不稳定时，可将镜像推送到国内可访问的 Registry（如 Docker Hub、阿里云 ACR）：

```bash
# 以 Docker Hub 为例
docker tag ghcr.io/hjj1088/monkeycode-attendance_management-v3:latest \
  <你的DockerHub用户名>/attendance-v3:latest
docker login
docker push <你的DockerHub用户名>/attendance-v3:latest

# 以阿里云 ACR 个人版为例
docker tag ghcr.io/hjj1088/monkeycode-attendance_management-v3:latest \
  registry.cn-hangzhou.aliyuncs.com/<命名空间>/attendance-v3:latest
docker login registry.cn-hangzhou.aliyuncs.com
docker push registry.cn-hangzhou.aliyuncs.com/<命名空间>/attendance-v3:latest
```

### 6. 数据备份与升级

- **备份**：SQLite 单文件数据库，停服后直接拷贝 `data/attendance.db` 即可；或直接拷贝挂载目录
- **升级（源码重建）**：拉取最新代码后在 `attendance-v3/` 执行 `docker compose up -d --build`，数据目录保持不变
- **升级（GHCR 镜像）**：
  ```bash
  docker compose pull && docker compose up -d
  ```
- **V2.0 数据迁移**：旧版数据为浏览器 IndexedDB，登录系统后在设置页使用"数据库迁移"功能（`/api/migrate`）将 JSON 数据导入 SQLite
- 启动时 `database.py` 的 `_migrate` / `_ensure_columns` 会给已有库补列，挂载旧 `attendance.db` 可直接升级 schema

## 二、源码部署

### 环境要求

| 依赖 | 版本 |
|------|------|
| Python | 3.9+（Docker 运行时为 3.12） |
| Node.js | 18+（仅构建前端需要；Docker 构建阶段为 Node 20） |

### 步骤

```bash
# 1. 安装后端依赖
cd attendance-v3
pip install -r requirements.txt

# 2. 构建前端（生产模式，产物在 client/dist）
cd client
npm ci
npm run build
cd ..

# 3. 启动服务（端口 8001）
python3 server/server.py
```

访问 `http://localhost:8001`。

开发模式（前后端分离热更新）：

```bash
# 终端 1：后端（8001）
cd attendance-v3
python3 server/server.py

# 终端 2：前端 dev server（8002，/api 自动代理到 8001）
cd attendance-v3/client
npm ci
npm run dev
# 访问 http://localhost:8002
```

## 三、初始账号与测试数据

| 账号 | 密码 | 角色 | 说明 |
|------|------|------|------|
| `admin` | `admin123` | superadmin | 系统管理员，首次登录强制改密 |

调用 `POST /api/system/seed-test-data`（需 admin 登录）生成测试数据：技术部/销售部/行政部各 5 名员工 + 部门管理员 `dept_*`（角色 deptadmin），密码统一 `test123`。

## 四、端口与配置

| 项 | 值 |
|----|----|
| 服务端口 | 8001（`server/server.py` 中硬编码，Docker 通过 `HOST_PORT` 或 `-p` 调整宿主端口） |
| SQLite 数据文件 | `server/data/attendance.db`（Docker 中挂载 `/app/server/data`） |
| JWT 有效期 | 24 小时 |
| JWT 密钥 | 环境变量 `JWT_SECRET` |
| 登录失败锁定 | 连续 5 次失败锁定 24 小时；距上次失败超 1 天清零计数 |
| 健康检查 | Dockerfile `HEALTHCHECK` 请求 `http://127.0.0.1:8001/` |

## 五、常见问题

**Q1: 国内拉取 GHCR 镜像很慢/失败怎么办？**

- 使用 GHCR 加速代理：如 `ghcr.nju.edu.cn` 等公共镜像代理，把 `ghcr.io` 前缀替换后拉取再重新 tag；
- 或源码目录执行 `docker compose up -d --build` 本地构建；
- 或先在有条件的环境拉取镜像，push 到阿里云 ACR / Docker Hub 后从国内拉取。

**Q2: 端口 8001 被占用？**

```bash
HOST_PORT=8080 docker compose up -d
```

或 `docker run` 改用 `-p 8080:8001`。

**Q3: 重启容器后数据丢失？**

检查是否挂载了数据卷（`-v ./xxx:/app/server/data` 或 compose 的 `./data`）。未挂载时数据存于容器内层，容器删除即丢失。

**Q4: 修改管理员密码后忘记？**

停掉服务，删除/初始化数据目录中的 `attendance.db` 后重启，系统会重新创建 `admin/admin123` 初始账号（注意会清空全部业务数据）。业务数据有备份时可保留数据库文件、改用 `handle_users_reset_password` 相关 API 重置。

**Q5: 构建镜像时 npm / pip 安装超时？**

```bash
NPM_REGISTRY=https://registry.npmmirror.com \
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
docker compose up -d --build
```

**Q6: 页面仍是旧前端？**

镜像内托管的是构建时的 `client/dist`。源码改 Vue/CSS 后必须 `--build` 重建，仅 `docker compose up -d` 不会刷新前端。

**Q7: `docker pull ... denied`？**

GHCR 包默认 `Private`。匿名 `pull` 会被拒绝。两种处理：

1. 仓库维护者把包改成 Public：GitHub → Packages → `monkeycode-attendance_management-v3` → Package settings → Change visibility → Public。之后任何人可直接 `docker pull`。
2. 保持私有时先登录再拉：

```bash
echo <GITHUB_PAT> | docker login ghcr.io -u hjj1088 --password-stdin
docker pull ghcr.io/hjj1088/monkeycode-attendance_management-v3:latest
```

PAT 需 `read:packages`。无权限或不想登录时，在源码目录本地构建：`cd attendance-v3 && docker compose up -d --build`。

## 相关文件

| 文件 | 说明 |
|------|------|
| `attendance-v3/Dockerfile` | 多阶段 Dockerfile（Node 20 构建前端 → Python 3.12 运行时 + HEALTHCHECK） |
| `attendance-v3/docker-compose.yml` | 一键编排（数据卷、`HOST_PORT`、构建参数） |
| `attendance-v3/.dockerignore` | 构建上下文精简（排除 dist、data、tests、预览页） |
| `.github/workflows/docker-publish.yml` | GitHub Actions：自动构建并推送 V2.0 / V3.2 镜像到 GHCR |
