import { useEffect, useMemo, useRef, useState } from 'react';
import { Modal, Spinner } from '@/shared/ui';
import { CATEGORY_TYPE } from '@/shared/utils/constants';
import { todayInput } from '@/shared/utils/formatters';
import { useToast } from '@/contexts/ToastContext';

const emptyForm = { categoryId: '', amount: '', occurredAt: todayInput(), note: '' };

// Câu chờ dí dỏm khi "quét" hóa đơn (luân phiên hiển thị)
const SCAN_MSGS = [
  '📸 Đang chụp lại cái hóa đơn...',
  '🔍 Soi từng con số cho kỹ...',
  '🧾 Hỏi nhỏ hóa đơn: "hết nhiêu vậy?"',
  '🤖 Nhờ AI đọc chữ như đọc toa bác sĩ...',
  '🧮 Bấm máy tính lạch cạch...',
  '😎 Sắp xong — nhớ đừng tiêu lố nha!',
];
const SCAN_STEP_MS = 1200;

const TransactionFormModal = ({ open, onClose, onSubmit, categories, editing }) => {
  const toast = useToast();
  const [type, setType] = useState(CATEGORY_TYPE.EXPENSE);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [scanning, setScanning] = useState(false);
  const [scanMsg, setScanMsg] = useState(SCAN_MSGS[0]);
  const fileRef = useRef(null);
  const scanTimers = useRef([]);

  const clearScan = () => {
    scanTimers.current.forEach(clearTimeout);
    scanTimers.current = [];
  };

  const openScan = () => fileRef.current?.click();

  const onPickImage = (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    clearScan();
    setScanMsg(SCAN_MSGS[0]);
    setScanning(true);
    SCAN_MSGS.forEach((m, i) => {
      scanTimers.current.push(setTimeout(() => setScanMsg(m), i * SCAN_STEP_MS));
    });
    scanTimers.current.push(
      setTimeout(() => {
        setScanning(false);
        // Chưa nối OCR thật — báo nhẹ nhàng, dí dỏm
        toast.info('Máy quét đang đi nghỉ mát 🏖️ — bạn nhập số tiền tay giúp mình nhé!');
      }, SCAN_MSGS.length * SCAN_STEP_MS),
    );
  };

  // Dọn timer khi đóng modal / unmount
  useEffect(() => {
    if (!open) {
      clearScan();
      setScanning(false);
    }
  }, [open]);
  useEffect(() => () => clearScan(), []);

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
        {scanning && (
          <div className="tx-scan-overlay">
            <div className="tx-scan-lens">🧾</div>
            <div className="tx-scan-msg">{scanMsg}</div>
            <div className="tx-scan-bar"><span /></div>
          </div>
        )}

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
          <div className="tx-amount-head">
            <label className="label">Số tiền</label>
            <button type="button" className="btn btn-ghost btn-sm tx-ocr-btn"
              onClick={openScan} disabled={saving || scanning}>
              📷 Quét hóa đơn
            </button>
          </div>
          <input className="input" type="number" name="amount" min="0" step="1000"
            value={form.amount} onChange={onChange} placeholder="0" autoFocus />
          <input ref={fileRef} type="file" accept="image/*" capture="environment"
            hidden onChange={onPickImage} />
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
