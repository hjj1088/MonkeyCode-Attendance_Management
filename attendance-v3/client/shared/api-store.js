// shared/api-store.js V3.1
// Store API - replaces IndexedDB/Dexie with REST API backend
// Same interface as V2.0 db.js Store object

const API_BASE = '/api';

function _request(path, options = {}) {
  const token = sessionStorage.getItem('token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: 'Bearer ' + token } : {}),
    ...options.headers,
  };

  const url = API_BASE + path;
  const fetchOptions = { ...options, headers };

  return fetch(url, fetchOptions).then(async (res) => {
    if (res.status === 401) {
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('user');
      window.location.href = 'index.html';
      throw new Error('Unauthorized');
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.message || 'Request failed');
    }
    const body = await res.json();
    if (body.code !== 0) {
      throw new Error(body.message || 'API error');
    }
    return body.data;
  });
}

const Store = {
  _clean(value) {
    return JSON.parse(JSON.stringify(value));
  },

  async bulkPut(tableName, records) {
    if (!records || records.length === 0) return 0;
    const data = await _request('/store/' + tableName + '/bulk', {
      method: 'POST',
      body: JSON.stringify({ records: this._clean(records) }),
    });
    return data.count;
  },

  async clearTable(tableName) {
    await _request('/store/' + tableName, { method: 'DELETE' });
  },

  async getAll(tableName) {
    return await _request('/store/' + tableName);
  },

  async getByIndex(tableName, indexName, value) {
    if (value === undefined || value === null) return [];
    return await _request('/store/' + tableName + '?index=' + encodeURIComponent(indexName) + '&value=' + encodeURIComponent(value));
  },

  async getByRange(tableName, indexName, lower, upper) {
    return await _request('/store/' + tableName + '/range?index=' + encodeURIComponent(indexName) + '&lower=' + encodeURIComponent(lower) + '&upper=' + encodeURIComponent(upper));
  },

  async getByKey(tableName, key) {
    return await _request('/store/' + tableName + '/' + encodeURIComponent(key));
  },

  async put(tableName, record) {
    await _request('/store/' + tableName, {
      method: 'POST',
      body: JSON.stringify({ record: this._clean(record) }),
    });
  },

  async deleteByKey(tableName, key) {
    await _request('/store/' + tableName + '/' + encodeURIComponent(key), { method: 'DELETE' });
  },

  async resetAllData() {
    await _request('/store/reset', { method: 'POST' });
  },
};

// Initialize default settings on first load
Store.getByKey('settings', 'attendance_config').then(config => {
  if (!config) {
    Store.put('settings', {
      key: 'attendance_config',
      value: {
        workStartTime: '08:30',
        workEndTime: '17:30',
        lateThreshold: 0,
        earlyThreshold: 0,
        graceTimes: 2,
        graceMinutes: 30,
      },
    });
  }
});
