# 交互式数据分析系统（分类版）

后端：Django + DRF + Token Auth  
前端：Vue 3 + Vite + ECharts  
流程：注册/登录 → 上传 → 清洗 → 训练 → 预测 → 可视化 → 导出

## 运行（后端）

### macOS / Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py manage.py migrate
py manage.py runserver
```

### Windows CMD

```bat
py -3 -m venv .venv
.\.venv\Scripts\activate.bat
pip install -r requirements.txt
py manage.py migrate
py manage.py runserver
```

打开（后端）：

- API（根路径会跳转前端）：`http://127.0.0.1:8000/`
- 管理后台：`http://127.0.0.1:8000/admin/`

## 运行（前端）

### macOS / Linux / Windows

```bash
cd frontend
npm install
npm run dev
```

打开（前端）：`http://127.0.0.1:5173/`

如果 Windows 上 PowerShell 运行脚本被拦截，可以先执行一次：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

如果你们组员用的是 Git Bash，也可以把上面的 `activate.ps1` 换成：

```bash
source .venv/Scripts/activate
```

如果 `npm install` 报错 `TAR_ENTRY_ERROR`、`EPERM`，或者启动时提示 `vite 不是内部或外部命令`，通常是前端依赖目录损坏或 npm 缓存目录权限问题。请按下面顺序处理：

```powershell
rmdir /s /q node_modules
npm config set cache "%LOCALAPPDATA%\npm-cache" --global
npm install --no-audit --no-fund
npm run dev
```

如果还是失败，先确认当前目录是 `frontend`，并且 `package.json` 和 `node_modules` 没被杀毒软件/编辑器占用。

## Windows 一键启动

如果组员想最省事，可以直接在项目根目录双击或运行下面任意一个脚本：

- `start-all.bat`：同时启动后端和前端
- `start-backend.bat`：只启动后端
- `start-frontend.bat`：只启动前端

对应的 PowerShell 脚本也在根目录里：

- `start-all.ps1`
- `start-backend.ps1`
- `start-frontend.ps1`

说明：
- 第一次运行会自动创建 `.venv` 并安装后端依赖
- 第一次运行前端会自动安装 `node_modules`
- 如果 PowerShell 执行策略拦截脚本，先执行：
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
  ```

## 核心功能

- 多账户登录：`register / login / logout / me`
- 数据上传：仅支持 CSV，单文件限制 10MB
- 数据清洗：缺失值处理、异常值处理、类别规范化
- 训练分析：逻辑回归（必做）+ 随机森林（对比）
- 预测：输出概率和阈值二分类结果
- 可视化：柱状统计、箱线分布、散点相关
- 导出：下载当前用户的数据集 CSV

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
- `web/services/`：清洗、训练、存储等业务实现
- `templates/`：项目模板
- `static/`：静态资源
- `frontend/`：Vue 前端工程
- `data/`：运行时数据落盘目录（上传原始文件、清洗结果、模型元数据）

## 现在的数据存储方式

- 原始/清洗后的 CSV 存在 `data/datasets/<dataset_id>/`
- 模型文件存在 `data/model_runs/<model_run_id>/model.joblib`
- 数据归属和运行指标写在对应目录的 `meta.json`
- 账号信息由 Django 自带 `auth` 和 `authtoken` 维护，数据通过 `owner_id` 隔离

## 小组协作

- 当前仓库使用分支开发，建议每人新建 `feature/<name>-<topic>` 分支
- 合并时尽量保留提交记录，避免使用 squash merge

## Windows 常见问题

- `python3` 不存在时，用 `py -3`
- `. .venv/bin/activate` 是 macOS / Linux 写法，Windows 要用 `Scripts` 目录
- 如果前端页面能打开但接口失败，先确认后端在 `http://127.0.0.1:8000/` 正常运行
- 如果 `npm install` 过程中出现 `TAR_ENTRY_ERROR`、`EPERM`，先删除 `frontend/node_modules`，再把 npm cache 改到 `%LOCALAPPDATA%\npm-cache`
- 如果 `vite` 提示不是内部命令，先确认前一步 `npm install` 是否成功，再执行 `npm run dev`
- 如果组员已经装过 Python / Node，但命令找不到，先重开终端再试
