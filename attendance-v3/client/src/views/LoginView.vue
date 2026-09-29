<template>
  <div class="login-page">
    <div class="login-card">
      <div class="flex-center mb-md">
        <div class="login-logo-seal">勤</div>
      </div>
      <h1>考勤管理系统</h1>
      <p class="subtitle">Attendance Management</p>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <div class="form-group">
        <label class="form-label" for="username">用户名</label>
        <input ref="usernameInput" type="text" id="username" v-model="username" class="form-input" placeholder="请输入用户名" autocomplete="username" @keydown.enter="passwordInput && passwordInput.focus()">
      </div>

      <div class="form-group">
        <label class="form-label" for="password">密码</label>
        <input ref="passwordInput" type="password" id="password" v-model="password" class="form-input" placeholder="请输入密码" autocomplete="current-password" @keydown.enter="handleLogin">
      </div>

      <button class="btn btn-primary" style="width:100%;justify-content:center;" :disabled="loading" @click="handleLogin">
        <AppIcon name="log-in" /><span>{{ loading ? '登录中...' : '登录' }}</span>
      </button>
      <div class="login-version" style="text-align:center;margin-top:16px;font-size:12px;color:var(--ink-muted);">V3.2 考勤管理系统</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import Auth from '../shared/auth';

const router = useRouter();
const username = ref('');
const password = ref('');
const error = ref('');
const loading = ref(false);
const usernameInput = ref(null);
const passwordInput = ref(null);

onMounted(async () => {
  await nextTick();
  if (usernameInput.value) usernameInput.value.focus();
});

async function handleLogin() {
  error.value = '';
  const uname = username.value.trim();
  const pwd = password.value;

  if (!uname || !pwd) {
    error.value = '请输入用户名和密码';
    return;
  }

  loading.value = true;
  const result = await Auth.login(uname, pwd);
  loading.value = false;

  if (result.success) {
    if (result.needChangePassword) {
      sessionStorage.setItem('need_change_password', '1');
      router.push('/setup');
    } else {
      sessionStorage.removeItem('need_change_password');
      router.push('/');
    }
  } else {
    error.value = result.message || '账号或密码错误';
  }
}
</script>
