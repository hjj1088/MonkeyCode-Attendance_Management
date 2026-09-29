<template>
  <div class="sticky-table">
    <div ref="headWrap" class="sticky-head" @scroll="onHeadScroll">
      <table class="sticky-el" :style="{ minWidth }">
        <colgroup>
          <col v-for="(w, i) in cols" :key="'h' + i" :style="{ width: w }">
        </colgroup>
        <thead>
          <slot name="head" />
        </thead>
      </table>
    </div>
    <div ref="bodyWrap" class="sticky-body" @scroll="onBodyScroll">
      <table class="sticky-el" :style="{ minWidth }">
        <colgroup>
          <col v-for="(w, i) in cols" :key="'b' + i" :style="{ width: w }">
        </colgroup>
        <tbody>
          <slot />
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUpdated, onBeforeUnmount, nextTick } from 'vue';

defineProps({
  cols: { type: Array, default: () => [] },
  minWidth: { type: String, default: '960px' },
});

const headWrap = ref(null);
const bodyWrap = ref(null);
let syncing = false;
let resizeObserver = null;
let rafId = 0;

function applyOverflowTitles() {
  const wrap = bodyWrap.value;
  if (!wrap) return;
  wrap.querySelectorAll('td').forEach((td) => {
    if (td.querySelector('button, a, input, select, textarea')) return;
    if (td.scrollWidth > td.clientWidth) {
      const text = (td.textContent || '').trim();
      if (text) td.setAttribute('title', text);
    } else if (td.hasAttribute('title')) {
      td.removeAttribute('title');
    }
  });
}

function scheduleOverflowTitles() {
  cancelAnimationFrame(rafId);
  rafId = requestAnimationFrame(applyOverflowTitles);
}

onMounted(() => {
  scheduleOverflowTitles();
  if (typeof ResizeObserver !== 'undefined' && bodyWrap.value) {
    resizeObserver = new ResizeObserver(scheduleOverflowTitles);
    resizeObserver.observe(bodyWrap.value);
  }
});

onUpdated(() => {
  nextTick(scheduleOverflowTitles);
});

onBeforeUnmount(() => {
  cancelAnimationFrame(rafId);
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
});

function onHeadScroll() {
  if (syncing || !bodyWrap.value || !headWrap.value) return;
  syncing = true;
  bodyWrap.value.scrollLeft = headWrap.value.scrollLeft;
  syncing = false;
}

function onBodyScroll() {
  if (syncing || !bodyWrap.value || !headWrap.value) return;
  syncing = true;
  headWrap.value.scrollLeft = bodyWrap.value.scrollLeft;
  syncing = false;
}
</script>

<style scoped>
.sticky-table {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sticky-head {
  flex: 0 0 auto;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
  scrollbar-gutter: stable;
}
.sticky-head::-webkit-scrollbar { height: 0; display: none; }
.sticky-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  scrollbar-gutter: stable;
}
.sticky-el {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
}
.sticky-el :deep(th) { position: static; }
.sticky-el :deep(td) {
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
