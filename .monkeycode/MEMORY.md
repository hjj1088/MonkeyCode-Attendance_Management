# 用户指令记忆

本文件记录了用户的指令、偏好和教导，用于在未来的交互中提供参考。

## 格式

### 用户指令条目
用户指令条目应遵循以下格式：

[用户指令摘要]
- Date: [YYYY-MM-DD]
- Context: [提及的场景或时间]
- Instructions:
  - [用户教导或指示的内容，逐行描述]

### 项目知识条目
Agent 在任务执行过程中发现的条目应遵循以下格式：

[项目知识摘要]
- Date: [YYYY-MM-DD]
- Context: Agent 在执行 [具体任务描述] 时发现
- Category: [运维部署|构建方法|测试方法|排错调试|工作流协作|环境配置]
- Instructions:
  - [具体的知识点，逐行描述]

## 去重策略
- 添加新条目前，检查是否存在相似或相同的指令
- 若发现重复，跳过新条目或与已有条目合并
- 合并时，更新上下文或日期信息
- 这有助于避免冗余条目，保持记忆文件整洁

## 条目

[账号恢复信息]
- Date: 2026-08-15
- Context: 用户反馈强制改密后未记住新密码导致账号被锁
- Category: 排错调试
- Instructions:
  - 修改管理员密码、生成临时凭证或重置账号状态后，必须在下一条回复的开头用醒目标记（如加粗 + 独立段落）明示新账号与密码，防止用户找不到登录凭据

[考勤系统后端排障要点]
- Date: 2026-08-15
- Context: Agent 在执行 V3.2 D3 补测试时发现
- Category: 排错调试
- Instructions:
  - server.py `json_serialize` 会对 settings.value 等 JSON 字段自动反序列化，前端取到的 value 是对象而非字符串；测试 mock 与断言需按对象形态处理
  - `INSERT OR IGNORE` 遇到 NOT NULL 约束冲突会被静默忽略（rowcount 0 但不报错），导入/迁移类写入前必须把 None 转成 '' 或 0，否则出现"报告导入成功但实际零落库"
  - V3.2 考勤计算逻辑在前端 `client/src/shared/rules.js`（esbuild bundle 后可在 Node 中跑），后端 `/api/attendance/calculate` 仅负责存储结果；测试用 mock fetch 驱动
  - 后端 store 路由有表名映射（`punch`→`punch_records` 等），API 测试传物理表名或短表名均可
  - 种子用户密码为 `test123`（非 admin123）；管理员初始密码 `admin123`，登录返回 `need_change_password` 触发强制改密
  - 测试基础设施：`tests/conftest.py` 提供 `e2e_server` fixture（独立 DB + 独立端口，模块级），新测试模块设置 `TEST_PORT` 避免端口冲突
