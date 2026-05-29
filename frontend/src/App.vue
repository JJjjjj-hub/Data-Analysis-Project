<script setup>
import { computed, ref, watch } from "vue";
import DataPreview from "./components/DataPreview.vue";
import EChart from "./components/EChart.vue";
import LoginPage from "./components/LoginPage.vue";
import {
  authLogout,
  authMe,
  cleanDataset,
  downloadDatasetCsv,
  getToken,
  predict,
  setToken,
  stats,
  trainDataset,
  uploadDataset,
} from "./api";

const steps = [
  { key: "upload", label: "上传数据" },
  { key: "clean", label: "数据清洗" },
  { key: "train", label: "模型分析" },
  { key: "viz", label: "可视化" },
  { key: "export", label: "导出数据" },
];
const activeStep = ref("upload");

const uploadFile = ref(null);
const fileInputEl = ref(null);
const busy = ref(false);
const error = ref("");

const authedUser = ref(null);

const datasetId = ref("");
const cleanedDatasetId = ref("");
const columns = ref([]);
const previewRows = ref([]);
const rowCount = ref(0);
const columnKinds = ref({});
const cleanReport = ref(null);
const showAdvanced = ref(false);

const cleaning = ref({
  missing_strategy: "auto",
  outlier_strategy: "none",
  normalize_categories: true,
});

const trainOpts = ref({
  target_col: "",
  model: "logistic_regression",
  test_size: 0.2,
  random_state: 42,
});

const modelRunId = ref("");
const metrics = ref(null);
const threshold = ref(0.5);
const predSample = ref(null);

const countByCol = ref("gender");
const boxValueCol = ref("daily_social_media_hours");
const boxGroupCol = ref("gender");
const scatterX = ref("daily_social_media_hours");
const scatterY = ref("sleep_hours");
const scatterColor = ref("");

const chartOption = ref(null);
const chartType = ref("count"); // count | box | scatter | pie

const usableDatasetId = computed(() => cleanedDatasetId.value || datasetId.value);
const shortDatasetId = computed(() => (usableDatasetId.value ? `${usableDatasetId.value.slice(0, 8)}…` : "-"));
const shortModelRunId = computed(() => (modelRunId.value ? `${modelRunId.value.slice(0, 8)}…` : "-"));

const numericColumns = computed(() => columns.value.filter((c) => (columnKinds.value?.[c] || "") === "numeric"));
const categoricalColumns = computed(() => columns.value.filter((c) => (columnKinds.value?.[c] || "") === "categorical"));
const scatterYOptions = computed(() => numericColumns.value.filter((c) => c !== scatterX.value));
const binaryColumns = computed(() => columns.value.filter((c) => (columnKinds.value?.[c] || "") === "binary"));
const candidateRefCols = computed(() => {
  const base = [...categoricalColumns.value];
  // 训练时选择的目标列也可作为分类参考列
  const t = trainOpts.value.target_col;
  if (t && columns.value.includes(t) && !base.includes(t)) base.push(t);
  return base;
});

function pickIfMissing(currentRef, candidates, fallback) {
  if (candidates.includes(currentRef.value)) return;
  currentRef.value = candidates[0] || fallback;
}

watch(
  () => [columns.value, columnKinds.value],
  () => {
    // Set defaults based on uploaded schema
    pickIfMissing(countByCol, candidateRefCols.value, columns.value[0] || "");
    pickIfMissing(boxGroupCol, candidateRefCols.value, columns.value[0] || "");
    pickIfMissing(scatterColor, candidateRefCols.value, "");
    pickIfMissing(boxValueCol, numericColumns.value, numericColumns.value[0] || "");
    pickIfMissing(scatterX, numericColumns.value, numericColumns.value[0] || "");
    pickIfMissing(scatterY, numericColumns.value, numericColumns.value[1] || numericColumns.value[0] || "");
  },
  { immediate: true },
);

// 当 scatterX 变化时，如果 scatterY 和 scatterX 相同，自动切换到下一个可选列
watch(scatterX, (newX) => {
  if (scatterY.value === newX) {
    const opts = scatterYOptions.value;
    scatterY.value = opts[0] || "";
  }
});

function setError(e) {
  error.value = e?.message || String(e || "请求失败");
}

async function refreshMe() {
  if (!getToken()) {
    authedUser.value = null;
    return;
  }
  try {
    const out = await authMe();
    authedUser.value = out.user;
  } catch {
    setToken("");
    authedUser.value = null;
  }
}

refreshMe();

function goto(step) {
  activeStep.value = step;
  error.value = "";
  chartOption.value = null;
  cleanReport.value = null;
  metrics.value = null;
  predSample.value = null;
}

function setChart(type) {
  chartType.value = type;
  chartOption.value = null;
  error.value = "";
}

function onFileChange(e) {
  const el = e?.target;
  const f = el?.files?.[0] || null;
  uploadFile.value = f;
  error.value = "";
}

function getSelectedFile() {
  return uploadFile.value || fileInputEl.value?.files?.[0] || null;
}

async function onUpload() {
  if (!authedUser.value) {
    error.value = "请先登录";
    return;
  }
  const f = getSelectedFile();
  if (!f) {
    error.value = "请选择CSV文件";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    const out = await uploadDataset(f);
    datasetId.value = out.dataset_id;
    cleanedDatasetId.value = "";
    columns.value = out.columns;
    previewRows.value = out.preview_rows;
    rowCount.value = out.row_count;
    columnKinds.value = out.column_kinds || {};
    // 默认选择第一个二分类列作为目标列，如果没有则留空
    const binaryCols = out.columns.filter((c) => (out.column_kinds?.[c] || "") === "binary");
    trainOpts.value.target_col = binaryCols[0] || "";
    goto("clean");
  } catch (e) {
    setError(e);
  } finally {
    busy.value = false;
  }
}

async function onClean() {
  if (!authedUser.value) {
    error.value = "请先登录";
    return;
  }
  if (!datasetId.value) return;
  busy.value = true;
  error.value = "";
  try {
    const out = await cleanDataset(datasetId.value, {
      ...cleaning.value,
      target_col: trainOpts.value.target_col,
    });
    cleanedDatasetId.value = out.cleaned_dataset_id;
    cleanReport.value = out.clean_report;
    columns.value = out.columns;
    previewRows.value = out.preview_rows;
    rowCount.value = out.row_count;
    columnKinds.value = out.column_kinds || {};
    goto("train");
  } catch (e) {
    setError(e);
  } finally {
    busy.value = false;
  }
}

function rowsForPredict() {
  const t = trainOpts.value.target_col;
  if (!t) return [];
  return (previewRows.value || []).map((r) => {
    const copy = { ...r };
    delete copy[t];
    return copy;
  });
}

async function onTrain() {
  if (!authedUser.value) {
    error.value = "请先登录";
    return;
  }
  if (!usableDatasetId.value) return;
  if (!trainOpts.value.target_col) {
    error.value = "请先选择目标列";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    const out = await trainDataset(usableDatasetId.value, trainOpts.value);
    modelRunId.value = out.model_run_id;
    metrics.value = out.metrics;
    threshold.value = Number(out.metrics?.threshold_default ?? 0.5);
    predSample.value = null;
    goto("viz");
  } catch (e) {
    setError(e);
  } finally {
    busy.value = false;
  }
}

async function onPredictSample() {
  if (!authedUser.value) {
    error.value = "请先登录";
    return;
  }
  if (!modelRunId.value) return;
  busy.value = true;
  error.value = "";
  try {
    const out = await predict(modelRunId.value, rowsForPredict(), threshold.value);
    predSample.value = out;
  } catch (e) {
    setError(e);
  } finally {
    busy.value = false;
  }
}

async function loadCountBy() {
  if (!authedUser.value) {
    error.value = "请先登录";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    const out = await stats(usableDatasetId.value, { kind: "count_by", col: countByCol.value });
    const counts = out.counts || {};
    const labels = Object.keys(counts);
    const values = labels.map((k) => counts[k]);
    chartOption.value = {
      title: {
        text: `计数：${countByCol.value}`,
        left: "center",
        top: 8,
        textStyle: { color: "#1d1d1f", fontSize: 14, overflow: "truncate", width: 700 },
      },
      tooltip: {},
      xAxis: { type: "category", data: labels, axisLabel: { color: "#7a7a7a" } },
      yAxis: { type: "value", axisLabel: { color: "#7a7a7a" } },
      series: [{ type: "bar", data: values }],
      grid: { left: 40, right: 20, top: 70, bottom: 40 },
    };
  } catch (e) {
    setError(e);
  } finally {
    busy.value = false;
  }
}

async function loadPie() {
  if (!authedUser.value) {
    error.value = "请先登录";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    const out = await stats(usableDatasetId.value, { kind: "count_by", col: countByCol.value });
    const counts = out.counts || {};
    const labels = Object.keys(counts);
    const values = labels.map((k) => counts[k]);
    const pieData = labels.map((k, i) => ({ name: k, value: counts[k] }));
    chartOption.value = {
      title: {
        text: `饼状图：${countByCol.value}`,
        left: "center",
        top: 8,
        textStyle: { color: "#1d1d1f", fontSize: 14, overflow: "truncate", width: 700 },
      },
      tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
      legend: { top: 36, left: "center", textStyle: { color: "#7a7a7a" } },
      series: [
        {
          type: "pie",
          radius: ["25%", "55%"],
          center: ["50%", "58%"],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
          label: { show: true, formatter: "{b}\n{d}%", color: "#555" },
          labelLine: { show: true },
          emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: "rgba(0,0,0,0.3)" } },
          data: pieData,
        },
      ],
    };
  } catch (e) {
    setError(e);
  } finally {
    busy.value = false;
  }
}

async function loadBoxBy() {
  if (!authedUser.value) {
    error.value = "请先登录";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    const out = await stats(usableDatasetId.value, { kind: "box_by", value_col: boxValueCol.value, group_col: boxGroupCol.value });
    const series = out.series || [];
    const groups = series.map((s) => s.group);
    const values = series.map((s) => s.box);
    chartOption.value = {
      title: {
        text: `箱线：${boxValueCol.value} by ${boxGroupCol.value}`,
        left: "center",
        top: 8,
        textStyle: { color: "#1d1d1f", fontSize: 14, overflow: "truncate", width: 700 },
      },
      tooltip: { trigger: "item" },
      xAxis: { type: "category", data: groups, axisLabel: { color: "#7a7a7a" } },
      yAxis: { type: "value", axisLabel: { color: "#7a7a7a" } },
      series: [{ type: "boxplot", data: values }],
      grid: { left: 40, right: 20, top: 70, bottom: 40 },
    };
  } catch (e) {
    setError(e);
  } finally {
    busy.value = false;
  }
}

async function loadScatter() {
  if (!authedUser.value) {
    error.value = "请先登录";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    const out = await stats(usableDatasetId.value, { kind: "scatter", x_col: scatterX.value, y_col: scatterY.value, color_col: scatterColor.value || "", limit: 1200 });
    const points = out.points || [];
    const hasC = points.length && Object.prototype.hasOwnProperty.call(points[0], "c");
    if (!hasC) {
      chartOption.value = {
        title: {
          text: `散点：${scatterX.value} vs ${scatterY.value}`,
          left: "center",
          top: 8,
          textStyle: { color: "#1d1d1f", fontSize: 14, overflow: "truncate", width: 820 },
        },
        tooltip: { trigger: "item" },
        xAxis: { type: "value", name: scatterX.value, axisLabel: { color: "#7a7a7a" } },
        yAxis: { type: "value", name: scatterY.value, axisLabel: { color: "#7a7a7a" } },
        series: [{ type: "scatter", data: points.map((p) => [p.x, p.y]) }],
        grid: { left: 55, right: 20, top: 70, bottom: 50 },
      };
      return;
    }
    const groups = {};
    for (const p of points) {
      groups[p.c] ||= [];
      groups[p.c].push([p.x, p.y]);
    }
    chartOption.value = {
      title: {
        text: `散点：${scatterX.value} vs ${scatterY.value}（按 ${scatterColor.value}）`,
        left: "center",
        top: 8,
        textStyle: { color: "#1d1d1f", fontSize: 14, overflow: "truncate", width: 820 },
      },
      tooltip: { trigger: "item" },
      legend: { top: 36, left: "center", textStyle: { color: "#7a7a7a" } },
      xAxis: { type: "value", name: scatterX.value, axisLabel: { color: "#7a7a7a" } },
      yAxis: { type: "value", name: scatterY.value, axisLabel: { color: "#7a7a7a" } },
      series: Object.keys(groups).map((k) => ({ type: "scatter", name: String(k), data: groups[k] })),
      grid: { left: 55, right: 20, top: 92, bottom: 50 },
    };
  } catch (e) {
    setError(e);
  } finally {
    busy.value = false;
  }
}

function onAuthenticated(user) {
  authedUser.value = user;
}

async function onLogout() {
  busy.value = true;
  error.value = "";
  try {
    await authLogout();
  } catch {
    // ignore
  } finally {
    setToken("");
    authedUser.value = null;
    busy.value = false;
  }
}

async function onDownloadCsv() {
  if (!authedUser.value) {
    error.value = "请先登录";
    return;
  }
  if (!usableDatasetId.value) {
    error.value = "请先上传并清洗数据";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    const blob = await downloadDatasetCsv(usableDatasetId.value);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${usableDatasetId.value}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    setError(e);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <LoginPage v-if="!authedUser" @authenticated="onAuthenticated" />

  <div class="app-shell" v-else>
    <!-- ── Sidebar ── -->
    <aside class="sidebar">
      <div class="sidebar__brand">
        <div class="sidebar__title">交互式数据分析系统</div>
        <div class="sidebar__sub">青少年心理健康 · 分类版</div>
      </div>

      <div class="sidebar__user">
        <span class="sidebar__username">{{ authedUser.username }}</span>
        <button class="btn btn--sm btn--danger" :disabled="busy" @click="onLogout">退出</button>
      </div>

      <!-- Navigation -->
      <nav class="sidebar__nav">
        <button
          v-for="s in steps"
          :key="s.key"
          class="nav-item"
          :class="{ 'nav-item--active': activeStep === s.key }"
          @click="goto(s.key)"
        >
          {{ s.label }}
        </button>
      </nav>

      <div class="sidebar__foot">
        <div class="muted">
          数据 {{ shortDatasetId }}<br />模型 {{ shortModelRunId }}
        </div>
      </div>
    </aside>

    <!-- ── Main Content ── -->
    <main class="main">
      <p class="error" v-if="error">{{ error }}</p>

      <!-- Step: Upload -->
      <div class="section" v-if="activeStep === 'upload'">
        <div class="section__header">
          <span class="section__title">上传数据</span>
          <span class="section__sub">流程：{{ steps.map(s => s.label).join(' → ') }}</span>
        </div>
        <div class="row">
          <div class="form-group">
            <label>选择 CSV 文件</label>
            <div class="file-row">
              <label class="file-btn">
                选择文件
                <input ref="fileInputEl" type="file" accept=".csv,text/csv" @change="onFileChange" hidden />
              </label>
              <span class="file-name" v-if="getSelectedFile()">{{ getSelectedFile().name }}</span>
            </div>
          </div>
          <button class="btn btn--primary" :disabled="busy || !authedUser" @click="onUpload">上传并预览</button>
        </div>
        <p class="muted" style="margin-top: 10px">支持任意 CSV 文件，目标列将在训练步骤中选择。</p>
      </div>

      <!-- Step: Clean -->
      <div class="section" v-if="activeStep === 'clean'">
        <div class="section__header">
          <span class="section__title">数据清洗</span>
          <span class="section__sub">数据集 {{ shortDatasetId }}</span>
        </div>
        <div class="row">
          <div class="form-group">
            <label>缺失值策略</label>
            <select v-model="cleaning.missing_strategy">
              <option value="auto">auto（默认填充）</option>
              <option value="drop_rows">drop_rows（丢弃含缺失行）</option>
            </select>
          </div>
          <div class="form-group">
            <label>异常值策略</label>
            <select v-model="cleaning.outlier_strategy">
              <option value="iqr_clip">iqr_clip（IQR 截断）</option>
              <option value="none">none</option>
              <option value="iqr_drop_rows">iqr_drop_rows（删除异常行）</option>
            </select>
          </div>
          <div class="form-group">
            <label>类别规范化</label>
            <select v-model="cleaning.normalize_categories">
              <option :value="true">true</option>
              <option :value="false">false</option>
            </select>
          </div>
          <button class="btn btn--primary" :disabled="busy" @click="onClean">执行清洗</button>
        </div>
        <div v-if="cleanReport" class="code mt-md">{{ JSON.stringify(cleanReport, null, 2) }}</div>
      </div>

      <!-- Step: Train -->
      <div class="section" v-if="activeStep === 'train'">
        <div class="section__header">
          <span class="section__title">模型训练</span>
          <span class="section__sub">数据集 {{ shortDatasetId }}</span>
        </div>
        <div class="row">
          <div class="form-group">
            <label>目标列 *</label>
            <select v-model="trainOpts.target_col" style="min-width: 150px">
              <option value="">请选择目标列</option>
              <option v-for="c in binaryColumns" :key="c" :value="c">{{ c }}</option>
            </select>
            <span v-if="binaryColumns.length === 0" class="muted" style="font-size: 12px; color: #dc2626;">未检测到二分类列(0/1)</span>
          </div>
          <div class="form-group">
            <label>模型</label>
            <select v-model="trainOpts.model">
              <option value="logistic_regression">logistic_regression</option>
              <option value="random_forest">random_forest</option>
            </select>
          </div>
          <div class="form-group">
            <label>测试集比例</label>
            <input type="number" step="0.05" min="0.1" max="0.5" v-model.number="trainOpts.test_size" style="width: 100px" />
          </div>
          <div class="form-group">
            <label>随机种子</label>
            <input type="number" v-model.number="trainOpts.random_state" style="width: 100px" />
          </div>
          <button class="btn btn--primary" :disabled="busy || !trainOpts.target_col" @click="onTrain">训练并评估</button>
        </div>
        <p class="muted" style="margin-top: 8px">* 目标列应为二分类（0/1），用于监督学习训练</p>
        <div v-if="metrics" class="code mt-md">{{ JSON.stringify(metrics, null, 2) }}</div>
      </div>

      <!-- Step: Viz -->
      <div class="section" v-if="activeStep === 'viz'">
        <div class="section__header">
          <span class="section__title">可视化与预测</span>
          <span class="section__sub">模型 {{ shortModelRunId }}</span>
        </div>

        <div class="row mb-sm">
          <button class="btn" :disabled="!metrics" @click="goto('train')">返回训练</button>
          <button class="btn btn--primary" :disabled="busy || !modelRunId" @click="onPredictSample">预测预览行</button>
          <div class="form-group">
            <label>阈值</label>
            <input type="number" min="0" max="1" step="0.01" v-model.number="threshold" style="width: 100px" />
          </div>
        </div>

        <!-- 预测结果展示 -->
        <div v-if="predSample" class="prediction-result mb-md">
          <div class="prediction-header">
            <span class="prediction-title">预测结果概览</span>
            <span class="prediction-threshold">阈值: {{ predSample.threshold }}</span>
          </div>
          <div class="prediction-stats">
            <div class="stat-item">
              <div class="stat-value">{{ predSample.labels?.length || 0 }}</div>
              <div class="stat-label">总样本</div>
            </div>
            <div class="stat-item positive">
              <div class="stat-value">{{ predSample.labels.filter((x) => x === 1).length }}</div>
              <div class="stat-label">阳性预测</div>
            </div>
            <div class="stat-item negative">
              <div class="stat-value">{{ predSample.labels.filter((x) => x === 0).length }}</div>
              <div class="stat-label">阴性预测</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ (predSample.proba.reduce((a, b) => a + b, 0) / predSample.proba.length * 100).toFixed(1) }}%</div>
              <div class="stat-label">平均概率</div>
            </div>
          </div>
          <div class="prediction-detail">
            <div class="detail-item">
              <span class="detail-label">最高概率:</span>
              <span class="detail-value">{{ (Math.max(...predSample.proba) * 100).toFixed(1) }}%</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">最低概率:</span>
              <span class="detail-value">{{ (Math.min(...predSample.proba) * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </div>

        <div class="mb-sm" style="font-weight: 650; font-size: 14px">图表类型</div>
        <div class="chart-tabs mb-md">
          <button class="chart-tab" :class="{ 'chart-tab--active': chartType === 'count' }" @click="setChart('count')">柱状统计</button>
          <button class="chart-tab" :class="{ 'chart-tab--active': chartType === 'pie' }" @click="setChart('pie')">饼状图</button>
          <button class="chart-tab" :class="{ 'chart-tab--active': chartType === 'box' }" @click="setChart('box')">箱线分布</button>
          <button class="chart-tab" :class="{ 'chart-tab--active': chartType === 'scatter' }" @click="setChart('scatter')">散点相关</button>
        </div>

        <div class="row mt-sm" v-if="chartType === 'count'">
          <div class="form-group">
            <label>分组列</label>
            <select v-model="countByCol">
              <option v-for="c in candidateRefCols" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <button class="btn btn--primary" :disabled="busy" @click="loadCountBy">生成柱状图</button>
        </div>

        <div class="row mt-sm" v-else-if="chartType === 'pie'">
          <div class="form-group">
            <label>分组列</label>
            <select v-model="countByCol">
              <option v-for="c in candidateRefCols" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <button class="btn btn--primary" :disabled="busy" @click="loadPie">生成饼状图</button>
        </div>

        <div class="row mt-sm" v-else-if="chartType === 'box'">
          <div class="form-group">
            <label>数值列</label>
            <select v-model="boxValueCol">
              <option v-for="c in numericColumns" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>分组列</label>
            <select v-model="boxGroupCol">
              <option v-for="c in candidateRefCols" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <button class="btn btn--primary" :disabled="busy" @click="loadBoxBy">生成箱线图</button>
        </div>

        <div class="row mt-sm" v-else-if="chartType === 'scatter'">
          <div class="form-group">
            <label>X 轴</label>
            <select v-model="scatterX">
              <option v-for="c in numericColumns" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Y 轴</label>
            <select v-model="scatterY">
              <option v-for="c in scatterYOptions" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>颜色列</label>
            <select v-model="scatterColor">
              <option value="">(none)</option>
              <option v-for="c in candidateRefCols" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <button class="btn btn--primary" :disabled="busy" @click="loadScatter">生成散点图</button>
        </div>

        <div v-if="chartOption" class="mt-md">
          <EChart :option="chartOption" height="460px" />
        </div>
      </div>

      <!-- Step: Export -->
      <div class="section" v-if="activeStep === 'export'">
        <div class="section__header">
          <span class="section__title">导出数据</span>
          <span class="section__sub">数据集 {{ shortDatasetId }}</span>
        </div>
        <p class="muted mb-sm">导出清洗后数据（若已清洗则导出 cleaned，否则导出 raw）。</p>
        <div class="row">
          <button class="btn btn--primary" :disabled="busy || !authedUser" @click="onDownloadCsv">下载 CSV</button>
          <button class="btn" @click="goto('upload')">重新上传</button>
        </div>
      </div>

      <!-- Data Preview -->
      <div class="section" v-if="columns.length">
        <div class="section__header">
          <span class="section__title">数据预览</span>
          <span class="section__sub">rows: {{ rowCount || "-" }}</span>
        </div>
        <DataPreview :columns="columns" :rows="previewRows" />
        <div class="row mt-sm">
          <button class="btn btn--sm" @click="showAdvanced = !showAdvanced">
            {{ showAdvanced ? "隐藏详情" : "列类型详情" }}
          </button>
        </div>
        <div v-if="showAdvanced && Object.keys(columnKinds || {}).length" class="code mt-sm">
          {{ JSON.stringify(columnKinds, null, 2) }}
        </div>
      </div>
    </main>
  </div>
</template>