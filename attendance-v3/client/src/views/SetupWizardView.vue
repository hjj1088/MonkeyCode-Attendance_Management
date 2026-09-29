<template>
  <div class="login-page">
    <div class="login-card">
      <div class="flex-center mb-md">
        <div class="sidebar-logo" style="width:48px;height:48px;font-size:26px" aria-hidden="true">勤</div>
      </div>
      <h1>设置管理员密码</h1>
      <p class="subtitle">检测到管理员仍在使用默认密码，请立即修改</p>

      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="success" class="alert alert-success">{{ success }}</div>

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
        <AppIcon name="key" /><span>{{ loading ? '提交中...' : '确认修改' }}</span>
      </button>
      <button class="btn btn-ghost" style="width:100%;justify-content:center;margin-top:8px;" @click="skip"><AppIcon name="skip" /><span>暂不修改，先进入系统</span></button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
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
