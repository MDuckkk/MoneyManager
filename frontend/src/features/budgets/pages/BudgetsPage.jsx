import { useCallback, useEffect, useState } from 'react';
import { useToast } from '@/contexts/ToastContext';
import PageHeader from '@/shared/components/PageHeader';
import PeriodSelector from '@/shared/components/PeriodSelector';
import { SpinnerCenter, EmptyState, Modal, ConfirmDialog, Spinner } from '@/shared/ui';
import { money, currentPeriod } from '@/shared/utils/formatters';
import { BUDGET_STATUS_CLASS, BUDGET_STATUS_LABEL } from '@/shared/utils/constants';
import budgetsApi from '../api/budgetsApi';
import categoriesApi from '@/features/categories/api/categoriesApi';
import './BudgetsPage.css';

const statusBadgeClass = { SAFE: 'badge-safe', WARNING: 'badge-warning', EXCEEDED: 'badge-exceeded' };

const BudgetsPage = () => {
  const toast = useToast();
  const [period, setPeriod] = useState(currentPeriod);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ categoryId: '', limitAmount: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    categoriesApi.list({ type: 'EXPENSE' }).then((r) => setCategories(r.data || [])).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await budgetsApi.status(period);
      setItems(res.data.items || []);
    } catch (err) {
      toast.error(err.message || 'Không tải được ngân sách');
    } finally {
      setLoading(false);
    }
  }, [period, toast]);

  useEffect(() => { load(); }, [load]);

  const openAdd = () => {
    setEditing(null);
    setForm({ categoryId: '', limitAmount: '' });
    setError('');
    setModalOpen(true);
  };
  const openEdit = (item) => {
    setEditing(item);
    setForm({ categoryId: String(item.categoryId), limitAmount: String(item.limit) });
    setError('');
    setModalOpen(true);
  };

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (!editing && !form.categoryId) return setError('Vui lòng chọn danh mục');
    if (!(Number(form.limitAmount) > 0)) return setError('Hạn mức phải lớn hơn 0');
    setSaving(true);
    try {
      if (editing) {
        await budgetsApi.updateBudget(editing.budgetId, { limitAmount: Number(form.limitAmount) });
        toast.success('Đã cập nhật ngân sách');
      } else {
        await budgetsApi.createBudget({
          categoryId: Number(form.categoryId),
          month: period.month,
          year: period.year,
          limitAmount: Number(form.limitAmount),
        });
        toast.success('Đã tạo ngân sách');
      }
      setModalOpen(false);
      load();
    } catch (err) {
      setError(err.message || 'Lưu thất bại');
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    try {
      await budgetsApi.deleteBudget(deleting.budgetId);
      toast.success('Đã xóa ngân sách');
      setDeleting(null);
      load();
    } catch (err) {
      toast.error(err.message || 'Xóa thất bại');
    }
  };

  const totalLimit = items.reduce((s, i) => s + i.limit, 0);
  const totalSpent = items.reduce((s, i) => s + i.spent, 0);
  const usedCategoryIds = new Set(items.map((i) => i.categoryId));
  const availableCategories = categories.filter((c) => !usedCategoryIds.has(c.id));

  return (
    <div>
      <PageHeader
        title="Ngân sách"
        subtitle="Đặt hạn mức chi tiêu và theo dõi tiến độ theo tháng"
        actions={
          <>
            <PeriodSelector month={period.month} year={period.year} onChange={setPeriod} />
            <button className="btn btn-primary" onClick={openAdd}>+ Đặt ngân sách</button>
          </>
        }
      />

      {loading ? (
        <SpinnerCenter />
      ) : items.length === 0 ? (
        <div className="card">
          <EmptyState emoji="🎯" title="Chưa có ngân sách"
            subtitle="Đặt hạn mức cho danh mục chi tiêu để được cảnh báo khi sắp vượt."
            action={<button className="btn btn-primary btn-sm" onClick={openAdd}>+ Đặt ngân sách</button>} />
        </div>
      ) : (
        <>
          <div className="card budget-summary fade-up">
            <div className="bs-item">
              <span className="bs-label">Tổng hạn mức</span>
              <span className="num bs-value">{money(totalLimit)}</span>
            </div>
            <div className="bs-divider" />
            <div className="bs-item">
              <span className="bs-label">Đã chi</span>
              <span className="num bs-value">{money(totalSpent)}</span>
            </div>
            <div className="bs-divider" />
            <div className="bs-item">
              <span className="bs-label">Còn lại</span>
              <span className={`num bs-value ${totalLimit - totalSpent >= 0 ? 'amount-income' : 'amount-expense'}`}>
                {money(totalLimit - totalSpent)}
              </span>
            </div>
          </div>

          <div className="budget-cards fade-up">
            {items.map((b) => (
              <div className="card budget-card" key={b.budgetId}>
                <div className="bc-head">
                  <span className="bc-name">{b.icon} {b.categoryName}</span>
                  <span className={`badge ${statusBadgeClass[b.status]}`}>{BUDGET_STATUS_LABEL[b.status]}</span>
                </div>
                <div className="bc-amounts">
                  <span className="num bc-spent">{money(b.spent)}</span>
                  <span className="muted text-sm num"> / {money(b.limit)}</span>
                </div>
                <div className="progress bc-progress">
                  <div className={`progress-fill ${BUDGET_STATUS_CLASS[b.status]}`}
                    style={{ width: `${Math.min(b.percentage, 100)}%` }} />
                </div>
                <div className="bc-foot">
                  <span className="num text-sm muted">{b.percentage}% đã dùng</span>
                  <span className={`num text-sm ${b.remaining >= 0 ? 'muted' : 'amount-expense'}`}>
                    {b.remaining >= 0 ? `Còn ${money(b.remaining, { compact: true })}` : `Vượt ${money(-b.remaining, { compact: true })}`}
                  </span>
                </div>
                <div className="bc-actions">
                  <button className="btn btn-ghost btn-sm" onClick={() => openEdit(b)}>Sửa</button>
                  <button className="btn btn-ghost btn-sm" onClick={() => setDeleting(b)}>Xóa</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <Modal
        open={modalOpen}
        title={editing ? 'Sửa ngân sách' : 'Đặt ngân sách'}
        onClose={() => setModalOpen(false)}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setModalOpen(false)} disabled={saving}>Hủy</button>
            <button className="btn btn-primary" onClick={submit} disabled={saving}>
              {saving ? <Spinner /> : 'Lưu'}
            </button>
          </>
        }
      >
        <form className="tx-form" onSubmit={submit}>
          {error && <div className="auth-error">{error}</div>}
          <div className="field">
            <label className="label">Danh mục chi tiêu</label>
            {editing ? (
              <input className="input" value={`${editing.icon || ''} ${editing.categoryName}`} disabled />
            ) : (
              <select className="select" value={form.categoryId}
                onChange={(e) => setForm((f) => ({ ...f, categoryId: e.target.value }))}>
                <option value="">— Chọn danh mục —</option>
                {availableCategories.map((c) => (
                  <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                ))}
              </select>
            )}
            {!editing && availableCategories.length === 0 && (
              <span className="text-sm faint">Tất cả danh mục chi tiêu đã có ngân sách trong tháng này.</span>
            )}
          </div>
          <div className="field">
            <label className="label">Hạn mức tháng</label>
            <input className="input" type="number" min="0" step="1000"
              value={form.limitAmount}
              onChange={(e) => setForm((f) => ({ ...f, limitAmount: e.target.value }))}
              placeholder="0" />
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleting)}
        message={`Xóa ngân sách cho "${deleting?.categoryName}"?`}
        onConfirm={confirmDelete}
        onClose={() => setDeleting(null)}
      />
    </div>
  );
};

export default BudgetsPage;
