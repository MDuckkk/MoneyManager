import './AuthLayout.css';

// Các ký hiệu tiền tệ trôi lên tạo cảm giác "dòng tiền"
const FLOATERS = ['₫', '$', '€', '¥', '₫', '£', '$', '₫', '€', '$'];

const AuthLayout = ({ children }) => (
  <div className="auth-shell">
    <div className="auth-aside">
      {/* Nền động: dòng tiền chảy */}
      <div className="auth-fx" aria-hidden="true">
        {FLOATERS.map((s, i) => (
          <span key={i} className={`auth-coin auth-coin-${i}`}>{s}</span>
        ))}
        <svg className="auth-flow" viewBox="0 0 400 140" preserveAspectRatio="none">
          <defs>
            <linearGradient id="flowStroke" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="rgba(255,255,255,0.15)" />
              <stop offset="50%" stopColor="rgba(255,255,255,0.85)" />
              <stop offset="100%" stopColor="rgba(255,255,255,0.15)" />
            </linearGradient>
          </defs>
          <polyline
            className="auth-flow-line"
            points="0,110 44,96 90,104 140,70 188,82 236,44 288,58 336,26 400,20"
          />
        </svg>
      </div>

      <div className="auth-brand">
        <img src="/logo.png" alt="Money Manager" className="auth-logo" />
      </div>

      <div className="auth-hero">
        <h1 className="auth-hero-title">Nắm rõ dòng tiền của bạn.</h1>
        <p className="auth-hero-sub">
          Theo dõi thu chi, đặt ngân sách và xem báo cáo trực quan — tất cả trong một nơi.
        </p>
      </div>

      <ul className="auth-list">
        <li>Theo dõi thu chi hằng ngày</li>
        <li>Đặt ngân sách theo từng tháng</li>
        <li>Báo cáo trực quan, dễ nhìn</li>
      </ul>
    </div>

    <div className="auth-main">
      <div className="auth-main-inner">
        <div className="auth-card">{children}</div>
      </div>
      <footer className="auth-foot">© 2026 Money Manager — Quản lý chi tiêu cá nhân</footer>
    </div>
  </div>
);

export default AuthLayout;
