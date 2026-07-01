import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';
import ROUTES from '@/app/routes/paths';
import { Spinner } from '@/shared/ui';
import authApi from '../api/authApi';
import './auth.css';

const RegisterPage = () => {
  const { login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const onChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.password.length < 6) {
      setError('Mật khẩu phải có ít nhất 6 ký tự');
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.register(form);
      const { user, accessToken, refreshToken } = res.data;
      login(user, accessToken, refreshToken);
      toast.success('Tạo tài khoản thành công!');
      navigate(ROUTES.DASHBOARD);
    } catch (err) {
      setError(err.message || 'Đăng ký thất bại');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-up">
      <div className="auth-form-head">
        <div className="auth-form-title">Tạo tài khoản</div>
        <div className="auth-form-sub">Bắt đầu kiểm soát tài chính cá nhân</div>
      </div>

      <form className="auth-form" onSubmit={onSubmit}>
        {error && <div className="auth-error">{error}</div>}
        <div className="field">
          <label className="label">Tên hiển thị</label>
          <input className="input" name="name" value={form.name} onChange={onChange} placeholder="Nguyễn Văn A" />
        </div>
        <div className="field">
          <label className="label">Email</label>
          <input className="input" type="email" name="email" value={form.email} onChange={onChange} placeholder="ban@email.com" required />
        </div>
        <div className="field">
          <label className="label">Mật khẩu</label>
          <input className="input" type="password" name="password" value={form.password} onChange={onChange} placeholder="Tối thiểu 6 ký tự" required />
        </div>
        <button className="btn btn-primary btn-block" disabled={loading}>
          {loading ? <Spinner /> : 'Đăng ký'}
        </button>
      </form>

      <div className="auth-switch">
        Đã có tài khoản? <Link to={ROUTES.LOGIN}>Đăng nhập</Link>
      </div>
    </div>
  );
};

export default RegisterPage;
