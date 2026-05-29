# PRD：交互式数据分析系统（青少年心理健康数据分类版）

## 1. 背景与目标
- 交付一个可通过 Web 页面操作的数据分析系统，覆盖完整链路：注册/登录 → 上传 → 清洗 → 训练 → 预测 → 可视化 → 导出。
- 对齐实验验收点：基础功能闭环、至少 1 种分析功能、图表可交互、可演示可复现、支持多用户区分数据。

## 2. 数据与分析口径
- 数据集样例：`Teen_Mental_Health_Dataset.csv`
  - 列：13（含 `depression_label` 目标列）
  - 行：1200
  - 缺失：无
  - 类别不平衡：`depression_label=1` 约 2.6%
- 必做分析功能
  - 任务：二分类预测 `depression_label`
  - 模型：`logistic_regression`（必做，`class_weight=balanced`）
  - 对比：`random_forest`
  - 评估：Precision / Recall / F1 / ROC-AUC + 混淆矩阵
  - 输出：预测概率 + 阈值可调（影响最终标签）

## 3. 用户与场景
- 用户：课程小组成员、老师/助教
- 账号机制：每个用户需注册/登录，基于 Token 认证
- 数据隔离：每个用户只能访问自己上传的数据和对应模型
- 典型演示路径
  1. 注册/登录，前端保存 Token 并附带请求头
  2. 上传 CSV，自动预览前 20 行与列类型
  3. 执行清洗，查看清洗摘要
  4. 训练模型并展示指标与混淆矩阵
  5. 调整阈值做单条预测预览
  6. 查看柱状统计、箱线分布、散点相关图
  7. 导出清洗后 CSV

## 4. 功能需求
### 4.1 认证
- 用户注册：用户名 + 密码，成功后返回 Token
- 用户登录：用户名 + 密码，成功后返回 Token
- 用户登出：失效当前 Token
- 当前用户查询：返回登录态信息

### 4.2 数据管理
- 上传 CSV（<10MB），返回 `dataset_id`
- 读取并预览前 N 行、列名、列类型推断
- 所有数据接口必须认证
- 数据只属于当前用户，其他用户不可见

### 4.3 数据清洗
- 缺失值处理：数值中位数、类别众数，或丢弃含缺失行
- 异常值处理：IQR 截断、删除异常行、或不处理
- 类别规范化：trim + lower
- 输出清洗摘要：行数变化、缺失统计、异常值统计

### 4.4 训练与预测
- 训练：逻辑回归（必做）和随机森林（对比）
- 预处理：数值标准化 + 类别 One-Hot
- 划分：随机 80/20，分类任务使用分层抽样
- 指标：Precision / Recall / F1 / ROC-AUC / 混淆矩阵
- 预测：输入若干行样本，返回概率和阈值后的标签

### 4.5 统计可视化
- 柱状统计：分类列计数
- 箱线分布：数值列按分组列展示
- 散点相关：任意两数值列散点，支持按类别分色
- 统计接口只返回图表数据，前端负责渲染

### 4.6 导出
- 导出清洗后 CSV
- 导出操作必须认证，且只能导出当前用户自己的数据

## 5. 接口说明
### 认证接口
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### 数据接口
- `POST /api/datasets/upload`
- `POST /api/datasets/{dataset_id}/clean`
- `POST /api/datasets/{dataset_id}/train`
- `POST /api/model-runs/{model_run_id}/predict`
- `GET /api/datasets/{dataset_id}/stats`
- `GET /api/datasets/{dataset_id}/export`

## 6. 非功能需求
- 文件限制：仅 `.csv`，大小 <10MB
- 存储方式：本地文件系统落盘，数据集和模型运行分目录保存
- 归属字段：`owner_id` / `owner_username`
- 认证方式：DRF Token Authentication
- 前端：Vue 3 + Vite + ECharts，前后端分离开发
- 开发环境：README 需同时提供 macOS/Linux 和 Windows 的启动方式，并包含前端依赖安装失败（`TAR_ENTRY_ERROR`、`EPERM`、`vite` 未找到）的排查步骤，便于组员直接运行

## 7. 验收标准
- 能完成完整闭环：注册/登录 → 上传 → 清洗 → 训练 → 预测 → 可视化 → 导出
- 未登录访问受保护接口返回 401
- 用户 A 无法访问用户 B 的数据/模型，返回 403
- 训练能返回合理指标，支持模型对比
- 导出 CSV 可下载，且内容与当前用户数据一致

## 8. 测试用例
- Happy path：注册 → 登录 → 上传 → 清洗 → 训练 → 预测 → 统计 → 导出
- 认证：重复注册 409、错误密码 401、未登录访问 401
- 隔离：跨用户访问 403
- 边界：非 CSV、空文件、单类标签、列缺失、异常值策略切换

## 9. 小组分工与个人职责

> 本项目按“模块负责人制”拆分，保证每个人都有独立代码范围、独立提交记录和独立展示内容。  
> 建议以 `feature/<name>-<topic>` 分支开发，每个成员围绕自己的模块做持续提交，最终由组长负责联调合并。

### 9.1 前端 A：界面主流程

**负责文件**
- `frontend/src/App.vue`：核心页面，承载所有业务逻辑、状态管理和事件处理
- `frontend/src/api.js`：API 调用封装、Token 注入、导出请求封装
- `frontend/vite.config.js`：前端开发代理与构建配置

**职责范围**
- 实现主流程：`upload → clean → train → viz → export`
- 负责登录/注册面板、Token 保存、权限检查与按钮禁用逻辑
- 负责页面状态流转：上传后进入清洗、清洗后进入训练、训练后进入可视化和导出
- 统一页面交互风格，保证“一个页面完成完整演示”

**学习重点**
- `ref / computed / watch` 的状态流转
- Token 认证流程与请求头注入
- 页面级表单校验、错误提示与按钮状态控制

**验收时要展示的内容**
- 从登录开始完整跑通一遍主流程
- 上传 CSV 后能够进入后续步骤
- 导出按钮可正常下载当前用户数据

### 9.2 前端 B：可视化组件

**负责文件**
- `frontend/src/components/DataPreview.vue`：数据预览表格
- `frontend/src/components/EChart.vue`：ECharts 图表封装
- `frontend/src/style.css`：全局样式、暗色主题与布局
- `frontend/index.html`：前端入口 HTML

**职责范围**
- 实现三类图表：柱状图、箱线图、散点图
- 负责图表 props 传递、图表参数展示与图例布局
- 负责主题样式：深色背景、卡片布局、响应式间距
- 配合前端 A 完成“选图 → 显示对应参数 → 生成图表”的交互

**学习重点**
- 图表三种类型：`count / box / scatter`
- 组件 props 传递：`columns / rows / option`
- CSS 主题和布局统一

**验收时要展示的内容**
- 图表能随参数变化而更新
- 选择不同图表只显示对应参数
- 页面风格统一、简洁、可演示

### 9.3 后端 A：数据管理模块

**负责文件**
- `web/api_views.py`：上半部分上传 / 清洗 / 导出核心 API
- `web/services/cleaning.py`：数据清洗逻辑
- `web/services/csv_io.py`：CSV 读取、预览与列类型推断
- `web/services/storage.py`：文件存储逻辑、目录结构、元数据写入
- `web/services/errors.py`：统一错误处理

**对应接口**
- `dataset_upload()`：文件上传与预览
- `dataset_clean()`：数据清洗
- `dataset_export()`：导出 CSV

**职责范围**
- 负责原始数据的上传、解析、预览和落盘
- 负责清洗规则设计与清洗摘要生成
- 负责导出文件的路径与下载响应
- 负责数据集归属校验，保证不同用户数据互相隔离

**学习重点**
- `CleaningOptions` 清洗配置
- 文件存储结构：`data/datasets/<uuid>/`
- 权限检查：`ensure_dataset_owner()`

**验收时要展示的内容**
- 上传后能看到列名、前几行预览和列类型推断
- 清洗后能返回清洗摘要
- 导出 CSV 能下载且内容正确

### 9.4 后端 B：训练预测模块

**负责文件**
- `web/api_views.py`：下半部分训练 / 预测 / 统计核心 API
- `web/auth_views.py`：认证接口（登录 / 注册 / 登出）
- `web/models.py`：Django 模型预留位置
- `web/urls.py`：URL 路由
- `config/settings.py`：Django 全局配置
- `config/urls.py`：项目根路由

**对应接口**
- `dataset_train()`：模型训练
- `model_predict()`：预测
- `dataset_stats()`：统计图表数据

**职责范围**
- 负责训练分类模型并保存模型文件
- 负责加载已训练模型进行概率预测和阈值二分类
- 负责输出图表统计所需的数据
- 负责认证、Token 认证流程和用户数据隔离

**学习重点**
- Token 认证流程：`IsAuthenticated`
- `scikit-learn` 模型保存/加载：`joblib`
- 用户数据隔离：`owner_id` 验证

**验收时要展示的内容**
- 训练接口能返回指标和混淆矩阵
- 预测接口能按阈值输出标签
- 统计接口能给前端图表提供数据

### 9.5 算法：机器学习核心

**负责文件**
- `web/services/ml.py`：唯一核心算法文件

**学习重点（全部函数）**

| 行号 | 函数/类 | 作用 |
|---|---|---|
| 25–29 | `TrainOptions` | 训练配置（目标列 / 测试比例 / 随机种子） |
| 39–56 | `build_logreg_pipeline()` | 逻辑回归管道（标准化 + 编码 + 模型） |
| 59–76 | `build_rf_pipeline()` | 随机森林管道 |
| 79–128 | `train_classifier()` | 核心训练流程 |
| 143–148 | `predict_proba()` | 输出预测概率 |

**模型细节**
- 逻辑回归：`StandardScaler + OneHotEncoder + LogisticRegression`
- 随机森林：`OneHotEncoder + RandomForestClassifier`
- 评估指标：`precision / recall / f1 / roc_auc / confusion_matrix`

**职责范围**
- 负责分类任务的特征工程、训练和评估
- 负责处理类别不平衡问题
- 负责训练后模型的保存、预测概率输出和阈值转换
- 负责模型对比与后续加分功能扩展

**验收时要展示的内容**
- 解释为何选择逻辑回归作为必做模型
- 讲清训练流程、评估指标和预测阈值
- 能说明随机森林作为对比模型的用途

### 9.6 分工建议：5 人版与 6 人版

**5 人版**
- 前端 A：界面主流程
- 前端 B：可视化组件
- 后端 A：数据管理模块
- 后端 B：训练预测模块
- 算法：机器学习核心

**6 人版**
- 前端 A：界面主流程
- 前端 B：可视化组件
- 后端 A：数据管理模块
- 后端 B：训练预测模块
- 算法：机器学习核心
- 文档 / 测试：验收文档、测试用例、演示脚本、问题回归

### 9.7 提交与协作原则
- 每个成员至少保留自己的功能分支与提交历史
- 提交信息建议使用 `feat:`、`fix:`、`docs:`、`refactor:` 等规范前缀
- 合并优先保留提交记录，不建议使用 squash merge
- 每个模块都应能独立演示，避免“所有内容都堆在一个提交里”
