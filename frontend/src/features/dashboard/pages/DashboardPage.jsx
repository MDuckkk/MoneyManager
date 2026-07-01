import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';
import { useToast } from '@/contexts/ToastContext';
import PageHeader from '@/shared/components/PageHeader';
import PeriodSelector from '@/shared/components/PeriodSelector';
import { SpinnerCenter, EmptyState } from '@/shared/ui';
import useCountUp from '@/shared/hooks/useCountUp';
import { money, signedMoney, formatDate, currentPeriod, MONTH_NAMES } from '@/shared/utils/formatters';
import { colorFor, BUDGET_STATUS_CLASS } from '@/shared/utils/constants';
import ROUTES from '@/app/routes/paths';
import reportsApi from '../api/dashboardApi';
import budgetsApi from '@/features/budgets/api/budgetsApi';
import transactionsApi from '@/features/transactions/api/transactionsApi';
import './DashboardPage.css';

const KpiCard = ({ label, value, accent, deltaPct, deltaInverse, delay }) => {
  const animated = useCountUp(value);
  let deltaText = null;
  let deltaClass = 'flat';
  if (deltaPct !== null && deltaPct !== undefined) {
    const up = deltaPct >= 0;
    const good = deltaInverse ? !up : up;
    deltaClass = good ? 'good' : 'bad';
    deltaText = `${up ? '↑' : '↓'} ${Math.abs(deltaPct)}% so với tháng trước`;
  }
  return (
    <div className={`kpi card fade-up ${delay}`}>
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value num ${accent}`}>{money(Math.round(animated))}</div>
      {deltaText && <div className={`kpi-delta ${deltaClass}`}>{deltaText}</div>}
    </div>
  );
};

const DashboardPage = () => {
  const toast = useToast();
  const [period, setPeriod] = useState(currentPeriod);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [donut, setDonut] = useState([]);
  const [budgets, setBudgets] = useState([]);
  const [recent, setRecent] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, c, b, t] = await Promise.all([
        reportsApi.summary(period),
        reportsApi.byCategory({ ...period, type: 'EXPENSE' }),
        budgetsApi.status(period),
        transactionsApi.list({ ...period, page: 1, limit: 5 }),
      ]);
      setSummary(s.data);
      setDonut(c.data.items || []);
      setBudgets(b.data.items || []);
      setRecent(t.data || []);
    } catch (err) {
      toast.error(err.message || 'Không tải được tổng quan');
    } finally {
      setLoading(false);
    }
  }, [period, toast]);

  useEffect(() => { load(); }, [load]);

  const barData = summary
    ? [
        { name: 'Tháng trước', 'Thu nhập': summary.previousMonth.income, 'Chi tiêu': summary.previousMonth.expense },
        { name: MONTH_NAMES[period.month - 1], 'Thu nhập': summary.income, 'Chi tiêu': summary.expense },
      ]
    : [];

  return (
    <div>
      <PageHeader
        title="Tổng quan"
        subtitle="Bức tranh tài chính của bạn trong tháng"
        actions={<PeriodSelector month={period.month} year={period.year} onChange={setPeriod} />}
      />

      {loading ? (
        <SpinnerCenter />
      ) : (
        <>
          <div className="kpi-grid">
            <KpiCard label="Thu nhập" value={summary.income} accent="amount-income"
              deltaPct={summary.incomeChangePct} delay="fade-up-1" />
            <KpiCard label="Chi tiêu" value={summary.expense} accent="kpi-expense"
              deltaPct={summary.expenseChangePct} deltaInverse delay="fade-up-2" />
            <KpiCard label="Số dư" value={summary.balance}
              accent={summary.balance >= 0 ? 'amount-income' : 'kpi-expense'} delay="fade-up-3" />
          </div>

          <div className="dash-grid">
            {/* Donut: cơ cấu chi tiêu */}
            <div className="card fade-up fade-up-2">
              <div className="card-header">
                <div className="card-title">Cơ cấu chi tiêu</div>
                <div className="card-subtitle num">{money(donut.reduce((s, i) => s + i.total, 0), { compact: true })}</div>
              </div>
              <div className="card-pad">
                {donut.length === 0 ? (
                  <EmptyState emoji="🍃" title="Chưa có chi tiêu" subtitle="Thêm giao dịch để xem cơ cấu." />
                ) : (
                  <div className="donut-wrap">
                    <div className="donut-chart">
                      <ResponsiveContainer width="100%" height={220}>
                        <PieChart>
                          <Pie data={donut} dataKey="total" nameKey="categoryName"
                            innerRadius={62} outerRadius={92} paddingAngle={2} stroke="none">
                            {donut.map((d, i) => (
                              <Cell key={d.categoryId} fill={colorFor(d.color, i)} />
                            ))}
                          </Pie>
                          <Tooltip formatter={(v) => money(v)} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <ul className="donut-legend">
                      {donut.slice(0, 6).map((d, i) => (
                        <li key={d.categoryId}>
                          <span className="chip-dot" style={{ background: colorFor(d.color, i) }} />
                          <span className="legend-name">{d.icon} {d.categoryName}</span>
                          <span className="legend-val num">{money(d.total, { compact: true })}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* Bar: thu/chi so với tháng trước */}
            <div className="card fade-up fade-up-3">
              <div className="card-header">
                <div className="card-title">Thu & chi theo tháng</div>
              </div>
              <div className="card-pad">
                <ResponsiveContainer width="100%" height={244}>
                  <BarChart data={barData} barGap={8}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                    <YAxis tickFormatter={(v) => money(v, { compact: true })} tick={{ fontSize: 11, fill: 'var(--text-faint)' }} axisLine={false} tickLine={false} width={56} />
                    <Tooltip formatter={(v) => money(v)} cursor={{ fill: 'var(--surface-2)' }} />
                    <Bar dataKey="Thu nhập" fill="var(--income)" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="Chi tiêu" fill="var(--brand)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Budget progress */}
            <div className="card fade-up fade-up-3">
              <div className="card-header">
                <div className="card-title">Tiến độ ngân sách</div>
                <Link to={ROUTES.BUDGETS} className="card-subtitle link-more">Xem tất cả →</Link>
              </div>
              <div className="card-pad">
                {budgets.length === 0 ? (
                  <EmptyState emoji="🎯" title="Chưa đặt ngân sách"
                    subtitle="Đặt hạn mức để theo dõi chi tiêu."
                    action={<Link to={ROUTES.BUDGETS} className="btn btn-ghost btn-sm">Đặt ngân sách</Link>} />
                ) : (
                  <div className="budget-list">
                    {budgets.slice(0, 4).map((b) => (
                      <div key={b.budgetId} className="budget-row">
                        <div className="budget-top">
                          <span className="budget-name">{b.icon} {b.categoryName}</span>
                          <span className="num text-sm muted">{money(b.spent, { compact: true })} / {money(b.limit, { compact: true })}</span>
                        </div>
                        <div className="progress">
                          <div className={`progress-fill ${BUDGET_STATUS_CLASS[b.status]}`}
                            style={{ width: `${Math.min(b.percentage, 100)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Recent transactions */}
            <div className="card fade-up fade-up-4">
              <div className="card-header">
                <div className="card-title">Giao dịch gần đây</div>
                <Link to={ROUTES.TRANSACTIONS} className="card-subtitle link-more">Xem tất cả →</Link>
              </div>
              <div className="card-pad">
                {recent.length === 0 ? (
                  <EmptyState emoji="🧾" title="Chưa có giao dịch"
                    subtitle="Bắt đầu ghi lại thu chi của bạn."
                    action={<Link to={ROUTES.TRANSACTIONS} className="btn btn-primary btn-sm">Thêm giao dịch</Link>} />
                ) : (
                  <div className="recent-list">
                    {recent.map((t) => (
                      <div key={t.id} className="recent-row">
                        <span className="recent-icon" style={{ background: `${colorFor(t.category?.color)}22` }}>
                          {t.category?.icon || '💸'}
                        </span>
                        <div className="recent-main">
                          <div className="recent-name">{t.category?.name}</div>
                          <div className="recent-sub faint text-sm">{t.note || '—'} · {formatDate(t.occurredAt)}</div>
                        </div>
                        <div className={`num tx-amount ${t.type === 'INCOME' ? 'amount-income' : ''}`}>
                          {signedMoney(t.amount, t.type)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default DashboardPage;
