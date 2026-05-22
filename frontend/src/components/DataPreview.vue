<script setup>
defineProps({
  columns: { type: Array, default: () => [] },
  rows: { type: Array, default: () => [] },
});
</script>

<template>
  <div class="table-wrap" v-if="columns.length">
    <table>
      <thead>
        <tr>
          <th v-for="c in columns" :key="c">{{ c }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(r, idx) in rows" :key="idx">
          <td v-for="c in columns" :key="c">{{ r?.[c] ?? "" }}</td>
        </tr>
      </tbody>
    </table>
  </div>
  <p class="muted" v-else>暂无预览数据</p>
</template>

