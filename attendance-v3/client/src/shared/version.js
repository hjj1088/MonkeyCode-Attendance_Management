// 版本号展示统一格式：version_name + patch 号（如 V3.3.2）
export function formatVersion(v) {
  if (!v || (!v.version_name && !v.app_version)) return '';
  const base = v.version_name || ('V' + v.app_version);
  const patch = String(v.app_version || '').split('.')[2] || '';
  return patch ? base + '.' + patch : base;
}
