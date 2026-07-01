/** Định dạng tiền tệ VND. compact=true → "12,4 Tr". */
export const money = (value, { compact = false } = {}) => {
  const n = Number(value || 0);
  if (compact && Math.abs(n) >= 1_000_000)
    return `${(n / 1_000_000).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} Tr`;
  if (compact && Math.abs(n) >= 1_000)
    return `${(n / 1_000).toLocaleString('vi-VN', { maximumFractionDigits: 0 })}K`;
  return n.toLocaleString('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 });
};

/** Số có dấu +/- cho thu/chi. */
export const signedMoney = (value, type) => {
  const sign = type === 'INCOME' ? '+' : '−';
  return `${sign}${money(Math.abs(Number(value || 0)))}`;
};

/** ISO date → "DD/MM/YYYY". */
export const formatDate = (value) => {
  if (!value) return '-';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString('vi-VN');
};

/** Nhãn nhóm ngày: Hôm nay / Hôm qua / DD/MM/YYYY. */
export const dateGroupLabel = (value) => {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  const same = (a, b) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  if (same(d, today)) return 'Hôm nay';
  if (same(d, yesterday)) return 'Hôm qua';
  return d.toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' });
};

export const MONTH_NAMES = [
  'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
  'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12',
];

/** {month, year} của hôm nay (month 1-12). */
export const currentPeriod = () => {
  const now = new Date();
  return { month: now.getMonth() + 1, year: now.getFullYear() };
};

/** "YYYY-MM-DD" của hôm nay (cho input date). */
export const todayInput = () => new Date().toISOString().slice(0, 10);
