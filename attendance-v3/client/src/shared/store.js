// shared/store.js
// Store 接口 - 与 V3.1 api-store.js 相同语义，转调后端 /api/store/*

import { apiRequest } from './api';

const Store = {
  _clean(value) {
    return JSON.parse(JSON.stringify(value));
  },

  async bulkPut(tableName, records) {
    if (!records || records.length === 0) return 0;
    const data = await apiRequest('/store/' + tableName + '/bulk', {
      method: 'POST',
      body: JSON.stringify({ records: this._clean(records) }),
    });
    return data.count;
  },

  async clearTable(tableName) {
    await apiRequest('/store/' + tableName, { method: 'DELETE' });
  },

  async getAll(tableName) {
    return await apiRequest('/store/' + tableName);
  },

  async getByIndex(tableName, indexName, value) {
    if (value === undefined || value === null) return [];
    return await apiRequest(
      '/store/' + tableName + '?index=' + encodeURIComponent(indexName) + '&value=' + encodeURIComponent(value)
    );
  },

  async getByRange(tableName, indexName, lower, upper) {
    return await apiRequest(
      '/store/' + tableName + '/range?index=' + encodeURIComponent(indexName) + '&lower=' + encodeURIComponent(lower) + '&upper=' + encodeURIComponent(upper)
    );
  },

  async getByKey(tableName, key) {
    return await apiRequest('/store/' + tableName + '/' + encodeURIComponent(key));
  },

  async put(tableName, record) {
    await apiRequest('/store/' + tableName, {
      method: 'POST',
      body: JSON.stringify({ record: this._clean(record) }),
    });
  },

  async deleteByKey(tableName, key) {
    await apiRequest('/store/' + tableName + '/' + encodeURIComponent(key), { method: 'DELETE' });
  },

  async resetAllData() {
    await apiRequest('/store/reset', { method: 'POST' });
  },
};

export default Store;
