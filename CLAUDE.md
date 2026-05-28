# 项目上下文

## 基本信息
- **项目名称**: 交互式数据分析系统（青少年心理健康数据分类版）
- **团队规模**: 5人小组开发
- **当前分支**: `codex-auth-login`

## 技术栈
- **后端**: Django + Django REST Framework (DRF)
- **前端**: Vue 3 + Vite + ECharts
- **认证**: DRF TokenAuthentication
- **数据库**: SQLite（用户/认证数据）
- **文件存储**: 本地文件系统（CSV/模型文件）

## 数据存储架构
1. **账户数据**: Django User 模型 + DRF Token 模型（SQLite）
2. **数据集/模型文件**: 存储在 `data/datasets/` 和 `data/model_runs/`，按 UUID 分目录
3. **元数据**: `meta.json` 文件记录 owner_id、owner_username 等

## 当前进度
- [x] 基础项目结构
- [x] 数据上传、清洗、分析、可视化、导出功能
- [x] 登录/注册/认证功能（刚完成，未合并）

## 待讨论事项
- 是否将生成的数据（CSV、模型）迁移到数据库（如 PostgreSQL）
- 推荐方案：混合架构——元数据存数据库，文件存文件系统

## 验收要求
- 链路闭环：上传 → 清洗 → 分析 → 可视化 → 导出
- 二分类预测 `depression_label`，使用逻辑回归
- 数据隔离：用户只能访问自己的数据

## 关键文件
- `web/auth_views.py`: 认证接口
- `web/services/storage.py`: 数据存储逻辑
- `frontend/src/api.js`: API 客户端（含 Token 拦截器）
- `frontend/src/App.vue`: 前端主界面（含登录 UI）
