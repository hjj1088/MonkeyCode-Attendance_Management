<template>
  <div class="login-page">
    <div class="login-card">
      <div class="flex-center mb-md">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--vermillion)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
      </div>
      <h1>设置管理员密码</h1>
      <p class="subtitle">检测到管理员仍在使用默认密码，请立即修改</p>

      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="success" class="alert" style="background:rgba(45,125,70,0.06);color:var(--jade);border:1px solid rgba(45,125,70,0.15);">{{ success }}</div>

      <div class="form-group">
        <label class="form-label">当前密码</label>
        <input type="password" v-model="oldPassword" class="form-input" placeholder="请输入当前密码" autocomplete="current-password">
      </div>

      <div class="form-group">
        <label class="form-label">新密码</label>
        <input type="password" v-model="newPassword" class="form-input" placeholder="至少 6 位" autocomplete="new-password">
      </div>

      <div class="form-group">
        <label class="form-label">确认新密码</label>
        <input type="password" v-model="confirmPassword" class="form-input" placeholder="再次输入新密码" autocomplete="new-password" @keydown.enter="submit">
      </div>

      <button class="btn btn-primary" style="width:100%;justify-content:center;" :disabled="loading" @click="submit">
        {{ loading ? '提交中...' : '确认修改' }}
      </button>
      <button class="btn btn-ghost" style="width:100%;justify-content:center;margin-top:8px;" @click="skip">暂不修改，先进入系统</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { apiRequest } from '../shared/api';
import Auth from '../shared/auth';

const router = useRouter();
const oldPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const error = ref('');
const success = ref('');
const loading = ref(false);

async function submit() {
  error.value = '';
  success.value = '';
  if (!oldPassword.value || !newPassword.value) {
    error.value = '请输入当前密码和新密码';
    return;
  }
  if (newPassword.value.length < 6) {
    error.value = '新密码长度不能少于 6 位';
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次输入的新密码不一致';
    return;
  }

  loading.value = true;
  try {
    await apiRequest('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password: oldPassword.value, new_password: newPassword.value }),
    });
    success.value = '密码修改成功';
    sessionStorage.removeItem('need_change_password');
    setTimeout(() => router.push('/'), 800);
  } catch (err) {
    error.value = err.message || '密码修改失败';
  }
  loading.value = false;
}

function skip() {
  sessionStorage.removeItem('need_change_password');
  router.push('/');
}
</script>
