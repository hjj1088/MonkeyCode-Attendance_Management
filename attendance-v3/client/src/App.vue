<template>
  <div v-if="showLayout" class="app-shell">
    <div v-if="sidebarOpen" class="sidebar-overlay" @click="sidebarOpen = false"></div>
    <AppSidebar :open="sidebarOpen" @navigate="sidebarOpen = false" />
    <main class="main-content">
      <header class="topbar">
        <button class="hamburger-btn" aria-label="打开菜单" @click="sidebarOpen = !sidebarOpen">
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
        </button>
        <h1 class="page-title">{{ pageTitle }}</h1>
        <span class="topbar-spacer"></span>
        <span v-if="contextChip" class="context-chip">{{ contextChip }}</span>
      </header>
      <div class="page-container">
        <router-view />
      </div>
    </main>
  </div>
  <router-view v-else />
</template>

<script setup>
import { computed, ref, provide } from 'vue';
import { useRoute } from 'vue-router';
import AppSidebar from './components/AppSidebar.vue';

const route = useRoute();
const sidebarOpen = ref(false);
const contextChip = ref('');

provide('setContextChip', (text) => { contextChip.value = text || ''; });

const showLayout = computed(
  () => route.matched.length > 0 && route.meta.noLayout !== true,
);
const pageTitle = computed(() => route.meta.title || '考勤管理');
</script>
