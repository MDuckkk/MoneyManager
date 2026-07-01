import './AuthLayout.css';

const AuthLayout = ({ children }) => (
  <div className="auth-shell">
    <div className="auth-aside">
      <div className="auth-brand">
        <div className="brand-mark">₫</div>
        <span>Money<b>Manager</b></span>
      </div>
      <h1 className="auth-hero-title">Nắm rõ dòng tiền của bạn.</h1>
      <p className="auth-hero-sub">
        Theo dõi thu nhập, chi tiêu và ngân sách hằng tháng — trực quan, gọn gàng,
        và luôn trong tầm kiểm soát.
      </p>
      <ul className="auth-points">
        <li>📊 Tổng quan tài chính theo thời gian thực</li>
        <li>🎯 Đặt ngân sách & cảnh báo khi sắp vượt</li>
        <li>🏷️ Phân loại giao dịch theo danh mục</li>
      </ul>
    </div>
    <div className="auth-main">
      <div className="auth-card">{children}</div>
    </div>
  </div>
);

export default AuthLayout;
