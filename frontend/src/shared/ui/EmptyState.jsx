import './ui.css';

const EmptyState = ({ emoji = '📭', title = 'Chưa có dữ liệu', subtitle, action }) => (
  <div className="empty">
    <div className="empty-emoji">{emoji}</div>
    <div className="empty-title">{title}</div>
    {subtitle && <div className="empty-sub">{subtitle}</div>}
    {action}
  </div>
);

export default EmptyState;
