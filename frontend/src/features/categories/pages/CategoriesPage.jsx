import { useCallback, useEffect, useMemo, useState } from 'react';
import { useToast } from '@/contexts/ToastContext';
import PageHeader from '@/shared/components/PageHeader';
import { SpinnerCenter, EmptyState, Modal, ConfirmDialog, Spinner } from '@/shared/ui';
import {
  CATEGORY_TYPE_LABEL, CATEGORY_PALETTE, ICON_CHOICES, colorFor,
} from '@/shared/utils/constants';
import categoriesApi from '../api/categoriesApi';
import './CategoriesPage.css';

const emptyForm = { name: '', type: 'EXPENSE', icon: '💸', color: CATEGORY_PALETTE[0] };

const CategoriesPage = () => {
  const toast = useToast();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await categoriesApi.list();
      setList(res.data || []);
    } catch (err) {
      toast.error(err.message || 'Không tải được danh mục');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  const grouped = useMemo(() => ({
    INCOME: list.filter((c) => c.type === 'INCOME'),
    EXPENSE: list.filter((c) => c.type === 'EXPENSE'),
  }), [list]);

  const openAdd = (type = 'EXPENSE') => {
    setEditing(null);
    setForm({ ...emptyForm, type });
    setError('');
    setModalOpen(true);
  };
  const openEdit = (cat) => {
    setEditing(cat);
    setForm({ name: cat.name, type: cat.type, icon: cat.icon || '💸', color: cat.color || CATEGORY_PALETTE[0] });
    setError('');
    setModalOpen(true);
  };

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (!form.name.trim()) return setError('Vui lòng nhập tên danh mục');
    setSaving(true);
    try {
      if (editing) {
        await categoriesApi.updateCategory(editing.id, {
          name: form.name.trim(), icon: form.icon, color: form.color,
        });
        toast.success('Đã cập nhật danh mục');
      } else {
        await categoriesApi.createCategory({
          name: form.name.trim(), type: form.type, icon: form.icon, color: form.color,
        });
        toast.success('Đã tạo danh mục');
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
      await categoriesApi.deleteCategory(deleting.id);
      toast.success('Đã xóa danh mục');
      setDeleting(null);
      load();
    } catch (err) {
      toast.error(err.message || 'Xóa thất bại');
    }
  };

  const renderGroup = (type) => (
    <div className="card cat-group">
      <div className="card-header">
        <div className="card-title">{CATEGORY_TYPE_LABEL[type]} <span className="muted">({grouped[type].length})</span></div>
        <button className="btn btn-ghost btn-sm" onClick={() => openAdd(type)}>+ Thêm</button>
      </div>
      <div className="card-pad">
        {grouped[type].length === 0 ? (
          <EmptyState emoji="🏷️" title="Chưa có danh mục" />
        ) : (
          <div className="cat-grid">
            {grouped[type].map((c) => (
              <div className="cat-item" key={c.id}>
                <span className="cat-icon" style={{ background: `${colorFor(c.color)}22`, color: colorFor(c.color) }}>
                  {c.icon || '💸'}
                </span>
                <span className="cat-name">{c.name}</span>
                <div className="cat-actions">
                  <button className="btn btn-icon btn-ghost btn-sm" onClick={() => openEdit(c)} title="Sửa">✏️</button>
                  <button className="btn btn-icon btn-ghost btn-sm" onClick={() => setDeleting(c)} title="Xóa">🗑️</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div>
      <PageHeader
        title="Danh mục"
        subtitle="Tổ chức thu nhập và chi tiêu theo nhóm"
        actions={<button className="btn btn-primary" onClick={() => openAdd('EXPENSE')}>+ Thêm danh mục</button>}
      />

      {loading ? (
        <SpinnerCenter />
      ) : (
        <div className="cat-columns fade-up">
          {renderGroup('EXPENSE')}
          {renderGroup('INCOME')}
        </div>
      )}

      <Modal
        open={modalOpen}
        title={editing ? 'Sửa danh mục' : 'Thêm danh mục'}
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

          {!editing && (
            <div className="type-toggle">
              <button type="button" className={`type-btn ${form.type === 'EXPENSE' ? 'active expense' : ''}`}
                onClick={() => setForm((f) => ({ ...f, type: 'EXPENSE' }))}>Chi tiêu</button>
              <button type="button" className={`type-btn ${form.type === 'INCOME' ? 'active income' : ''}`}
                onClick={() => setForm((f) => ({ ...f, type: 'INCOME' }))}>Thu nhập</button>
            </div>
          )}

          <div className="field">
            <label className="label">Tên danh mục</label>
            <input className="input" value={form.name} autoFocus
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Ví dụ: Ăn uống" />
          </div>

          <div className="field">
            <label className="label">Biểu tượng</label>
            <div className="picker">
              {ICON_CHOICES.map((ic) => (
                <button type="button" key={ic}
                  className={`picker-item ${form.icon === ic ? 'sel' : ''}`}
                  onClick={() => setForm((f) => ({ ...f, icon: ic }))}>{ic}</button>
              ))}
            </div>
          </div>

          <div className="field">
            <label className="label">Màu</label>
            <div className="picker">
              {CATEGORY_PALETTE.map((col) => (
                <button type="button" key={col}
                  className={`color-dot ${form.color === col ? 'sel' : ''}`}
                  style={{ background: col }}
                  onClick={() => setForm((f) => ({ ...f, color: col }))} />
              ))}
            </div>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleting)}
        message={`Xóa danh mục "${deleting?.name}"? Không thể xóa nếu đang có giao dịch.`}
        onConfirm={confirmDelete}
        onClose={() => setDeleting(null)}
      />
    </div>
  );
};

export default CategoriesPage;
