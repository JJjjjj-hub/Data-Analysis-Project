<script setup>
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, BoxplotChart, ScatterChart, LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  DatasetComponent,
} from "echarts/components";

use([CanvasRenderer, BarChart, BoxplotChart, ScatterChart, LineChart, GridComponent, LegendComponent, TitleComponent, TooltipComponent, DatasetComponent]);

defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: "420px" },
});
</script>

<template>
  <VChart :option="option" :style="{ height }" autoresize />
</template>

