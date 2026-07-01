/**
 * BaseApi — lớp cơ sở cho mọi API service (CRUD + xây URL theo endpoint).
 */
import axiosInstance from './axios';

class BaseApi {
  constructor(endpoint) {
    this.endpoint = endpoint;
  }

  async get(url = '', config = {}) {
    const { data } = await axiosInstance.get(`${this.endpoint}${url}`, config);
    return data;
  }
  async post(url = '', body = {}, config = {}) {
    const { data } = await axiosInstance.post(`${this.endpoint}${url}`, body, config);
    return data;
  }
  async patch(url = '', body = {}, config = {}) {
    const { data } = await axiosInstance.patch(`${this.endpoint}${url}`, body, config);
    return data;
  }
  async delete(url = '', config = {}) {
    const { data } = await axiosInstance.delete(`${this.endpoint}${url}`, config);
    return data;
  }

  query(params = {}) {
    const clean = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
    );
    const qs = new URLSearchParams(clean).toString();
    return this.get(qs ? `?${qs}` : '');
  }
}

export default BaseApi;
