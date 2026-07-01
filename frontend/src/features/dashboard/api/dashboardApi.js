import { BaseApi } from '@/core';

class ReportsApi extends BaseApi {
  constructor() {
    super('/reports');
  }

  summary(params = {}) {
    const qs = this.toQuery(params);
    return this.get(`/summary${qs}`);
  }
  byCategory(params = {}) {
    const qs = this.toQuery(params);
    return this.get(`/by-category${qs}`);
  }

  toQuery(params) {
    const clean = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v != null && v !== ''),
    );
    const qs = new URLSearchParams(clean).toString();
    return qs ? `?${qs}` : '';
  }
}

export default new ReportsApi();
