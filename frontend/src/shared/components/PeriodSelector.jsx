import { MONTH_NAMES } from '@/shared/utils/formatters';
import './PeriodSelector.css';

const YEARS = (() => {
  const y = new Date().getFullYear();
  return [y - 2, y - 1, y, y + 1];
})();

const PeriodSelector = ({ month, year, onChange }) => {
  const shift = (delta) => {
    let m = month + delta;
    let y = year;
    if (m < 1) { m = 12; y -= 1; }
    if (m > 12) { m = 1; y += 1; }
    onChange({ month: m, year: y });
  };

  return (
    <div className="period">
      <button className="btn btn-icon btn-ghost btn-sm" onClick={() => shift(-1)} aria-label="Tháng trước">‹</button>
      <select
        className="select period-select"
        value={month}
        onChange={(e) => onChange({ month: Number(e.target.value), year })}
      >
        {MONTH_NAMES.map((name, i) => (
          <option key={i} value={i + 1}>{name}</option>
        ))}
      </select>
      <select
        className="select period-select"
        value={year}
        onChange={(e) => onChange({ month, year: Number(e.target.value) })}
      >
        {YEARS.map((y) => (
          <option key={y} value={y}>{y}</option>
        ))}
      </select>
      <button className="btn btn-icon btn-ghost btn-sm" onClick={() => shift(1)} aria-label="Tháng sau">›</button>
    </div>
  );
};

export default PeriodSelector;
