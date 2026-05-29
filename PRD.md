# PRD：交互式数据分析系统（通用数据分类版）

## 1. 项目概述

### 1.1 项目名称
交互式数据分析系统（通用二分类版）

### 1.2 项目目标
交付一个可通过 Web 页面操作的通用数据分析系统，支持任意 CSV 数据的二分类任务，覆盖完整链路：注册/登录 → 上传 → 清洗 → 训练 → 预测 → 可视化 → 导出。

### 1.3 团队构成（5人）
- 前端 A：界面主流程
- 前端 B：可视化组件
- 后端 A：数据管理模块
- 后端 B：训练预测模块
- 算法工程师：机器学习核心

---

## 2. 技术栈

| 层级 | 技术 | 版本 |
|-----|------|-----|
| 后端框架 | Django + Django REST Framework | 4.2+ / 3.15+ |
| 前端框架 | Vue 3 + Vite | 3.x |
| 可视化 | ECharts | 5.x |
| 认证 | DRF Token Authentication | - |
| 数据库 | SQLite（用户/认证数据） | - |
| 文件存储 | 本地文件系统 | - |
| 算法库 | scikit-learn / pandas / numpy | 1.5+ / 2.2+ |

---

## 3. 核心功能

### 3.1 数据支持
- **格式**：仅 CSV 文件
- **大小**：单文件 < 10MB
- **目标列**：系统自动检测二分类列（值仅为 0/1 的列）
- **列类型推断**：
  - `binary`：二分类列（0/1），适合作为目标列
  - `numeric`：数值列（连续数值）
  - `categorical`：类别列（文本/离散值）

### 3.2 功能模块

#### 3.2.1 认证模块
- 用户注册（用户名 + 密码）
- 用户登录（返回 Token）
- 用户登出（失效 Token）
- 当前用户查询

#### 3.2.2 数据管理
- 上传 CSV → 返回 dataset_id
- 预览前 20 行数据
- 自动推断列类型（binary/numeric/categorical）
- 数据隔离：用户只能访问自己的数据

#### 3.2.3 数据清洗
- 缺失值处理：
  - `auto`：数值列用中位数填充，类别列用众数填充
  - `drop_rows`：删除包含缺失值的行
- 异常值处理（排除目标列）：
  - `none`：不处理
  - `iqr_clip`：IQR 截断（将异常值限制在合理范围）
  - `iqr_drop_rows`：删除异常值所在行
- 类别规范化：trim + lower

#### 3.2.4 模型训练
- **支持模型**：
  - 逻辑回归（必做，class_weight=balanced）
  - 随机森林（对比）
- **目标列选择**：下拉框仅显示二分类列
- **预处理**：
  - 数值列：StandardScaler 标准化
  - 类别列：One-Hot 编码
- **数据划分**：随机 80/20，分层抽样
- **评估指标**：Precision / Recall / F1 / ROC-AUC / 混淆矩阵

#### 3.2.5 预测
- 输入：若干行样本（自动剔除目标列）
- 输出：概率值 + 阈值分类结果
- 阈值可调（默认 0.5）

#### 3.2.6 可视化
- 柱状统计（count_by）
- 饼状图（pie）
- 箱线分布（box_by）
- 散点相关（scatter）

#### 3.2.7 导出
- 导出清洗后 CSV
- 仅允许导出当前用户自己的数据

---

## 4. 数据存储架构

```
data/
├── datasets/
│   └── <dataset_id>/
│       ├── data.csv          # 原始/清洗后数据
│       ├── meta.json         # 元数据（owner_id, created_at等）
│       └── schema.json       # 列信息（列名、类型、预览行数）
└── model_runs/
    └── <model_run_id>/
        ├── model.joblib      # 训练好的模型
        └── meta.json         # 元数据（metrics, owner_id等）
```

- **账户数据**：Django User 模型 + DRF Token 模型（SQLite）
- **数据隔离**：通过 `owner_id` 和 `owner_username` 字段实现

---

## 5. 接口规范

### 5.1 认证接口
| 方法 | 路径 | 说明 |
|-----|------|-----|
| POST | `/api/auth/register` | 注册（username, password） |
| POST | `/api/auth/login` | 登录（username, password） |
| POST | `/api/auth/logout` | 登出（需 Token） |
| GET | `/api/auth/me` | 获取当前用户（需 Token） |

### 5.2 数据接口（均需 Token）
| 方法 | 路径 | 说明 |
|-----|------|-----|
| POST | `/api/datasets/upload` | 上传 CSV（multipart: file） |
| POST | `/api/datasets/{id}/clean` | 清洗数据（target_col, missing_strategy, outlier_strategy, normalize_categories） |
| POST | `/api/datasets/{id}/train` | 训练模型（target_col, model, test_size, random_state） |
| POST | `/api/model-runs/{id}/predict` | 预测（rows, threshold） |
| GET | `/api/datasets/{id}/stats` | 统计图表（kind, col等） |
| GET | `/api/datasets/{id}/export` | 导出 CSV |

---

## 6. 小组分工与个人职责

### 6.1 前端 A：界面主流程（1人）

**负责文件**（精确到行范围）：
- `frontend/src/App.vue`（第 1-400 行）：
  - 全局状态管理（ref/computed/watch）
  - 事件处理函数（onUpload, onClean, onTrain, onPredictSample）
  - 登录面板、Token 管理
  - 页面状态流转逻辑
- `frontend/src/api.js`：API 调用封装、Token 注入拦截器
- `frontend/vite.config.js`：开发代理配置

**核心功能**：
- 5 步流程界面（上传 → 清洗 → 训练 → 可视化 → 导出）
- 目标列下拉框只显示二分类列（使用 binaryColumns computed）
- 预测结果卡片展示（总样本、阳性/阴性、概率统计）
- Token 认证与权限控制

**验收标准**：
- 从登录到导出完整流程能跑通
- 错误提示友好（如"请先选择目标列"）
- 响应式布局正常

---

### 6.2 前端 B：可视化组件（1人）

**负责文件**（精确到行范围）：
- `frontend/src/App.vue`（第 400-760 行）：
  - 图表类型切换逻辑（count/box/scatter/pie）
  - 图表参数选择界面
  - loadCountBy / loadBoxBy / loadScatter / loadPie 函数
- `frontend/src/components/DataPreview.vue`：数据预览表格
- `frontend/src/components/EChart.vue`：ECharts 图表封装组件
- `frontend/src/style.css`：全局样式、预测结果卡片样式

**核心功能**：
- 4 种图表类型渲染
- 散点图 X/Y 轴自动排除重复列（scatterYOptions）
- 图表参数联动（选择 X 轴后 Y 轴自动切换）
- 预测结果可视化卡片样式

**验收标准**：
- 4 种图表都能正常显示
- 图表随参数变化实时更新
- 风格统一（Apple Design 风格）

---

### 6.3 后端 A：数据管理模块（1人）

**负责文件**（精确到函数）：
- `web/api_views.py`：
  - `dataset_upload()`（第 64-113 行）：上传与预览
  - `dataset_clean()`（第 116-171 行）：数据清洗
  - `dataset_export()`（第 258-270 行）：导出 CSV
- `web/services/cleaning.py`：
  - `clean_dataframe()`：清洗逻辑
  - `CleaningOptions`：清洗配置
- `web/services/csv_io.py`：
  - `read_csv_flexible()`：多编码 CSV 读取
  - `infer_column_kinds()`：列类型推断（binary/numeric/categorical）
  - `_is_binary_column()`：二分类检测（值仅为 0/1）
- `web/services/storage.py`：
  - `create_raw_dataset()` / `create_cleaned_dataset()`：数据集创建
  - `dataset_csv_path()` / `dataset_meta()`：文件路径管理
- `web/services/errors.py`：`UserFacingError` 异常定义

**核心功能**：
- 上传时自动推断列类型（新增 binary 类型检测）
- 清洗时排除目标列（避免异常值处理影响目标列）
- 数据隔离（owner_id 校验）

**验收标准**：
- 上传后能正确识别二分类列
- 清洗后目标列不丢失
- 导出文件内容正确

---

### 6.4 后端 B：训练预测模块（1人）

**负责文件**（精确到函数）：
- `web/api_views.py`：
  - `dataset_train()`（第 174-219 行）：模型训练
  - `model_predict()`（第 222-256 行）：预测
  - `dataset_stats()`（第 273-343 行）：统计图表数据
- `web/auth_views.py`：
  - `register()` / `login()` / `logout()` / `me()`：认证接口
- `web/urls.py`：URL 路由配置
- `config/settings.py`：Django 全局配置
- `config/urls.py`：项目根路由

**核心功能**：
- 训练接口校验（目标列必须存在且为二分类）
- Token 认证流程（IsAuthenticated 权限）
- 统计接口（count_by / box_by / scatter）
- 用户数据隔离（403 权限控制）

**验收标准**：
- 未选择目标列时返回 400 错误
- 跨用户访问返回 403 错误
- 统计接口返回正确数据格式

---

### 6.5 算法工程师：机器学习核心（1人）

**负责文件**（精确到函数/类）：
- `web/services/ml.py`（共 150 行）：
  - `TrainOptions`（第 25-30 行）：训练配置数据类
  - `build_logreg_pipeline()`（第 39-56 行）：逻辑回归管道
  - `build_rf_pipeline()`（第 59-76 行）：随机森林管道
  - `train_classifier()`（第 79-130 行）：核心训练流程
  - `predict_proba()`（第 145-150 行）：预测概率
  - `_as_int_labels()`：标签转换为 0/1 整数
  - `_label_counts()`：统计标签分布
  - `_safe_auc()`：安全计算 ROC-AUC

**模型细节**：
- **逻辑回归**：`StandardScaler + OneHotEncoder + LogisticRegression(class_weight='balanced')`
- **随机森林**：`OneHotEncoder + RandomForestClassifier(class_weight='balanced_subsample')`
- **评估指标**：precision / recall / f1 / roc_auc / confusion_matrix
- **特征工程**：自动识别数值/类别列，分别预处理

**核心功能**：
- 二分类任务训练与评估
- 处理类别不平衡（class_weight='balanced'）
- 训练后模型保存（joblib）
- 预测概率输出

**验收标准**：
- 能解释逻辑回归为何适合做必做模型
- 讲清训练流程、评估指标含义
- 能说明随机森林作为对比的优势
- 不同数据集都能正常训练

---

## 7. 代码文件责任矩阵

| 文件路径 | 负责角色 | 行数范围 | 核心内容 |
|---------|---------|---------|---------|
| `frontend/src/App.vue` | 前端 A + B | 1-400 / 400-760 | 状态管理+事件 / 图表逻辑 |
| `frontend/src/api.js` | 前端 A | 全部 | API 封装、Token 拦截 |
| `frontend/src/components/DataPreview.vue` | 前端 B | 全部 | 数据预览表格 |
| `frontend/src/components/EChart.vue` | 前端 B | 全部 | ECharts 封装 |
| `frontend/src/style.css` | 前端 B | 全部 | 样式、预测卡片 |
| `web/api_views.py` | 后端 A + B | 64-171 / 174-343 | 上传清洗 / 训练预测 |
| `web/auth_views.py` | 后端 B | 全部 | 认证接口 |
| `web/services/cleaning.py` | 后端 A | 全部 | 清洗逻辑 |
| `web/services/csv_io.py` | 后端 A | 全部 | CSV 读取、类型推断 |
| `web/services/storage.py` | 后端 A | 全部 | 文件存储 |
| `web/services/ml.py` | 算法 | 全部 | 模型训练核心 |
| `web/services/errors.py` | 后端 A | 全部 | 异常定义 |

---

## 8. 验收标准

### 8.1 功能验收
- [ ] 完整闭环：注册 → 登录 → 上传 → 清洗 → 训练 → 预测 → 可视化 → 导出
- [ ] 认证：重复注册 409、错误密码 401、未登录访问 401
- [ ] 隔离：跨用户访问 403
- [ ] 目标列检测：只有二分类列（0/1）显示在下拉框
- [ ] 清洗保护：异常值处理不影响目标列
- [ ] 模型对比：逻辑回归 vs 随机森林指标对比

### 8.2 演示验收
- [ ] 能使用任意 CSV 文件（不限于 Teen_Mental_Health_Dataset）
- [ ] 预测结果可视化展示（非 raw JSON）
- [ ] 4 种图表都能正常渲染

---

## 9. 提交与协作规范

### 9.1 分支命名
```
feature/<name>-<topic>
```
例如：`feature/zhangsan-login-ui`、`feature/lisi-cleaning`

### 9.2 提交信息规范
```
feat: 新增功能ix: 修复 bug
docs: 文档更新
refactor: 重构代码
```

### 9.3 提交流程
1. 本地开发测试通过
2. `git add` 相关文件
3. `git commit -m "feat: xxx"`
4. 通知组长审核
5. 组长合并到 main 分支

---

*文档版本：v2.0*  
*最后更新：2026-05-29*  
*适用团队：5人小组开发*
