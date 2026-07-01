import { BaseApi } from '@/core';

class CategoriesApi extends BaseApi {
  constructor() {
    super('/categories');
  }

  list(params = {}) {
    return this.query(params);
  }
  createCategory(payload) {
    return this.post('', payload);
  }
  updateCategory(id, payload) {
    return this.patch(`/${id}`, payload);
  }
  deleteCategory(id) {
    return this.delete(`/${id}`);
  }
}

export default new CategoriesApi();
