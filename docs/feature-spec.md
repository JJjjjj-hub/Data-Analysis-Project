# 功能开发规范文档

## 概述
本文档定义了两个新功能的开发规范：
1. **后端A**：数据清洗 - 重复值检测与处理
2. **算法**：模型优化 - 超参数调优 + 特征重要性分析

---

## Part 1: 后端A - 重复值检测与处理

### 1.1 需求说明
在数据清洗流程中增加重复行检测和处理功能。

### 1.2 接口变更

#### 请求参数变更
`POST /api/datasets/{dataset_id}/clean/`

**新增字段**：
```json
{
  "target_col": "depression_label",
  "missing_strategy": "auto",
  "outlier_strategy": "iqr_clip",
  "normalize_categories": true,
  "duplicate_strategy": "none"  // 新增：none | keep_first | drop_all
}
```

#### 响应数据变更
```json
{
  "ok": true,
  "cleaned_dataset_id": "uuid",
  "clean_report": {
    "rows_before": 1000,
    "cols_before": 15,
    "rows_after": 980,
    "cols_after": 15,
    "missing": {...},
    "outliers": {...},
    "duplicates": {           // 新增字段
      "count": 20,
      "strategy": "keep_first",
      "dropped": 20
    },
    "normalized_categories": true,
    "notes": ["missing_strategy=auto", "duplicate_strategy=keep_first"]
  }
}
```

### 1.3 实现步骤

#### Step 1: 修改 CleaningOptions（cleaning.py 第11行）
```python
@dataclass(frozen=True)
class CleaningOptions:
    target_col: str = "depression_label"
    missing_strategy: str = "auto"
    outlier_strategy: str = "iqr_clip"
    normalize_categories: bool = True
    duplicate_strategy: str = "none"  # 新增：none | keep_first | drop_all
```

#### Step 2: 实现重复值处理逻辑（cleaning.py 第100行后插入）
```python
def _handle_duplicates(df: pd.DataFrame, strategy: str, report: Dict[str, Any]) -> pd.DataFrame:
    """处理重复行"""
    if strategy == "none":
        return df
    
    # 统计重复行（不包括第一次出现的）
    duplicate_mask = df.duplicated(keep='first')
    duplicate_count = int(duplicate_mask.sum())
    
    report["duplicates"] = {
        "count": duplicate_count,
        "strategy": strategy,
        "dropped": 0
    }
    
    if strategy == "keep_first":
        df_clean = df.drop_duplicates(keep='first')
        report["duplicates"]["dropped"] = duplicate_count
    elif strategy == "drop_all":
        # 删除所有重复的行（包括第一次出现的）
        df_clean = df.drop_duplicates(keep=False)
        # 计算实际删除的行数
        all_duplicates = df.duplicated(keep=False)
        report["duplicates"]["dropped"] = int(all_duplicates.sum())
    else:
        raise ValueError(f"Unknown duplicate_strategy: {strategy}")
    
    return df_clean
```

#### Step 3: 在 clean_dataframe 中调用（cleaning.py 第45行后插入）
```python
def clean_dataframe(df: pd.DataFrame, options: CleaningOptions) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    report: Dict[str, Any] = {...}
    
    df_clean = df.copy()
    
    # 新增：处理重复值（放在最前面，避免其他操作影响判断）
    if options.duplicate_strategy != "none":
        df_clean = _handle_duplicates(df_clean, options.duplicate_strategy, report)
        report["notes"].append(f"duplicate_strategy={options.duplicate_strategy}")
    
    # 原有逻辑继续...
```

#### Step 4: 修改 api_views.py 解析参数
在 `dataset_clean` 函数中（第121行附近）增加：
```python
@api_view(["POST"])
def dataset_clean(request, dataset_id: str):
    target_col = (request.data.get("target_col") or "depression_label").strip()
    missing_strategy = (request.data.get("missing_strategy") or "auto").strip()
    outlier_strategy = (request.data.get("outlier_strategy") or "iqr_clip").strip()
    normalize_categories = _parse_bool(request.data.get("normalize_categories"), True)
    duplicate_strategy = (request.data.get("duplicate_strategy") or "none").strip()  # 新增
    
    # 验证参数
    if duplicate_strategy not in {"none", "keep_first", "drop_all"}:
        return _bad_request("duplicate_strategy 必须是 none / keep_first / drop_all")
    
    options = CleaningOptions(
        target_col=target_col,
        missing_strategy=missing_strategy,
        outlier_strategy=outlier_strategy,
        normalize_categories=normalize_categories,
        duplicate_strategy=duplicate_strategy,  # 新增
    )
    # ...
```

### 1.4 测试用例
```python
# 测试数据（包含2行重复）
test_df = pd.DataFrame({
    'age': [15, 16, 17, 15, 15],  # 第1行和第4行重复
    'gender': ['M', 'F', 'M', 'M', 'M'],
    'score': [80, 90, 85, 80, 80]
})

# Test 1: strategy=none，不删除任何行，结果应为5行
# Test 2: strategy=keep_first，保留第一次出现，结果应为4行
# Test 3: strategy=drop_all，删除所有重复，结果应为3行（第1,4,5行都删掉）
```

---

## Part 2: 算法 - 超参数调优 + 特征重要性

### 2.1 需求说明
1. **超参数调优**：使用交叉验证自动搜索最优参数
2. **特征重要性**：返回模型中各特征的权重/重要性

### 2.2 接口变更

#### 请求参数变更
`POST /api/datasets/{dataset_id}/train/`

**新增字段**：
```json
{
  "target_col": "depression_label",
  "model": "logistic_regression",
  "test_size": 0.2,
  "random_state": 42,
  "enable_cv": false,           // 新增：是否启用交叉验证调优
  "cv_folds": 3                 // 新增：交叉验证折数（3-5）
}
```

#### 响应数据变更
```json
{
  "ok": true,
  "model_run_id": "uuid",
  "metrics": {
    "model": "logistic_regression",
    "target_col": "depression_label",
    "test_size": 0.2,
    "random_state": 42,
    "label_counts": {...},
    "precision": 0.85,
    "recall": 0.82,
    "f1": 0.835,
    "roc_auc": 0.91,
    "confusion_matrix": [...],
    "threshold_default": 0.5,
    "features": {
      "numeric": ["age", "sleep_hours"],
      "categorical": ["gender"]
    },
    "best_params": {              // 新增（enable_cv=true时返回）
      "C": 1.0,
      "class_weight": "balanced"
    },
    "cv_scores": {                // 新增（enable_cv=true时返回）
      "mean_f1": 0.84,
      "std_f1": 0.03,
      "scores": [0.82, 0.85, 0.85]
    },
    "feature_importance": [       // 新增
      {"feature": "sleep_hours", "importance": 0.45, "type": "positive"},
      {"feature": "age", "importance": 0.25, "type": "positive"},
      {"feature": "gender_M", "importance": -0.15, "type": "negative"}
    ]
  }
}
```

### 2.3 实现步骤

#### Step 1: 修改 TrainOptions（ml.py 第25行）
```python
@dataclass(frozen=True)
class TrainOptions:
    target_col: str = "depression_label"
    test_size: float = 0.2
    random_state: int = 42
    enable_cv: bool = False       # 新增
    cv_folds: int = 3             # 新增
```

#### Step 2: 实现超参数调优（ml.py 第103行附近）
```python
from sklearn.model_selection import GridSearchCV  # 新增导入

def _tune_hyperparams(pipe: Pipeline, X_train, y_train, model: str, cv_folds: int, random_state: int):
    """
    使用GridSearchCV搜索最优超参数
    返回: (best_pipe, cv_results_dict)
    """
    if model == "logistic_regression":
        param_grid = {
            'model__C': [0.01, 0.1, 1.0, 10.0],
            'model__class_weight': ['balanced', None]
        }
    elif model == "random_forest":
        param_grid = {
            'model__n_estimators': [100, 200, 300],
            'model__max_depth': [5, 10, None],
            'model__min_samples_split': [2, 5]
        }
    else:
        return pipe, None
    
    grid_search = GridSearchCV(
        pipe,
        param_grid,
        cv=cv_folds,
        scoring='f1',
        n_jobs=-1,
        random_state=random_state
    )
    grid_search.fit(X_train, y_train)
    
    cv_results = {
        "best_params": grid_search.best_params_,
        "cv_scores": {
            "mean_f1": float(grid_search.cv_results_['mean_test_score'][grid_search.best_index_]),
            "std_f1": float(grid_search.cv_results_['std_test_score'][grid_search.best_index_]),
            "scores": [
                float(grid_search.cv_results_[f'split{i}_test_score'][grid_search.best_index_])
                for i in range(cv_folds)
            ]
        }
    }
    
    return grid_search.best_estimator_, cv_results
```

#### Step 3: 实现特征重要性提取（ml.py 第127行后插入）
```python
def _extract_feature_importance(pipe: Pipeline, feature_names: List[str], model: str) -> List[Dict[str, Any]]:
    """
    提取特征重要性
    逻辑回归：返回系数（正负表示方向）
    随机森林：返回feature_importances_
    """
    if model == "logistic_regression":
        # 获取系数（注意：经过ColumnTransformer后特征顺序可能改变）
        coef = pipe.named_steps['model'].coef_[0]
        
        # 获取预处理后的特征名
        preprocessor = pipe.named_steps['preprocess']
        try:
            transformed_features = preprocessor.get_feature_names_out()
        except:
            # 如果无法获取，使用原始特征名（可能有偏差）
            transformed_features = feature_names
        
        importance_list = []
        for name, value in zip(transformed_features, coef):
            importance_list.append({
                "feature": name,
                "importance": float(abs(value)),
                "raw_value": float(value),
                "type": "positive" if value > 0 else "negative" if value < 0 else "neutral"
            })
        
        # 按绝对值排序
        importance_list.sort(key=lambda x: x["importance"], reverse=True)
        
    elif model == "random_forest":
        importances = pipe.named_steps['model'].feature_importances_
        
        try:
            transformed_features = pipe.named_steps['preprocess'].get_feature_names_out()
        except:
            transformed_features = feature_names
        
        importance_list = []
        for name, value in zip(transformed_features, importances):
            importance_list.append({
                "feature": name,
                "importance": float(value),
                "raw_value": float(value),
                "type": "importance"
            })
        
        importance_list.sort(key=lambda x: x["importance"], reverse=True)
    
    return importance_list[:10]  # 只返回前10个最重要的特征
```

#### Step 4: 修改 train_classifier 函数（ml.py 第79行）
```python
def train_classifier(df: pd.DataFrame, options: TrainOptions, *, model: str) -> Tuple[Pipeline, Dict[str, Any]]:
    # ... 原有验证逻辑 ...
    
    X_train, X_test, y_train, y_test = train_test_split(...)
    
    # 构建基础管道
    if model == "logistic_regression":
        pipe = build_logreg_pipeline(numeric_cols=numeric_cols, categorical_cols=categorical_cols)
    elif model == "random_forest":
        pipe = build_rf_pipeline(numeric_cols=numeric_cols, categorical_cols=categorical_cols)
    
    # 新增：超参数调优
    cv_results = None
    if options.enable_cv:
        pipe, cv_results = _tune_hyperparams(
            pipe, X_train, y_train, model, 
            options.cv_folds, options.random_state
        )
    else:
        pipe.fit(X_train, y_train)
    
    # 预测和评估（原有逻辑）
    proba = pipe.predict_proba(X_test)[:, 1]
    y_pred = (proba >= 0.5).astype(int)
    
    # 组装metrics
    metrics: Dict[str, Any] = {
        "model": model,
        "target_col": options.target_col,
        "test_size": options.test_size,
        "random_state": options.random_state,
        "label_counts": {...},
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(_safe_auc(y_test, proba)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "threshold_default": 0.5,
        "features": {"numeric": numeric_cols, "categorical": categorical_cols},
    }
    
    # 新增：添加CV结果
    if cv_results:
        metrics["best_params"] = cv_results["best_params"]
        metrics["cv_scores"] = cv_results["cv_scores"]
    
    # 新增：添加特征重要性
    all_feature_names = numeric_cols + categorical_cols
    metrics["feature_importance"] = _extract_feature_importance(pipe, all_feature_names, model)
    
    return pipe, metrics
```

#### Step 5: 修改 api_views.py 解析参数
在 `dataset_train` 函数中（第176行附近）增加：
```python
@api_view(["POST"])
def dataset_train(request, dataset_id: str):
    target_col = (request.data.get("target_col") or "depression_label").strip()
    model_name = (request.data.get("model") or "logistic_regression").strip()
    test_size = float(request.data.get("test_size") or 0.2)
    random_state = int(request.data.get("random_state") or 42)
    enable_cv = _parse_bool(request.data.get("enable_cv"), False)  # 新增
    cv_folds = int(request.data.get("cv_folds") or 3)               # 新增
    
    # 验证cv_folds
    if cv_folds < 2 or cv_folds > 5:
        return _bad_request("cv_folds 必须在 2-5 之间")
    
    # ...
    
    pipe, metrics = train_classifier(
        df,
        TrainOptions(
            target_col=target_col, 
            test_size=test_size, 
            random_state=random_state,
            enable_cv=enable_cv,      # 新增
            cv_folds=cv_folds         # 新增
        ),
        model=model_name,
    )
    # ...
```

### 2.4 依赖安装
```bash
pip install scikit-learn  # 确保版本 >= 1.3
```

---

## Part 3: 前端适配指南

### 3.1 数据清洗页面修改（App.vue）

#### 新增数据（第48行 cleaning 对象）
```javascript
const cleaning = ref({
  target_col: "depression_label",
  missing_strategy: "auto",
  outlier_strategy: "iqr_clip",
  normalize_categories: true,
  duplicate_strategy: "none",  // 新增
});
```

#### 新增UI（第481行 clean 模板区域）
```vue
<template v-else-if="activeStep === 'clean'">
  <div class="row">
    <!-- 原有选项... -->
    <div>
      <label>重复值策略</label><br />
      <select v-model="cleaning.duplicate_strategy">
        <option value="none">none（不处理）</option>
        <option value="keep_first">keep_first（保留首次出现）</option>
        <option value="drop_all">drop_all（删除所有重复行）</option>
      </select>
    </div>
    <button class="btn btn--primary" :disabled="busy" @click="onClean">执行清洗</button>
  </div>
  
  <!-- 清洗报告显示 -->
  <div v-if="cleanReport" style="margin-top: 12px" class="code">
    {{ JSON.stringify(cleanReport, null, 2) }}
  </div>
  <!-- 显示重复值统计 -->
  <div v-if="cleanReport?.duplicates?.count > 0" style="margin-top: 8px; color: #ff9800;">
    检测到 {{ cleanReport.duplicates.count }} 行重复数据，
    已删除 {{ cleanReport.duplicates.dropped }} 行
  </div>
</template>
```

### 3.2 训练页面修改（App.vue）

#### 新增数据（第55行 trainOpts 对象）
```javascript
const trainOpts = ref({
  target_col: "depression_label",
  model: "logistic_regression",
  test_size: 0.2,
  random_state: 42,
  enable_cv: false,    // 新增
  cv_folds: 3,         // 新增
});
```

#### 新增UI（第510行 train 模板区域）
```vue
<template v-else-if="activeStep === 'train'">
  <div class="row">
    <!-- 原有选项... -->
    <div>
      <label>交叉验证</label><br />
      <select v-model="trainOpts.enable_cv">
        <option :value="false">关闭</option>
        <option :value="true">启用</option>
      </select>
    </div>
    <div v-if="trainOpts.enable_cv">
      <label>CV折数</label><br />
      <input type="number" min="2" max="5" v-model.number="trainOpts.cv_folds" />
    </div>
    <button class="btn btn--primary" :disabled="busy" @click="onTrain">训练并评估</button>
  </div>
  
  <!-- 指标显示 -->
  <div v-if="metrics" style="margin-top: 12px" class="code">
    {{ JSON.stringify(metrics, null, 2) }}
  </div>
  
  <!-- 新增：特征重要性图表 -->
  <div v-if="metrics?.feature_importance?.length" style="margin-top: 16px;">
    <div style="font-weight: bold; margin-bottom: 8px;">特征重要性 TOP5</div>
    <div v-for="feat in metrics.feature_importance.slice(0, 5)" :key="feat.feature"
         style="display: flex; align-items: center; margin: 4px 0;">
      <span style="width: 120px; font-size: 12px;">{{ feat.feature }}</span>
      <div style="flex: 1; background: #333; height: 16px; border-radius: 4px; overflow: hidden;">
        <div :style="{width: `${feat.importance * 100}%`, background: feat.type === 'negative' ? '#f44336' : '#4caf50', height: '100%'}"
             style="transition: width 0.3s;"></div>
      </div>
      <span style="width: 60px; text-align: right; font-size: 12px;">{{ feat.importance.toFixed(3) }}</span>
    </div>
  </div>
</template>
```

### 3.3 API 调用确认
确保 `api.js` 中的 `cleanDataset` 和 `trainDataset` 函数会透传所有参数（它们应该已经会透传，但需确认）：

```javascript
// api.js - 确保参数正确传递
export const cleanDataset = (datasetId, options) => 
  post(`/api/datasets/${datasetId}/clean/`, options);  // options 包含所有字段

export const trainDataset = (datasetId, options) => 
  post(`/api/datasets/${datasetId}/train/`, options);  // options 包含所有字段
```

---

## 验收标准

### 后端A验收
- [ ] `duplicate_strategy=none` 时，不删除任何行，响应中 `duplicates.count` 正确
- [ ] `duplicate_strategy=keep_first` 时，正确删除后续重复行
- [ ] `duplicate_strategy=drop_all` 时，删除所有重复行
- [ ] 清洗报告正确显示重复值统计

### 算法验收
- [ ] `enable_cv=false` 时，训练速度正常，返回 `feature_importance`
- [ ] `enable_cv=true` 时，返回 `best_params` 和 `cv_scores`
- [ ] 逻辑回归返回系数（含正负）
- [ ] 随机森林返回 feature_importances_
- [ ] 特征重要性按绝对值降序排列

### 前端验收
- [ ] 清洗页面显示重复值策略下拉框
- [ ] 训练页面显示交叉验证开关和折数选择
- [ ] 训练结果显示特征重要性进度条
- [ ] 所有新功能与后端联调通过

---

## 协作流程

1. **Week 1**：
   - 后端A完成 `cleaning.py` 修改，本地测试通过
   - 算法完成 `ml.py` 修改，本地测试通过
   - 前端在 Mock 模式下完成 UI 修改

2. **Week 2**：
   - 各自提交 PR 到 `main` 分支
   - 联调测试，修复问题
   - 合并到 `main`，全员使用统一版本

3. **联调方式**：
   ```bash
   # 后端A启动服务
   python manage.py runserver 8001
   
   # 前端连接后端A测试
   VITE_API_BASE=http://localhost:8001/api npm run dev
   ```

---

*文档版本：v1.0*
*最后更新：2026-05-28*
