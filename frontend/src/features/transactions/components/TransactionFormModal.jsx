import { useEffect, useMemo, useState } from 'react';
import { Modal, Spinner } from '@/shared/ui';
import { CATEGORY_TYPE } from '@/shared/utils/constants';
import { todayInput } from '@/shared/utils/formatters';

const emptyForm = { categoryId: '', amount: '', occurredAt: todayInput(), note: '' };

const TransactionFormModal = ({ open, onClose, onSubmit, categories, editing }) => {
  const [type, setType] = useState(CATEGORY_TYPE.EXPENSE);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    setError('');
    if (editing) {
      setType(editing.type);
      setForm({
        categoryId: String(editing.categoryId),
        amount: String(editing.amount),
        occurredAt: editing.occurredAt?.slice(0, 10) || todayInput(),
        note: editing.note || '',
      });
    } else {
      setType(CATEGORY_TYPE.EXPENSE);
      setForm(emptyForm);
    }
  }, [open, editing]);

  const filtered = useMemo(
    () => categories.filter((c) => c.type === type),
    [categories, type],
  );

  const onChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (!form.categoryId) return setError('Vui lòng chọn danh mục');
    if (!(Number(form.amount) > 0)) return setError('Số tiền phải lớn hơn 0');

    setSaving(true);
    try {
      await onSubmit({
        categoryId: Number(form.categoryId),
        amount: Number(form.amount),
        occurredAt: form.occurredAt,
        note: form.note.trim() || undefined,
      });
      onClose();
    } catch (err) {
      setError(err.message || 'Lưu thất bại');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title={editing ? 'Sửa giao dịch' : 'Thêm giao dịch'}
      onClose={onClose}
      footer={
        <>
          <button className="btn btn-ghost" onClick={onClose} disabled={saving}>Hủy</button>
          <button className="btn btn-primary" onClick={submit} disabled={saving}>
            {saving ? <Spinner /> : 'Lưu'}
          </button>
        </>
      }
    >
      <form className="tx-form" onSubmit={submit}>
        {error && <div className="auth-error">{error}</div>}

        <div className="type-toggle">
          <button type="button"
            className={`type-btn ${type === 'EXPENSE' ? 'active expense' : ''}`}
            onClick={() => { setType('EXPENSE'); setForm((f) => ({ ...f, categoryId: '' })); }}>
            Chi tiêu
          </button>
          <button type="button"
            className={`type-btn ${type === 'INCOME' ? 'active income' : ''}`}
            onClick={() => { setType('INCOME'); setForm((f) => ({ ...f, categoryId: '' })); }}>
            Thu nhập
          </button>
        </div>

        <div className="field">
          <label className="label">Số tiền</label>
          <input className="input" type="number" name="amount" min="0" step="1000"
            value={form.amount} onChange={onChange} placeholder="0" autoFocus />
        </div>

        <div className="field">
          <label className="label">Danh mục</label>
          <select className="select" name="categoryId" value={form.categoryId} onChange={onChange}>
            <option value="">— Chọn danh mục —</option>
            {filtered.map((c) => (
              <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
            ))}
          </select>
        </div>

        <div className="field">
          <label className="label">Ngày</label>
          <input className="input" type="date" name="occurredAt" value={form.occurredAt} onChange={onChange} />
        </div>

        <div className="field">
          <label className="label">Ghi chú</label>
          <input className="input" name="note" value={form.note} onChange={onChange} placeholder="Ví dụ: Ăn trưa cùng đồng nghiệp" />
        </div>
      </form>
    </Modal>
  );
};

export default TransactionFormModal;
