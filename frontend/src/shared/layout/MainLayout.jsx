import { useEffect, useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';
import authApi from '@/features/auth/api/authApi';
import ROUTES from '@/app/routes/paths';
import './MainLayout.css';

const NAV = [
  { to: ROUTES.DASHBOARD, label: 'Tổng quan' },
  { to: ROUTES.TRANSACTIONS, label: 'Giao dịch' },
  { to: ROUTES.BUDGETS, label: 'Ngân sách' },
  { to: ROUTES.CATEGORIES, label: 'Danh mục' },
];

const useTheme = () => {
  const [theme, setTheme] = useState(() => localStorage.getItem('mm_theme') || 'light');
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('mm_theme', theme);
  }, [theme]);
  return [theme, setTheme];
};

const MainLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [theme, setTheme] = useTheme();
  // Mở sẵn trên màn rộng, thu gọn sẵn trên màn hẹp
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth > 880);

  // Chỉ tự đóng sidebar khi ở màn hẹp (overlay); màn rộng giữ nguyên
  const closeOnMobile = () => {
    if (window.innerWidth <= 880) setSidebarOpen(false);
  };

  const handleLogout = async () => {
    try { await authApi.logout(); } catch { /* ignore */ }
    logout();
    toast.success('Đã đăng xuất');
    navigate(ROUTES.LOGIN);
  };

  const initials = (user?.name || user?.email || 'U').charAt(0).toUpperCase();

  return (
    <div className="shell">
      <aside className={`sidebar ${sidebarOpen ? '' : 'collapsed'}`}>
        <Link to={ROUTES.DASHBOARD} className="brand" onClick={closeOnMobile}>
          <img src="/logo.png" alt="Money Manager" className="brand-logo" />
        </Link>
        <nav className="nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              onClick={closeOnMobile}
            >
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="main">
        <header className="topbar">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen((v) => !v)}
            type="button"
            aria-label={sidebarOpen ? 'Đóng sidebar' : 'Mở sidebar'}
          >
            <span className={`sidebar-toggle__icon ${sidebarOpen ? '' : 'collapsed'}`}>☰</span>
          </button>
          <div className="spacer" />
          <button
            className="sidebar-toggle"
            title="Đổi giao diện sáng/tối"
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
          >
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
          <div className="user-chip">
            <div className="avatar">{initials}</div>
            <div className="user-meta">
              <div className="user-name">{user?.name || 'Người dùng'}</div>
              <div className="user-email faint text-sm">{user?.email}</div>
            </div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={handleLogout}>Đăng xuất</button>
        </header>
        <main className="content">{children}</main>
      </div>

      {sidebarOpen && <div className="nav-backdrop" onClick={() => setSidebarOpen(false)} />}
    </div>
  );
};

export default MainLayout;
