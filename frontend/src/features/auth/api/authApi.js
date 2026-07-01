import { BaseApi } from '@/core';

class AuthApi extends BaseApi {
  constructor() {
    super('/auth');
  }

  register(payload) {
    return this.post('/register', payload);
  }
  login(payload) {
    return this.post('/login', payload);
  }
  logout() {
    return this.post('/logout');
  }
  me() {
    return this.get('/me');
  }
}

export default new AuthApi();
