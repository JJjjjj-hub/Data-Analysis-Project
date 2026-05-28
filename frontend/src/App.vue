<script setup>
import { computed, ref, watch } from "vue";
import DataPreview from "./components/DataPreview.vue";
import EChart from "./components/EChart.vue";
import {
  authLogin,
  authLogout,
  authMe,
  authRegister,
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
  { key: "upload", label: "1 上传" },
  { key: "clean", label: "2 清洗" },
  { key: "train", label: "3 分析" },
  { key: "viz", label: "4 可视化" },
  { key: "export", label: "5 导出" },
];
const activeStep = ref("upload");

const targetCol = ref("depression_label");
const uploadFile = ref(null);
const fileInputEl = ref(null);
const busy = ref(false);
const error = ref("");

const authedUser = ref(null);
const authMode = ref("login"); // login | register
const authForm = ref({ username: "", password: "" });

const datasetId = ref("");
const cleanedDatasetId = ref("");
const columns = ref([]);
const previewRows = ref([]);
const rowCount = ref(0);
const columnKinds = ref({});
const cleanReport = ref(null);
const showAdvanced = ref(false);

const cleaning = ref({
  target_col: "depression_label",
  missing_strategy: "auto",
  outlier_strategy: "iqr_clip",
  normalize_categories: true,
});

const trainOpts = ref({
  target_col: "depression_label",
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
const scatterColor = ref("depression_label");

const chartOption = ref(null);
const chartType = ref("count"); // count | box | scatter

const usableDatasetId = computed(() => cleanedDatasetId.value || datasetId.value);
const shortDatasetId = computed(() => (usableDatasetId.value ? `${usableDatasetId.value.slice(0, 8)}…` : "-"));
const shortModelRunId = computed(() => (modelRunId.value ? `${modelRunId.value.slice(0, 8)}…` : "-"));

const numericColumns = computed(() => columns.value.filter((c) => (columnKinds.value?.[c] || "") === "numeric"));
const categoricalColumns = computed(() => columns.value.filter((c) => (columnKinds.value?.[c] || "") === "categorical"));
const candidateRefCols = computed(() => {
  const t = targetCol.value;
  const base = [...categoricalColumns.value];
  if (columns.value.includes(t) && !base.includes(t)) base.push(t);
  return base;
});

function pickIfMissing(currentRef, candidates, fallback) {
  if (candidates.includes(currentRef.value)) return;
  currentRef.value = candidates[0] || fallback;
}

watch(
  () => [columns.value, columnKinds.value, targetCol.value],
  () => {
    // Set defaults based on uploaded schema
    pickIfMissing(countByCol, candidateRefCols.value, targetCol.value);
    pickIfMissing(boxGroupCol, candidateRefCols.value, targetCol.value);
    pickIfMissing(scatterColor, candidateRefCols.value, targetCol.value);
    pickIfMissing(boxValueCol, numericColumns.value, numericColumns.value[0] || boxValueCol.value);
    pickIfMissing(scatterX, numericColumns.value, numericColumns.value[0] || scatterX.value);
    pickIfMissing(scatterY, numericColumns.value, numericColumns.value[1] || numericColumns.value[0] || scatterY.value);
  },
  { immediate: true },
);

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
    const out = await uploadDataset(f, targetCol.value);
    datasetId.value = out.dataset_id;
    cleanedDatasetId.value = "";
    columns.value = out.columns;
    previewRows.value = out.preview_rows;
    rowCount.value = out.row_count;
    columnKinds.value = out.column_kinds || {};
    cleaning.value.target_col = targetCol.value;
    trainOpts.value.target_col = targetCol.value;
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
    const out = await cleanDataset(datasetId.value, cleaning.value);
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
  const t = trainOpts.value.target_col || "depression_label";
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
        textStyle: { color: "#fff", fontSize: 14, overflow: "truncate", width: 700 },
      },
      tooltip: {},
      xAxis: { type: "category", data: labels, axisLabel: { color: "rgba(255,255,255,0.75)" } },
      yAxis: { type: "value", axisLabel: { color: "rgba(255,255,255,0.75)" } },
      series: [{ type: "bar", data: values }],
      grid: { left: 40, right: 20, top: 70, bottom: 40 },
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
        textStyle: { color: "#fff", fontSize: 14, overflow: "truncate", width: 700 },
      },
      tooltip: { trigger: "item" },
      xAxis: { type: "category", data: groups, axisLabel: { color: "rgba(255,255,255,0.75)" } },
      yAxis: { type: "value", axisLabel: { color: "rgba(255,255,255,0.75)" } },
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
          textStyle: { color: "#fff", fontSize: 14, overflow: "truncate", width: 820 },
        },
        tooltip: { trigger: "item" },
        xAxis: { type: "value", name: scatterX.value, axisLabel: { color: "rgba(255,255,255,0.75)" } },
        yAxis: { type: "value", name: scatterY.value, axisLabel: { color: "rgba(255,255,255,0.75)" } },
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
        textStyle: { color: "#fff", fontSize: 14, overflow: "truncate", width: 820 },
      },
      tooltip: { trigger: "item" },
      legend: { top: 36, left: "center", textStyle: { color: "rgba(255,255,255,0.75)" } },
      xAxis: { type: "value", name: scatterX.value, axisLabel: { color: "rgba(255,255,255,0.75)" } },
      yAxis: { type: "value", name: scatterY.value, axisLabel: { color: "rgba(255,255,255,0.75)" } },
      series: Object.keys(groups).map((k) => ({ type: "scatter", name: String(k), data: groups[k] })),
      grid: { left: 55, right: 20, top: 92, bottom: 50 },
    };
  } catch (e) {
    setError(e);
  } finally {
    busy.value = false;
  }
}

async function onAuthSubmit() {
  busy.value = true;
  error.value = "";
  try {
    const { username, password } = authForm.value;
    const out = authMode.value === "register" ? await authRegister(username, password) : await authLogin(username, password);
    setToken(out.token);
    authedUser.value = out.user;
    authForm.value.password = "";
  } catch (e) {
    setError(e);
  } finally {
    busy.value = false;
  }
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
  <div class="container">
    <div class="header">
      <div class="brand">
        <div class="brand__title">交互式数据分析系统（分类版）</div>
        <div class="brand__sub">上传 → 清洗 → 分析 → 可视化 → 导出</div>
      </div>
      <div class="steps">
        <button
          v-for="s in steps"
          :key="s.key"
          class="step"
          :class="{ 'step--active': activeStep === s.key }"
          @click="goto(s.key)"
        >
          {{ s.label }}
        </button>
      </div>
    </div>

    <div class="grid">
      <div class="panel">
        <div class="panel__hd">
          <div class="panel__title">操作区</div>
          <div class="muted" v-if="authedUser">用户 {{ authedUser.username }} · 数据 {{ shortDatasetId }} · 模型 {{ shortModelRunId }}</div>
          <div class="muted" v-else>未登录</div>
        </div>
        <div class="panel__bd">
          <p class="error" v-if="error">{{ error }}</p>

          <div class="panel" style="margin-bottom: 14px" v-if="!authedUser">
            <div class="panel__hd">
              <div class="panel__title">{{ authMode === "login" ? "登录" : "注册" }}</div>
              <div class="row" style="gap: 8px">
                <button class="btn" @click="authMode = 'login'">登录</button>
                <button class="btn" @click="authMode = 'register'">注册</button>
              </div>
            </div>
            <div class="panel__bd">
              <div class="row">
                <div>
                  <label>用户名</label><br />
                  <input type="text" v-model="authForm.username" style="width: 220px" />
                </div>
                <div>
                  <label>密码</label><br />
                  <input type="password" v-model="authForm.password" style="width: 220px" />
                </div>
                <button class="btn btn--primary" :disabled="busy" @click="onAuthSubmit">{{ authMode === "login" ? "登录" : "注册并登录" }}</button>
              </div>
              <p class="muted" style="margin-top: 8px">登录后才能上传/清洗/分析/导出（用于区分不同用户的数据）。</p>
            </div>
          </div>

          <div class="row" v-if="authedUser" style="margin-bottom: 12px">
            <button class="btn btn--danger" :disabled="busy" @click="onLogout">退出登录</button>
          </div>

          <template v-if="activeStep === 'upload'">
            <div class="row">
              <div>
                <label>目标列</label><br />
                <input type="text" v-model="targetCol" style="width: 260px" />
              </div>
              <div>
                <label>选择 CSV</label><br />
                <input ref="fileInputEl" type="file" accept=".csv,text/csv" @change="onFileChange" />
                <div class="muted" style="margin-top: 6px" v-if="getSelectedFile()">
                  已选择：{{ getSelectedFile().name }}
                </div>
              </div>
              <button class="btn btn--primary" :disabled="busy || !authedUser" @click="onUpload">上传并预览</button>
            </div>
            <p class="muted" style="margin-top: 10px">建议使用你提供的 `Teen_Mental_Health_Dataset.csv`。</p>
          </template>

          <template v-else-if="activeStep === 'clean'">
            <div class="row">
              <div>
                <label>缺失值策略</label><br />
                <select v-model="cleaning.missing_strategy">
                  <option value="auto">auto（默认填充）</option>
                  <option value="drop_rows">drop_rows（丢弃含缺失行）</option>
                </select>
              </div>
              <div>
                <label>异常值策略</label><br />
                <select v-model="cleaning.outlier_strategy">
                  <option value="iqr_clip">iqr_clip（IQR截断）</option>
                  <option value="none">none</option>
                  <option value="iqr_drop_rows">iqr_drop_rows（删除异常行）</option>
                </select>
              </div>
              <div>
                <label>类别规范化</label><br />
                <select v-model="cleaning.normalize_categories">
                  <option :value="true">true</option>
                  <option :value="false">false</option>
                </select>
              </div>
              <button class="btn btn--primary" :disabled="busy" @click="onClean">执行清洗</button>
            </div>
            <div v-if="cleanReport" style="margin-top: 12px" class="code">{{ JSON.stringify(cleanReport, null, 2) }}</div>
          </template>

          <template v-else-if="activeStep === 'train'">
            <div class="row">
              <div>
                <label>模型</label><br />
                <select v-model="trainOpts.model">
                  <option value="logistic_regression">logistic_regression</option>
                  <option value="random_forest">random_forest</option>
                </select>
              </div>
              <div>
                <label>测试集比例</label><br />
                <input type="number" step="0.05" min="0.1" max="0.5" v-model.number="trainOpts.test_size" />
              </div>
              <div>
                <label>随机种子</label><br />
                <input type="number" v-model.number="trainOpts.random_state" />
              </div>
              <button class="btn btn--primary" :disabled="busy" @click="onTrain">训练并评估</button>
            </div>
            <div v-if="metrics" style="margin-top: 12px" class="code">{{ JSON.stringify(metrics, null, 2) }}</div>
          </template>

          <template v-else-if="activeStep === 'viz'">
            <div class="row" style="margin-bottom: 8px">
              <button class="btn" :disabled="!metrics" @click="goto('train')">回到分析</button>
              <button class="btn btn--primary" :disabled="busy || !modelRunId" @click="onPredictSample">用当前阈值预测预览行</button>
              <div class="row" style="gap: 8px">
                <label>阈值</label>
                <input type="number" min="0" max="1" step="0.01" v-model.number="threshold" style="width: 110px" />
              </div>
            </div>

            <div v-if="predSample" class="code" style="margin-bottom: 12px">
              {{ JSON.stringify({ threshold: predSample.threshold, positive: predSample.labels.filter((x) => x === 1).length, total: predSample.labels.length }, null, 2) }}
            </div>

            <div class="row" style="margin: 10px 0 6px">
              <strong>图表：</strong>
              <button class="btn" :class="{ 'btn--primary': chartType === 'count' }" @click="setChart('count')">柱状统计</button>
              <button class="btn" :class="{ 'btn--primary': chartType === 'box' }" @click="setChart('box')">箱线分布</button>
              <button class="btn" :class="{ 'btn--primary': chartType === 'scatter' }" @click="setChart('scatter')">散点相关</button>
            </div>
            <div class="muted">选中某种图表后，只显示该图的参数。</div>

            <div class="row" style="margin-top: 10px" v-if="chartType === 'count'">
              <div>
                <label>柱状分组列</label><br />
                <select v-model="countByCol">
                  <option v-for="c in candidateRefCols" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
              <button class="btn btn--primary" :disabled="busy" @click="loadCountBy">生成柱状图</button>
            </div>

            <div class="row" style="margin-top: 10px" v-else-if="chartType === 'box'">
              <div>
                <label>数值列（value）</label><br />
                <select v-model="boxValueCol">
                  <option v-for="c in numericColumns" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
              <div>
                <label>分组列（group）</label><br />
                <select v-model="boxGroupCol">
                  <option v-for="c in candidateRefCols" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
              <button class="btn btn--primary" :disabled="busy" @click="loadBoxBy">生成箱线图</button>
            </div>

            <div class="row" style="margin-top: 10px" v-else-if="chartType === 'scatter'">
              <div>
                <label>x 轴（数值列）</label><br />
                <select v-model="scatterX">
                  <option v-for="c in numericColumns" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
              <div>
                <label>y 轴（数值列）</label><br />
                <select v-model="scatterY">
                  <option v-for="c in numericColumns" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
              <div>
                <label>颜色列（可选）</label><br />
                <select v-model="scatterColor">
                  <option value="">(none)</option>
                  <option v-for="c in candidateRefCols" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
              <button class="btn btn--primary" :disabled="busy" @click="loadScatter">生成散点图</button>
            </div>

            <div v-if="chartOption" style="margin-top: 12px">
              <EChart :option="chartOption" height="460px" />
            </div>
          </template>

          <template v-else-if="activeStep === 'export'">
            <p class="muted">导出清洗后数据（若已清洗则导出 cleaned，否则导出 raw）。</p>
            <div class="row">
              <button class="btn btn--primary" :disabled="busy || !authedUser" @click="onDownloadCsv">下载 CSV</button>
              <button class="btn" @click="goto('upload')">重新上传</button>
            </div>
          </template>

          <div class="row" style="margin-top: 14px">
            <button class="btn" @click="goto('upload')">上传</button>
            <button class="btn" :disabled="!datasetId || !authedUser" @click="goto('clean')">清洗</button>
            <button class="btn" :disabled="!usableDatasetId || !authedUser" @click="goto('train')">分析</button>
            <button class="btn" :disabled="!usableDatasetId || !authedUser" @click="goto('viz')">可视化</button>
            <button class="btn" :disabled="!usableDatasetId || !authedUser" @click="goto('export')">导出</button>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel__hd">
          <div class="panel__title">数据预览</div>
          <div class="muted">rows: {{ rowCount || "-" }}</div>
        </div>
        <div class="panel__bd">
          <DataPreview :columns="columns" :rows="previewRows" />
          <div class="row" style="margin-top: 12px">
            <button class="btn" @click="showAdvanced = !showAdvanced">{{ showAdvanced ? "隐藏详情" : "显示详情" }}</button>
          </div>
          <div v-if="showAdvanced && Object.keys(columnKinds || {}).length" class="code" style="margin-top: 12px">
            {{ JSON.stringify(columnKinds, null, 2) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
