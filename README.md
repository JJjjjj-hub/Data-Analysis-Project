# 交互式数据分析系统（分类版）

后端：Django + DRF（API）  
前端：Vue 3 + Vite（步骤式向导）+ ECharts  
流程：上传 → 清洗 → 分析（分类）→ 可视化 → 导出

## 运行（后端）

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

打开（后端）：

- API（根路径会跳转前端）：`http://127.0.0.1:8000/`
- 管理后台：`http://127.0.0.1:8000/admin/`

## 运行（前端）

```bash
cd frontend
npm install
npm run dev
```

打开（前端）：`http://127.0.0.1:5173/`

## API（核心）

- 认证
  - `POST /api/auth/register`（json：`username`/`password`）
  - `POST /api/auth/login`（json：`username`/`password`）
  - `POST /api/auth/logout`（需要 `Authorization: Token ...`）
  - `GET /api/auth/me`（需要 `Authorization: Token ...`）
- `POST /api/datasets/upload`（multipart: `file`，可选 `target_col`）
- `POST /api/datasets/{dataset_id}/clean`（json：缺失值/异常值/类别规范化选项）
- `POST /api/datasets/{dataset_id}/train`（json：`model=logistic_regression|random_forest` 等）
- `POST /api/model-runs/{model_run_id}/predict`（json：`rows` + 可选 `threshold`）
- `GET /api/datasets/{dataset_id}/stats`（query：`kind=count_by|box_by|scatter`）
- `GET /api/datasets/{dataset_id}/export`（下载CSV）

提示：`/api/*` 除认证接口外都需要先登录（前端会保存 Token 并自动附带请求头）。

## 目录结构

- `config/`：项目配置（settings / urls）
- `web/`：后端应用（模板页 + API）
- `templates/`：项目模板
- `static/`：静态资源
- `frontend/`：Vue 前端工程
