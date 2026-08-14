<template>
  <div v-if="!route.meta.noLayout" class="app-shell">
    <AppSidebar />
    <main class="main-content">
      <header class="topbar">
        <button class="hamburger-btn" @click="sidebarOpen = !sidebarOpen">
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
        </button>
        <span id="header-greeting">{{ greeting }}</span>
      </header>
      <div class="page-container">
        <router-view />
      </div>
    </main>
  </div>
  <router-view v-else />
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import AppSidebar from './components/AppSidebar.vue';
import Auth from './shared/auth';

const route = useRoute();
const sidebarOpen = ref(false);

const greeting = computed(() => {
  const hour = new Date().getHours();
  let g = '上午好';
  if (hour >= 12 && hour < 18) g = '下午好';
  if (hour >= 18) g = '晚上好';
  const name = (Auth.getUser() && Auth.getUser().name) || Auth.getUsername() || '管理员';
  return g + '，' + name;
});

onMounted(() => {
  sidebarOpen.value = false;
});
</script>
