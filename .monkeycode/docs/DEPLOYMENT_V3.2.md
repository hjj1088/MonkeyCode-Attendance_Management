# V3.2 部署指南

本指南覆盖 V3.2（`attendance-v3/`，Vite + Vue 3 SPA + SQLite 后端）的完整部署流程，包括 Docker 镜像部署（推荐）与源码部署两种方式。

## 部署方式总览

| 方式 | 适用场景 | 难度 |
|------|----------|------|
| Docker 镜像 | 服务器/本地一键部署，环境隔离，升级方便 | 低 |
| 源码部署 | 二次开发、无 Docker 环境 | 中 |

## 一、Docker 部署

### 1. 获取镜像

镜像由 GitHub Actions 自动构建并发布到 **GitHub Container Registry (GHCR)**。镜像地址（`<owner>` 为 `hjj1088`）：

```
ghcr.io/hjj1088/MonkeyCode-Attendance_Management-v3:latest
```

> Gitee 不提供容器镜像仓库服务，因此 Gitee 用户有两种选择：
> 1. 从 Gitee 仓库下载源码后在本地自行构建镜像（见下文"源码构建镜像"）；
> 2. 将镜像转发/推送至 Docker Hub、阿里云 ACR 等任意 Docker Registry 后拉取（见下文"镜像分发"）。

拉取镜像（国内网络访问 GHCR 较慢时，可先配置镜像加速器或使用 GHCR 代理，见"常见问题"）：

```bash
docker pull ghcr.io/hjj1088/MonkeyCode-Attendance_Management-v3:latest
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
  -v ./attendance-data:/app/server/data \
  --restart unless-stopped \
  ghcr.io/hjj1088/MonkeyCode-Attendance_Management-v3:latest
```

- `-p 8001:8001`：暴露 Web 端口（宿主端口可改，如 `-p 8080:8001`）
- `-v ./attendance-data:/app/server/data`：将 SQLite 数据文件持久化到宿主机目录（**必须挂载**，否则容器删除后数据丢失）
- `--restart unless-stopped`：宕机/重启后自动拉起

启动后访问 `http://localhost:8001`，初始账号 `admin` / `admin123`（角色 superadmin，首次登录强制改密）。

### 3. 使用 docker compose 启动（推荐）

`attendance-v3/` 目录已提供 `docker-compose.yml`：

```bash
cd attendance-v3
docker compose up -d --build   # 首次或修改后带 --build 构建
docker compose up -d           # 之后只需启动
docker compose logs -f         # 查看日志
docker compose down            # 停止
```

数据保存在 `attendance-v3/data/` 目录。

### 4. 源码构建镜像

```bash
cd attendance-v3
docker build -t attendance-v3:latest .

# 国内网络构建时切换 npm 镜像源加速前端依赖下载
docker build -t attendance-v3:latest --build-arg NPM_REGISTRY=https://registry.npmmirror.com .
```

### 5. 镜像分发（可选）

GHCR 在国内访问不稳定时，可将镜像推送到国内可访问的 Registry（如 Docker Hub、阿里云 ACR）：

```bash
# 以 Docker Hub 为例
docker tag ghcr.io/hjj1088/MonkeyCode-Attendance_Management-v3:latest \
  <你的DockerHub用户名>/attendance-v3:latest
docker login
docker push <你的DockerHub用户名>/attendance-v3:latest

# 以阿里云 ACR 个人版为例
docker tag ghcr.io/hjj1088/MonkeyCode-Attendance_Management-v3:latest \
  registry.cn-hangzhou.aliyuncs.com/<命名空间>/attendance-v3:latest
docker login registry.cn-hangzhou.aliyuncs.com
docker push registry.cn-hangzhou.aliyuncs.com/<命名空间>/attendance-v3:latest
```

### 6. 数据备份与升级

- **备份**：SQLite 单文件数据库，停服后直接拷贝 `data/attendance.db` 即可；或直接拷贝挂载目录
- **升级**：拉取新镜像后重启容器，数据目录保持不变即完成升级：
  ```bash
  docker compose pull && docker compose up -d
  ```
- **V2.0 数据迁移**：旧版数据为浏览器 IndexedDB，登录系统后在设置页使用"数据库迁移"功能（`/api/migrate`）将 JSON 数据导入 SQLite

## 二、源码部署

### 环境要求

| 依赖 | 版本 |
|------|------|
| Python | 3.9+ |
| Node.js | 18+（仅构建前端需要） |

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
| 服务端口 | 8001（`server/server.py` 中硬编码，Docker 通过宿主端口映射调整） |
| SQLite 数据文件 | `server/data/attendance.db`（Docker 中挂载 `/app/server/data`） |
| JWT 有效期 | 24 小时 |
| 登录失败锁定 | 连续 5 次失败锁定 24 小时；距上次失败超 1 天清零计数 |

## 五、常见问题

**Q1: 国内拉取 GHCR 镜像很慢/失败怎么办？**

- 使用 GHCR 加速代理：如 `ghcr.nju.edu.cn` 等公共镜像代理，把 `ghcr.io` 前缀替换后拉取再重新 tag；
- 或先在有条件的环境拉取镜像，push 到阿里云 ACR / Docker Hub 后从国内拉取。

**Q2: 端口 8001 被占用？**

docker run 改用其他宿主端口，如 `-p 8080:8001`；compose 修改 `ports` 即可。

**Q3: 重启容器后数据丢失？**

检查是否挂载了数据卷（`-v ./xxx:/app/server/data`）。未挂载时数据存于容器内层，容器删除即丢失。

**Q4: 修改管理员密码后忘记？**

停掉服务，删除/初始化数据目录中的 `attendance.db` 后重启，系统会重新创建 `admin/admin123` 初始账号（注意会清空全部业务数据）。业务数据有备份时可保留数据库文件、改用 `handle_users_reset_password` 相关 API 重置。

**Q5: 构建镜像时 npm 安装超时？**

使用 `--build-arg NPM_REGISTRY=https://registry.npmmirror.com` 切换国内 npm 镜像源。

## 相关文件

| 文件 | 说明 |
|------|------|
| `attendance-v3/Dockerfile` | 多阶段 Dockerfile（Node 构建前端 → Python 运行时） |
| `attendance-v3/docker-compose.yml` | 一键编排（含数据卷持久化） |
| `attendance-v3/.dockerignore` | 构建上下文精简 |
| `.github/workflows/docker-publish.yml` | GitHub Actions：自动构建并推送 V2.0 / V3.2 镜像到 GHCR |
