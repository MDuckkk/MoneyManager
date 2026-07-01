import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';
import ROUTES from '@/app/routes/paths';
import { Spinner } from '@/shared/ui';
import authApi from '../api/authApi';
import './auth.css';

const LoginPage = () => {
  const { login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const onChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await authApi.login(form);
      const { user, accessToken, refreshToken } = res.data;
      login(user, accessToken, refreshToken);
      toast.success(`Chào mừng trở lại, ${user.name || user.email}!`);
      navigate(ROUTES.DASHBOARD);
    } catch (err) {
      setError(err.message || 'Đăng nhập thất bại');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-up">
      <div className="auth-form-head">
        <div className="auth-form-title">Đăng nhập</div>
        <div className="auth-form-sub">Tiếp tục quản lý chi tiêu của bạn</div>
      </div>

      <form className="auth-form" onSubmit={onSubmit}>
        {error && <div className="auth-error">{error}</div>}
        <div className="field">
          <label className="label">Email</label>
          <input
            className="input"
            type="email"
            name="email"
            value={form.email}
            onChange={onChange}
            placeholder="ban@email.com"
            required
          />
        </div>
        <div className="field">
          <label className="label">Mật khẩu</label>
          <input
            className="input"
            type="password"
            name="password"
            value={form.password}
            onChange={onChange}
            placeholder="••••••••"
            required
          />
        </div>
        <button className="btn btn-primary btn-block" disabled={loading}>
          {loading ? <Spinner /> : 'Đăng nhập'}
        </button>
      </form>

      <div className="auth-switch">
        Chưa có tài khoản? <Link to={ROUTES.REGISTER}>Đăng ký ngay</Link>
      </div>
    </div>
  );
};

export default LoginPage;
