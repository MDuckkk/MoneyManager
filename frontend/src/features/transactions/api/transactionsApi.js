import { BaseApi } from '@/core';

class TransactionsApi extends BaseApi {
  constructor() {
    super('/transactions');
  }

  list(params = {}) {
    return this.query(params);
  }
  createTransaction(payload) {
    return this.post('', payload);
  }
  updateTransaction(id, payload) {
    return this.patch(`/${id}`, payload);
  }
  deleteTransaction(id) {
    return this.delete(`/${id}`);
  }
}

export default new TransactionsApi();
