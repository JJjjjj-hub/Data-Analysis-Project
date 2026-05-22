# PRD：交互式数据分析系统（青少年心理健康数据分类版）

## 1. 背景与目标
- 交付可通过 Web 页面操作的数据分析系统，覆盖完整链路：上传 → 清洗 → 分析（分类）→ 可视化 → 导出
- 对齐验收要点：链路闭环、至少 1 种分析功能、图表可交互、可演示可复现

## 2. 数据与分析口径
- 数据集样例：`Teen_Mental_Health_Dataset.csv`
  - 列：13（含 `depression_label` 目标列）
  - 行：1200
  - 缺失：无
  - 类别不平衡：`depression_label=1` 约 2.6%
- 分析功能（必做）
  - 任务：二分类预测 `depression_label`
  - 模型：`logistic_regression`（必做，`class_weight=balanced`）
  - 评估：Precision / Recall / F1 / ROC-AUC + 混淆矩阵
  - 输出：预测概率 + 阈值可调（影响预测标签分布）
- 加分项（可选）
  - 多算法对比：增加 `random_forest` 并对比指标

## 3. 用户与使用场景
- 用户：课程小组成员（开发/演示/写个人文档）、老师/助教（验收）
- 典型演示路径
  1) 上传样例 CSV → 自动预览前 20 行与列类型
  2) 执行清洗（缺失值策略、异常值 IQR、类别规范化）
  3) 训练模型并展示指标与混淆矩阵
  4) 可视化（≥3）：柱状统计、箱线分布、散点相关
  5) 导出清洗后 CSV

## 4. 功能需求（模块）
### 4.1 数据管理（必做）
- 上传 CSV（<10MB），返回 `dataset_id`
- 预览前 N 行、列名、列类型推断（数值/类别/目标列）
- 输出：`dataset_id`、预览数据、行数

### 4.2 数据清洗（必做）
- 缺失值处理（默认 auto：数值用中位数、类别用众数；可选 drop_rows）
- 异常值检测与处理（IQR；默认 clip；可选 none / drop_rows）
- 类别规范化（默认开启：trim + lower）
- 输出：`cleaned_dataset_id` + 清洗摘要（行数变化、缺失统计、异常值统计）

### 4.3 分析功能（必做）
- 预处理：数值标准化 + 类别 One-Hot
- 划分：随机 80/20，分类任务使用分层抽样
- 训练：逻辑回归（必做）；可选随机森林用于对比
- 展示：指标、混淆矩阵、阈值滑块（用于展示概率→标签的变化）

### 4.4 可视化（必做 ≥3）
- 柱状统计：对 `gender / platform_usage / social_interaction_level / depression_label` 等列做计数
- 箱线分布：数值列按分类列分组展示（min/Q1/median/Q3/max）
- 散点相关：任意两数值列散点；可选按某列（如 label）分色

### 4.5 导出（必做）
- 导出清洗后数据：CSV 下载（MVP）

## 5. 接口（高层级）
- `POST /api/datasets/upload`（multipart：`file`，可选 `target_col`）
- `POST /api/datasets/{dataset_id}/clean`（json：清洗选项）
- `POST /api/datasets/{dataset_id}/train`（json：训练选项与模型名）
- `POST /api/model-runs/{model_run_id}/predict`（json：rows + 可选 threshold）
- `GET /api/datasets/{dataset_id}/stats`（query：图表数据）
- `GET /api/datasets/{dataset_id}/export`（下载 CSV）

## 6. 非功能需求
- 仅开发环境：不做登录/权限
- 文件限制：只允许 `.csv`，大小 <10MB
- 数据落盘：按 `UUID` 目录保存 raw/cleaned 与元数据；便于复现与演示

## 7. 验收测试用例
- Happy path：用样例 CSV 从上传到导出全流程跑通
- 边界：
  - 非 CSV / 空文件 / 列缺失（提示错误）
  - 目标列不是 0/1 或只有单类（提示无法训练）
  - 异常值策略切换（clip vs drop_rows）对行数/摘要有变化

## 8. 分工模板（待定）
- 5 人：前端 / 后端 / 算法 / 文档 / 测试
- 6 人：前端2 / 后端2 / 算法 / 文档&测试

