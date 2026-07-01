import { useCallback, useEffect, useMemo, useState } from 'react';
import { useToast } from '@/contexts/ToastContext';
import PageHeader from '@/shared/components/PageHeader';
import PeriodSelector from '@/shared/components/PeriodSelector';
import { SpinnerCenter, EmptyState, ConfirmDialog } from '@/shared/ui';
import {
  money, signedMoney, dateGroupLabel, currentPeriod,
} from '@/shared/utils/formatters';
import { colorFor, CATEGORY_TYPE_LABEL } from '@/shared/utils/constants';
import transactionsApi from '../api/transactionsApi';
import categoriesApi from '@/features/categories/api/categoriesApi';
import TransactionFormModal from '../components/TransactionFormModal';
import './TransactionsPage.css';

const groupByDate = (rows) => {
  const groups = [];
  const map = new Map();
  for (const row of rows) {
    const key = row.occurredAt?.slice(0, 10);
    if (!map.has(key)) {
      const g = { key, label: dateGroupLabel(key), items: [], total: 0 };
      map.set(key, g);
      groups.push(g);
    }
    const g = map.get(key);
    g.items.push(row);
    g.total += row.type === 'INCOME' ? Number(row.amount) : -Number(row.amount);
  }
  return groups;
};

const TransactionsPage = () => {
  const toast = useToast();
  const [period, setPeriod] = useState(currentPeriod);
  const [filters, setFilters] = useState({ type: '', categoryId: '', search: '' });
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ rows: [], meta: null });
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    categoriesApi.list().then((r) => setCategories(r.data || [])).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await transactionsApi.list({
        ...period,
        type: filters.type || undefined,
        categoryId: filters.categoryId || undefined,
        search: filters.search || undefined,
        page,
        limit: 20,
      });
      setData({ rows: res.data || [], meta: res.meta });
    } catch (err) {
      toast.error(err.message || 'Không tải được giao dịch');
    } finally {
      setLoading(false);
    }
  }, [period, filters, page, toast]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setPage(1); }, [period, filters]);

  const groups = useMemo(() => groupByDate(data.rows), [data.rows]);

  const handleSubmit = async (payload) => {
    if (editing) {
      await transactionsApi.updateTransaction(editing.id, payload);
      toast.success('Đã cập nhật giao dịch');
    } else {
      await transactionsApi.createTransaction(payload);
      toast.success('Đã thêm giao dịch');
    }
    load();
  };

  const confirmDelete = async () => {
    try {
      await transactionsApi.deleteTransaction(deleting.id);
      toast.success('Đã xóa giao dịch');
      setDeleting(null);
      load();
    } catch (err) {
      toast.error(err.message || 'Xóa thất bại');
    }
  };

  const openAdd = () => { setEditing(null); setModalOpen(true); };
  const openEdit = (tx) => { setEditing(tx); setModalOpen(true); };

  return (
    <div>
      <PageHeader
        title="Giao dịch"
        subtitle="Ghi lại và theo dõi mọi khoản thu chi"
        actions={
          <>
            <PeriodSelector month={period.month} year={period.year} onChange={setPeriod} />
            <button className="btn btn-primary" onClick={openAdd}>+ Thêm giao dịch</button>
          </>
        }
      />

      <div className="card filter-bar">
        <div className="filter-search">
          <svg className="filter-search__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            className="input filter-search__input"
            placeholder="Tìm theo ghi chú..."
            value={filters.search}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
          />
          {filters.search && (
            <button
              type="button"
              className="filter-search__clear"
              title="Xóa tìm kiếm"
              onClick={() => setFilters((f) => ({ ...f, search: '' }))}
            >
              ×
            </button>
          )}
        </div>
        <select className="select" value={filters.type}
          onChange={(e) => setFilters((f) => ({ ...f, type: e.target.value, categoryId: '' }))}>
          <option value="">Tất cả loại</option>
          <option value="INCOME">{CATEGORY_TYPE_LABEL.INCOME}</option>
          <option value="EXPENSE">{CATEGORY_TYPE_LABEL.EXPENSE}</option>
        </select>
        <select className="select" value={filters.categoryId}
          onChange={(e) => setFilters((f) => ({ ...f, categoryId: e.target.value }))}>
          <option value="">Tất cả danh mục</option>
          {categories
            .filter((c) => !filters.type || c.type === filters.type)
            .map((c) => <option key={c.id} value={c.id}>{c.icon} {c.name}</option>)}
        </select>
      </div>

      {loading ? (
        <SpinnerCenter />
      ) : groups.length === 0 ? (
        <div className="card">
          <EmptyState emoji="🧾" title="Không có giao dịch"
            subtitle="Chưa có giao dịch nào khớp bộ lọc. Thêm giao dịch đầu tiên của bạn."
            action={<button className="btn btn-primary btn-sm" onClick={openAdd}>+ Thêm giao dịch</button>} />
        </div>
      ) : (
        <div className="tx-groups fade-up">
          {groups.map((g) => (
            <div className="tx-group card" key={g.key}>
              <div className="tx-group-head">
                <span className="tx-group-date">{g.label}</span>
              </div>
              {g.items.map((t) => (
                <div className="tx-row" key={t.id}>
                  <span className="tx-icon" style={{ background: `${colorFor(t.category?.color)}22` }}>
                    {t.category?.icon || '💸'}
                  </span>
                  <div className="tx-main">
                    <div className="tx-name">{t.category?.name}</div>
                    <div className="tx-note faint text-sm">{t.note || '—'}</div>
                  </div>
                  <div className={`num tx-amount ${t.type === 'INCOME' ? 'amount-income' : ''}`}>
                    {signedMoney(t.amount, t.type)}
                  </div>
                  <div className="tx-actions">
                    <button className="btn btn-icon btn-ghost btn-sm" onClick={() => openEdit(t)} title="Sửa">✏️</button>
                    <button className="btn btn-icon btn-ghost btn-sm" onClick={() => setDeleting(t)} title="Xóa">🗑️</button>
                  </div>
                </div>
              ))}
            </div>
          ))}

          {data.meta && data.meta.totalPages > 1 && (
            <div className="pager">
              <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>‹ Trước</button>
              <span className="text-sm muted">Trang {data.meta.page}/{data.meta.totalPages}</span>
              <button className="btn btn-ghost btn-sm" disabled={page >= data.meta.totalPages} onClick={() => setPage((p) => p + 1)}>Sau ›</button>
            </div>
          )}
        </div>
      )}

      <TransactionFormModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
        categories={categories}
        editing={editing}
      />
      <ConfirmDialog
        open={Boolean(deleting)}
        message={`Xóa giao dịch "${deleting?.category?.name}" (${deleting ? money(deleting.amount) : ''})?`}
        onConfirm={confirmDelete}
        onClose={() => setDeleting(null)}
      />
    </div>
  );
};

export default TransactionsPage;
