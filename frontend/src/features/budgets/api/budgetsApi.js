import { BaseApi } from '@/core';

class BudgetsApi extends BaseApi {
  constructor() {
    super('/budgets');
  }

  list(params = {}) {
    return this.query(params);
  }
  status(params = {}) {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null)),
    ).toString();
    return this.get(`/status${qs ? `?${qs}` : ''}`);
  }
  createBudget(payload) {
    return this.post('', payload);
  }
  updateBudget(id, payload) {
    return this.patch(`/${id}`, payload);
  }
  deleteBudget(id) {
    return this.delete(`/${id}`);
  }
}

export default new BudgetsApi();
