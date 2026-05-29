# 交互式数据分析系统（通用二分类版）

后端：Django + DRF + Token Auth  
前端：Vue 3 + Vite + ECharts  
算法：scikit-learn（逻辑回归 + 随机森林）  

**系统流程**：注册/登录 → 上传 CSV → 数据清洗 → 模型训练 → 预测 → 可视化 → 导出

**核心特性**：
- 支持任意 CSV 数据的二分类任务
- 自动检测二分类目标列（0/1）
- 数据清洗时自动保护目标列
- 支持逻辑回归与随机森林模型对比

---

## 快速启动

### Windows 一键启动（推荐）

在项目根目录双击或运行：

```powershell
# 同时启动后端和前端
start-all.bat

# 或只启动后端
start-backend.bat

# 或只启动前端
start-frontend.bat
```

**说明**：
- 第一次运行会自动创建 `.venv` 并安装后端依赖
- 第一次前端会自动安装 `node_modules`
- 如果 PowerShell 执行策略拦截，先执行：
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
  ```

---

## 手动启动

### 后端启动

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

#### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py manage.py migrate
py manage.py runserver
```

#### Windows CMD

```bat
py -3 -m venv .venv
.\.venv\Scripts\activate.bat
pip install -r requirements.txt
py manage.py migrate
py manage.py runserver
```

**访问地址**：
- API 根路径：`http://127.0.0.1:8000/`
- 管理后台：`http://127.0.0.1:8000/admin/`

---

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

**访问地址**：`http://localhost:5173/`

---

## 系统功能详解

### 1. 认证模块

| 功能 | 说明 |
|-----|------|
| 注册/登录 | 用户名 + 密码，返回 Token |
| 数据隔离 | 基于 `owner_id` 字段，用户只能访问自己的数据 |
| Token 持久化 | 前端 localStorage 保存，自动附带请求头 |

### 2. 数据上传

- **格式**：CSV 文件（< 10MB）
- **列类型自动推断**：
  - `binary`：二分类列（值仅为 0/1），适合作为目标列
  - `numeric`：数值列
  - `categorical`：类别列

### 3. 数据清洗

| 配置项 | 选项 | 说明 |
|-------|------|-----|
| 缺失值策略 | `auto` | 数值列用中位数填充，类别列用众数填充 |
| | `drop_rows` | 删除包含缺失值的行 |
| 异常值策略 | `none` | 不处理 |
| | `iqr_clip` | IQR 截断（将异常值限制在合理范围） |
| | `iqr_drop_rows` | 删除异常值所在行 |
| 类别规范化 | `true` | trim + lower |

**重要**：清洗时自动排除目标列，避免异常值处理影响目标列分布。

### 4. 模型训练

**目标列选择**：
- 下拉框仅显示二分类列（binary 类型）
- 如果没有二分类列，显示红色提示

**支持模型**：
- 逻辑回归（必做，`class_weight='balanced'`）
- 随机森林（对比）

**评估指标**：
- Precision（精确率）
- Recall（召回率）
- F1 Score
- ROC-AUC
- 混淆矩阵

### 5. 预测

- 自动使用当前数据预览的 20 行作为样本
- 输出：概率值 + 阈值分类结果
- 阈值可调（默认 0.5）
- 可视化展示：总样本、阳性/阴性数量、平均概率、最高/最低概率

### 6. 可视化

| 图表类型 | 用途 |
|---------|------|
| 柱状统计 | 分类列计数统计 |
| 饼状图 | 分类列占比展示 |
| 箱线分布 | 数值列按分组列展示分布 |
| 散点相关 | 两数值列相关性，支持按类别分色 |

### 7. 导出

- 导出当前用户清洗后的数据集
- 格式：CSV

---

## API 文档

### 认证接口

```http
POST /api/auth/register      # 注册 {username, password}
POST /api/auth/login         # 登录 {username, password}
POST /api/auth/logout        # 登出（需 Token）
GET  /api/auth/me            # 获取当前用户（需 Token）
```

### 数据接口（均需 Token）

```http
# 上传 CSV
POST /api/datasets/upload
Content-Type: multipart/form-data
file: <CSV文件>

# 清洗数据
POST /api/datasets/{dataset_id}/clean
{
  "target_col": "depression_label",
  "missing_strategy": "auto",      // auto | drop_rows
  "outlier_strategy": "none",      // none | iqr_clip | iqr_drop_rows
  "normalize_categories": true
}

# 训练模型
POST /api/datasets/{dataset_id}/train
{
  "target_col": "depression_label",
  "model": "logistic_regression",  // logistic_regression | random_forest
  "test_size": 0.2,
  "random_state": 42
}

# 预测
POST /api/model-runs/{model_run_id}/predict
{
  "rows": [...],
  "threshold": 0.5
}

# 统计图表
GET /api/datasets/{dataset_id}/stats?kind=count_by&col=gender
GET /api/datasets/{dataset_id}/stats?kind=box_by&value_col=age&group_col=gender
GET /api/datasets/{dataset_id}/stats?kind=scatter&x_col=age&y_col=sleep_hours

# 导出 CSV
GET /api/datasets/{dataset_id}/export
```

---

## 目录结构

```
project/
├── config/                 # Django 配置
│   ├── settings.py        # 全局设置
│   └── urls.py            # 根路由
├── web/                    # 后端应用
│   ├── api_views.py       # API 视图（上传/清洗/训练/预测/统计）
│   ├── auth_views.py      # 认证视图（注册/登录/登出）
│   ├── urls.py            # URL 路由
│   └── services/          # 业务逻辑
│       ├── cleaning.py    # 数据清洗
│       ├── csv_io.py      # CSV 读取、列类型推断
│       ├── ml.py          # 机器学习核心
│       ├── storage.py     # 文件存储
│       └── errors.py      # 异常定义
├── frontend/               # Vue 前端
│   ├── src/
│   │   ├── App.vue        # 主页面
│   │   ├── api.js         # API 封装
│   │   ├── components/    # 组件
│   │   │   ├── DataPreview.vue
│   │   │   └── EChart.vue
│   │   └── style.css      # 全局样式
│   └── package.json
├── data/                   # 运行时数据
│   ├── datasets/          # 数据集目录
│   └── model_runs/        # 模型目录
├── start-all.bat          # Windows 一键启动
├── start-backend.bat
├── start-frontend.bat
└── requirements.txt       # Python 依赖
```

---

## 小组分工

### 5人团队分工

| 角色 | 负责人数 | 核心文件 | 主要职责 |
|-----|---------|---------|---------|
| 前端 A - 界面主流程 | 1 | `App.vue`(1-400行), `api.js` | 状态管理、事件处理、Token认证 |
| 前端 B - 可视化组件 | 1 | `App.vue`(400-760行), `components/`, `style.css` | 图表渲染、预测卡片样式 |
| 后端 A - 数据管理 | 1 | `api_views.py`(上传/清洗/导出), `services/cleaning.py`, `services/csv_io.py`, `services/storage.py` | 上传、清洗、类型推断、存储 |
| 后端 B - 训练预测 | 1 | `api_views.py`(训练/预测/统计), `auth_views.py`, `urls.py` | 训练、预测、认证、权限 |
| 算法 - 机器学习 | 1 | `services/ml.py` | 模型训练、评估、预测 |

---

## 常见问题

### Windows 问题

**PowerShell 执行策略拦截**
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**npm install 报错 `TAR_ENTRY_ERROR`、`EPERM`**
```powershell
rmdir /s /q node_modules
$env:npm_config_cache = ".npm-cache"
npm install --no-audit --no-fund --cache ".npm-cache"
npm run dev
```

**后端只输出 numpy 警告但不启动**
- 删除 `.venv`，用 `py -3` 重新创建虚拟环境
- 如果装了 Conda，先退出 `(base)` 环境

**前端页面能打开但接口失败**
- 确认后端在 `http://127.0.0.1:8000/` 正常运行

### 数据问题

**上传后提示"未检测到二分类列"**
- 目标列必须是 0/1 的数值列
- 检查 CSV 中该列是否有其他值（如 2, 3, NA 等）

**训练报错"目标列只有一个类别"**
- 清洗时选择了 `iqr_drop_rows` 导致删除了少数类
- 建议异常值策略选择 `none`

**清洗后目标列丢失**
- 可能是编码问题，确保 CSV 是 UTF-8 编码

---

## 技术细节

### 列类型推断逻辑

```python
binary:     值仅为 0/1 的数值列（可作为目标列）
numeric:    其他数值列（年龄、分数等）
categorical: 文本列（性别、地区等）
```

### 模型对比

| 特性 | 逻辑回归 | 随机森林 |
|-----|---------|---------|
| 可解释性 | 高（系数表示特征重要性） | 中 |
| 训练速度 | 快 | 较慢 |
| 特征处理 | 需要标准化 | 不需要标准化 |
| 非线性 | 不支持 | 支持 |
| 适用场景 | 线性可分数据 | 复杂非线性数据 |

---

## 许可证

课程项目，仅供学习交流使用。

---

*最后更新：2026-05-29*  
*版本：v2.0*
